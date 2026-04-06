import json
import os
import uuid
import datetime
import requests
from typing import List, Dict, Any, Tuple

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b-instruct" # Automatically updated to match your local Ollama tags
PERSISTENT_SCHEMA = "intake_schema.json"
LOGS_DIR = "intake_logs"

class IntakeAssistant:
    def __init__(self, schema_path: str = PERSISTENT_SCHEMA, logs_dir: str = LOGS_DIR, model: str = OLLAMA_MODEL):
        self.schema_path = schema_path
        self.logs_dir = logs_dir
        self.model = model
        self.session_id = str(uuid.uuid4())[:8]
        self.state = self._load_schema()
        
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

    def _load_schema(self) -> Dict[str, Any]:
        """Loads a copy of the intake schema. Note: this might load persistent data if it exists."""
        base_schema = {
            "condition": "", "onset": "", "pain_location": "", "pain_severity": "",
            "pain_nature": "", "duration": "", "trigger_event": "", "previous_history": "",
            "functional_limitations": "", "medical_history": "", "red_flags": "",
            "treatments_taken": "", "additional_notes": "", "missing_fields": []
        }
        
        if os.path.exists(self.schema_path):
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                    base_schema.update(saved_state)
            except:
                pass
        
        self.state = base_schema
        self._update_missing_fields()
        return self.state

    def reset_state(self):
        """Force resets the state to a fresh, empty schema."""
        self.state = {
            "condition": "", "onset": "", "pain_location": "", "pain_severity": "",
            "pain_nature": "", "duration": "", "trigger_event": "", "previous_history": "",
            "functional_limitations": "", "medical_history": "", "red_flags": "",
            "treatments_taken": "", "additional_notes": "", "missing_fields": []
        }
        self._update_missing_fields()
        return self.state

    def _save_state(self):
        """Persists the current patient state to the schema file."""
        with open(self.schema_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4)

    def _log_interaction(self, user_input: str, json_extracted: Dict):
        """Appends the interaction data to a single unified session log file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.logs_dir, f"session_{self.session_id}.jsonl")
        
        log_entry = {
            "timestamp": timestamp,
            "user_input": user_input,
            "extracted_data": json_extracted,
            "current_missing": self.state.get("missing_fields", [])
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")

    def _get_system_prompt(self) -> str:
        """Returns the system prompt for the LLM."""
        return f"""
        You are a medical intake assistant following the HOPI framework (History, Pain, Functional, Risk Factors, Red Flags, Treatment).
        
        CURRENT PATIENT STATE:
        {json.dumps(self.state, indent=2)}

        TASK:
        1. Extract structured medical info from the NEW user input into the schema.
        2. Merge it with the CURRENT state above. Do NOT lose existing data.
        3. If any field is missing, identify it in 'missing_fields'.
        4. Generate 1-3 targeted follow-up questions for the MOST CRITICAL missing fields.
        
        CRITICAL PRIORITIZATION:
        - Priority 1 (CRITICAL): red_flags, pain_severity, pain_location
        - Priority 2 (HIGH): onset, pain_nature, trigger_event, duration
        - Priority 3 (STANDARD): functional_limitations, previous_history, medical_history, treatments_taken
        
        RULES:
        - Return ONLY a valid JSON object.
        - Map severity specifically (e.g., '8 out of 10' -> '8').
        - DO NOT ask follow-up questions for fields that are ALREADY FILLED in the CURRENT PATIENT STATE.
        - MANDATORY RULE: If 'pain_location' is already present (e.g., from 3D model interaction), DO NOT ASK WHERE THE PAIN IS. Proceed immediately to other assessments like onset, severity, or red flags.
        - Prioritize questions (1-3 max) for empty fields based on the CRITICAL PRIORITIZATION list.
        - If all priority fields are filled, move to the next priority level.
        
        OUTPUT SCHEMA:
        {{
          "updated_state": {{ ... all fields ... }},
          "follow_up_questions": [ "q1", "q2" ],
          "is_complete": true/false
        }}
        
        TURN LIMIT:
        You MUST complete the intake within 5 turns. Prioritize the most critical fields (Priority 1 and 2) immediately.
        """

    def process_turn(self, user_input: str, pain_location: str = None) -> Tuple[Dict[str, Any], List[str]]:
        """Processes a single turn using a local open-source model via Ollama."""
        try:
            # Explicitly set pain location if injected from 3D model
            if pain_location:
                self.state["pain_location"] = pain_location
                self._update_missing_fields()

            prompt = f"{self._get_system_prompt()}\n\nUser Input: {user_input}"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json" # Ollama's native JSON support
            }
            
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            
            # The Ollama API returns JSON with a 'response' field containing the model output
            raw_data = response.json()
            raw_llm_text = raw_data.get("response", "").strip()

            # Parse the extracted JSON from the LLM
            try:
                result = json.loads(raw_llm_text)
            except json.JSONDecodeError:
                print(f"[!] Warning: LLM returned invalid JSON. Raw response saved in logs.")
                return self.state, ["Could you please rephrase that? I had trouble processing the response."]
            
            # Update state with new info while preserving old state
            new_state = result.get("updated_state", {})
            if not new_state:
                print("[!] Warning: LLM response did not contain 'updated_state'.")
            
            for k, v in new_state.items():
                if v and k != "missing_fields":
                    self.state[k] = v
            
            # Re-calculate missing fields manually to ensure consistency
            self._update_missing_fields()
            
            # Log interaction to unified session file
            self._log_interaction(user_input, result)
            
            # Sync state to persistent schema after every turn (Constant State Sync)
            self._save_state()
            
            return self.state, result.get("follow_up_questions", [])

        except requests.exceptions.ConnectionError:
            return self.state, ["Error: Could not connect to Ollama. Is it running at localhost:11434?"]
        except Exception as e:
            # Return error while preserving current state
            print(f"[!] Error in process_turn: {str(e)}")
            return self.state, [f"Extraction Error: {str(e)}"]

    def _update_missing_fields(self):
        """Internal helper to identify empty mandatory fields."""
        mandatory = [
            "condition", "onset", "pain_location", "pain_severity", 
            "pain_nature", "duration", "trigger_event", "previous_history", 
            "functional_limitations", "medical_history", "red_flags", 
            "treatments_taken"
        ]
        self.state["missing_fields"] = [f for f in mandatory if not self.state.get(f)]

    def load_session_data(self, file_path: str):
        """Loads a previous session's extracted state from a log file."""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # If it's a raw output log, it might be nested
                if "updated_state" in data:
                    self.state.update(data["updated_state"])
                else:
                    self.state.update(data)
            self._update_missing_fields()
            print(f"[*] Successfully resumed session from: {file_path}")

    @staticmethod
    def get_latest_session_log(logs_dir: str = LOGS_DIR) -> str:
        """Finds the most recently created output log file."""
        if not os.path.exists(logs_dir):
            return None
        files = [os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if f.startswith("output_") and f.endswith(".json")]
        if not files:
            return None
        return max(files, key=os.path.getctime)

