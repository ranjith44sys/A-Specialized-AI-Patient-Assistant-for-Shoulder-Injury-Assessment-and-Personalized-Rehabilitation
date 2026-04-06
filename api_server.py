"""
api_server.py — Flask REST API bridge between the React frontend and the Python RAG pipeline.

Run with:  python api_server.py
Frontend proxies POST /analyze → http://localhost:8000/analyze
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, uuid, traceback

# ── Pipeline imports ────────────────────────────────────────────────────────
from translation_utils import translator
from intake_assistant import IntakeAssistant
from reasoning_engine import HybridReasoningEngine
from hybrid_rag import run_pipeline as run_rag_pipeline
import patient_responder

try:
    from medclip_processor import medclip_processor, merge_with_user_input
except ImportError:
    medclip_processor = None

# ── Config ──────────────────────────────────────────────────────────────────
LOGS_DIR       = "intake_logs"
REPORTS_DIR    = "reasoning_reports"
RAG_OUTPUT_DIR = "hybrid_rag_outputs"

os.makedirs(LOGS_DIR,       exist_ok=True)
os.makedirs(REPORTS_DIR,    exist_ok=True)
os.makedirs(RAG_OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)   # allow the Vite dev server to call this API

# ── Shared stateful agents (re-used across turns) ───────────────────────────
intake_agent    = IntakeAssistant()
reasoning_engine = HybridReasoningEngine()

# ── Session state (single-session; extend with Redis for multi-user) ─────────
session = {
    "language": "en",
    "turn": 0,
    "state": None,
}


def _latest_file(directory, ext=".json"):
    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(ext)
    ]
    return max(files, key=os.path.getctime) if files else None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    # Handle both JSON and FormData requests
    if request.is_json:
        body = request.get_json(silent=True) or {}
        user_input = body.get("input", "").strip()
        lang_code = body.get("language", "en")
        pain_location = body.get("pain_location")
        image_bytes = None
    else:
        user_input = request.form.get("input", "").strip()
        lang_code = request.form.get("language", "en")
        pain_location = request.form.get("pain_location")
        # Read image to bytes in memory without saving to disk
        image_file = request.files.get("image")
        image_bytes = image_file.read() if image_file else None

    if not user_input and not image_bytes and not pain_location:
        return jsonify({"error": "Input, image, or pain location is required"}), 400

    try:
        # Auto-detect language from input to overrule client default if user typed in Tamil/Hindi
        if user_input:
            detected = translator.detect_language(user_input)
            if detected != "en":
                lang_code = detected

        # ── Store language for the session ────────────────────────────────────────
        session["language"] = lang_code
        session["turn"]    += 1

        # ── STEP 1: Translate input → English ─────────────────────────────────
        english_input = translator.translate_to_english(user_input) if user_input else ""

        # ── Inject 3D Touch Localization ──────────────────────────────────────
        if pain_location:
            touch_ctx = f"[VIRTUAL 3D MODEL interaction]: The user precisely selected the following anatomical region on the 3D model: {pain_location}."
            english_input = f"{english_input}\n{touch_ctx}".strip()

        # ── STEP 1.5: Process Image if provided ───────────────────────────────
        image_insights = ""
        image_insights_translated = ""
        if image_bytes and medclip_processor:
            print("[*] Processing uploaded image via MedCLIP...")
            image_insights = medclip_processor.get_image_insights(image_bytes)
            if image_insights:
                image_insights_translated = translator.translate_to_user_language(image_insights, lang_code)
            
        # Merge text input and image insights
        combined_input = merge_with_user_input(english_input, image_insights) if medclip_processor else english_input

        # ── STEP 2: Intake turn ───────────────────────────────────────────────
        if session["turn"] == 1:
            intake_agent.reset_state()

        state, follow_up_questions = intake_agent.process_turn(combined_input, pain_location=pain_location)
        session["state"] = state

        # Translate follow-up questions back to user's language
        translated_fups = [
            translator.translate_to_user_language(q, lang_code)
            for q in follow_up_questions
        ]

        # ── If intake not complete, return follow-up questions ────────────────
        missing = state.get("missing_fields", [])
        if missing and follow_up_questions and session["turn"] <= 5:
            return jsonify({
                "language": lang_code,
                "follow_up_questions": translated_fups,
                "missing_fields": missing,
                "turn": session["turn"],
                "image_description": image_insights_translated,
                "pain_location": pain_location
            })

        # ── STEP 3: Save final intake ─────────────────────────────────────────
        intake_path = os.path.join(LOGS_DIR, f"final_intake_{uuid.uuid4().hex[:8]}.json")
        with open(intake_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

        # ── STEP 4: Reasoning ─────────────────────────────────────────────────
        reasoning_engine.analyze(state)
        reasoning_path = _latest_file(REPORTS_DIR)
        if not reasoning_path:
            raise RuntimeError("Reasoning engine produced no output.")

        # ── STEP 5: Hybrid RAG ────────────────────────────────────────────────
        run_rag_pipeline(intake_path, reasoning_path)
        rag_path = _latest_file(RAG_OUTPUT_DIR)
        if not rag_path:
            raise RuntimeError("RAG pipeline produced no output.")

        with open(rag_path, "r", encoding="utf-8") as f:
            rag_data = json.load(f)

        # ── STEP 6: Generate patient-friendly response ────────────────────────
        print(f"DEBUG: Calling generate_patient_response with lang_code={lang_code}")
        final_response = patient_responder.generate_patient_response(rag_data, lang_code)
        print(f"DEBUG: Final response generated: {final_response[:100]}...")

        # Sources
        sources = []
        try:
            raw_res = rag_data.get("final_llm_response", "{}")
            summary_json = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
            sources = summary_json.get("sources_used", [])
        except Exception:
            pass

        # Reset for next session
        session["turn"] = 0

        return jsonify({
            "language": lang_code,
            "response": final_response,
            "disclaimer": rag_data.get(
                "disclaimer",
                "This is an AI-generated clinical insight for informational purposes only."
            ),
            "sources": sources,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 MedAssist API Server starting on http://localhost:8000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8000, debug=False)
