import json
import os
import datetime
import uuid
import requests
from typing import Dict, Any, Optional, Tuple

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b-instruct"
REPORTS_DIR = "reasoning_reports"

class HybridReasoningEngine:
    def __init__(self, reports_dir: str = REPORTS_DIR):
        self.reports_dir = reports_dir
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)

    def _apply_rules(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Step 1: Rule-Based Classification."""
        # Extract variables
        duration_str = data.get("duration", "").lower()
        onset = data.get("onset", "").lower()
        severity = 0
        try:
            severity = int(data.get("pain_severity", 0))
        except (ValueError, TypeError):
            pass
        
        pain_nature = data.get("pain_nature", "").lower()
        red_flags = str(data.get("red_flags", [])).lower()
        functional = data.get("functional_limitations", "").lower()
        trigger = data.get("trigger_event", "").lower()

        # Rule evaluation
        is_acute = ("week" not in duration_str or "day" in duration_str) and \
                   ("sudden" in onset or trigger != "")
        
        is_chronic = ("month" in duration_str or "year" in duration_str) and \
                     "gradual" in onset

        has_neurological = "numbness" in pain_nature or "tingling" in pain_nature or \
                          "numbness" in red_flags or "tingling" in red_flags

        is_severe = severity >= 8 or "difficulty" in functional or "major" in functional

        # Classification
        condition = data.get("condition", "Unknown Condition")
        stage = "Subacute" # Default
        
        if is_acute: stage = "Acute"
        if is_chronic: stage = "Chronic"
        if is_severe: stage = "Severe"

        confidence = "High" if (is_acute or is_chronic) and is_severe else "Medium"
        if not duration_str and not onset:
            confidence = "Low"

        return {
            "rule_based_condition": condition,
            "rule_based_stage": stage,
            "rule_confidence": confidence,
            "has_neurological": has_neurological,
            "is_severe": is_severe
        }, confidence

    def _determine_final_stage(self, data: Dict[str, Any], rule_output: Dict[str, Any]) -> str:
        """Step 3: Stage Determination (Duration + Severity)."""
        duration = data.get("duration", "").lower()
        severity = 0
        try:
            severity = int(data.get("pain_severity", 0))
        except: pass

        if severity >= 8 or rule_output.get("is_severe"):
            return "Severe"
        
        if "day" in duration or ("week" in duration and "1" in duration):
            return "Acute"
        elif "week" in duration:
            return "Subacute"
        elif "month" in duration or "year" in duration:
            return "Chronic"
        
        return rule_output.get("rule_based_stage", "Unknown")

    def _llm_validation(self, data: Dict[str, Any], current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: LLM Validation (Critical Reasoning)."""
        prompt = f"""[INST] <<SYS>>
You are a highly accurate Clinical Decision Support System.
You must strictly adhere to the provided PATIENT DATA.
HALLUCINATION IS STRICTLY FORBIDDEN (0% tolerance).

### PROHIBITED ACTIONS ###
1. DO NOT invent or assume patient demographics (Age, Gender, Name) if they are not explicitly provided in the "PATIENT DATA".
2. If age and gender are missing, refer to the individual ONLY as "The patient".
3. DO NOT assume physical exam findings, specific imaging results, or lab values not present in the "PATIENT DATA".
4. DO NOT provide a definitive diagnosis.
<</SYS>>

### PATIENT DATA ###
{json.dumps(data, indent=2)}

### PRELIMINARY REASONING ###
{json.dumps(current_analysis, indent=2)}

TASK:
1. Validate if the 'final_condition' matches symptoms logically.
2. Validate if the 'final_stage' aligns with duration and severity.
3. Correct any contradictions (e.g., Severe pain with no functional impact).
4. Identify Red Flag Alert status.
5. Return ONLY a valid JSON object matching the required format.

REQUIRED OUTPUT FORMAT (JSON):
{{
  "final_condition": "...",
  "final_stage": "...",
  "decision_source": "hybrid",
  "confidence": "High/Medium/Low",
  "rule_based_condition": "{current_analysis['rule_based_condition']}",
  "rule_based_stage": "{current_analysis['rule_based_stage']}",
  "ml_prediction_used": {str(current_analysis.get('ml_prediction_used', False)).lower()},
  "validation_status": "valid / corrected",
  "explanation": "Detailed clinical reasoning without ANY assumptions...",
  "red_flag_alert": true/false
}}
[/INST]"""
        
        try:
            payload = {
                "model": "medllama2",
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "num_predict": 512,
                    "num_ctx": 4096,
                    "temperature": 0.2
                }
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            raw_text = response.json().get("response", "").strip()
            return json.loads(raw_text)
        except Exception as e:
            print(f"[!] LLM Validation Error: {str(e)}")
            return {**current_analysis, "validation_status": "failed", "explanation": f"Validation error: {str(e)}"}

    def analyze(self, patient_data: Dict[str, Any], ml_prediction: Optional[str] = None, ml_confidence: float = 0.0) -> Dict[str, Any]:
        """Main hybrid reasoning pipeline."""
        # 1. Rule-Based
        rule_output, rule_conf = self._apply_rules(patient_data)
        
        # 2. ML Fallback
        use_ml = (rule_conf == "Low") and ml_prediction is not None
        final_condition = ml_prediction if use_ml else rule_output["rule_based_condition"]
        
        # 3. Stage Determination
        final_stage = self._determine_final_stage(patient_data, rule_output)
        
        # Build Intermediate Analysis
        current_analysis = {
            "final_condition": final_condition,
            "final_stage": final_stage,
            "decision_source": "ml_model" if use_ml else "rule_based",
            "confidence": str(ml_confidence if use_ml else rule_conf),
            "rule_based_condition": rule_output["rule_based_condition"],
            "rule_based_stage": rule_output["rule_based_stage"],
            "ml_prediction_used": use_ml,
            "red_flag_alert": bool(patient_data.get("red_flags"))
        }
        
        # 4. LLM Validation
        final_report = self._llm_validation(patient_data, current_analysis)
        
        # Step 5: Programmatic Enforcement (0% Hallucination)
        final_report["disclaimer"] = "This is a computer-generated clinical insight, not a replacement for professional medical advice."
        
        # Step 6: Persistence
        self._save_report(final_report)
        
        return final_report

    def _save_report(self, report: Dict[str, Any]):
        """Saves the final diagnostic report to the reports directory."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = str(uuid.uuid4())[:8]
        filename = f"report_{timestamp}_{report_id}.json"
        
        path = os.path.join(self.reports_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
        print(f"[+] Diagnostic Report saved to: {path}")

if __name__ == "__main__":
    # Quick sanity check with sample data
    engine = HybridReasoningEngine()
    sample_data = {
        "condition": "Shoulder pain",
        "onset": "Sudden",
        "pain_severity": "8",
        "duration": "3 weeks",
        "pain_nature": "Sharp and throbbing",
        "red_flags": "occasional numbness in arm",
        "functional_limitations": "lifting objects, reaching overhead"
    }
    print("[*] Running Sample Analysis...")
    report = engine.analyze(sample_data)
    print(json.dumps(report, indent=2))