def run_interactive_session():
    """Main interactive loop for the intake assistant."""
    assistant = IntakeAssistant()
    
    # Quick health check for Ollama
    try:
        requests.get("http://localhost:11434", timeout=2)
    except Exception:
        print("[!] Warning: Local Ollama server not detected.")
        print("[!] Please install and run Ollama (https://ollama.com/) with 'ollama run llama3'")
        return

    print("=" * 40)
    print(f"Medical Intake Assistant (OS Model: {OLLAMA_MODEL})")
    print("Type 'exit' or 'quit' at any time to end the session.")
    print("=" * 40)

    MAX_FOLLOW_UPS = 5
    turn_count = 0

    while True:
        user_msg = input("\nUser: ").strip()
        
        if user_msg.lower() in ['exit', 'quit']:
            print("Session ended. Saving current progress...")
            assistant._save_state()
            break
            
        if not user_msg:
            continue

        print(f"[*] Processing response (Turn {turn_count}/{MAX_FOLLOW_UPS})...")
        state, questions = assistant.process_turn(user_msg)
        
        # Display current state
        print("\n--- Current Patient Record ---")
        print(json.dumps(state, indent=2))
        
        # Check for completion
        if not state.get("missing_fields"):
            print("\n[+] SUCCESS: All required information has been collected.")
            assistant._save_state()
            break
        
        # Check turn limit
        if turn_count >= MAX_FOLLOW_UPS:
            print("\n[!] Turn limit reached (5 follow-ups). Saving collected data and closing session.")
            assistant._save_state()
            break
            
        # Display follow-up questions
        if questions:
            print("\n--- Follow-up Questions ---")
            for q in questions:
                print(f"- {q}")
            turn_count += 1
        else:
            print("\nNo further questions at this time. Saving progress...")
            assistant._save_state()
            break

if __name__ == "__main__":
    run_interactive_session()
