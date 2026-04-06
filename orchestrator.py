import os
import json
import datetime
import uuid
import sys
from intake_assistant import IntakeAssistant
from reasoning_engine import HybridReasoningEngine
from hybrid_rag import HybridRAGPipeline, run_pipeline as run_rag_pipeline
import patient_responder
from translation_utils import translator

# --- Configuration ---
LOGS_DIR = "intake_logs"
REPORTS_DIR = "reasoning_reports"
RAG_OUTPUT_DIR = "hybrid_rag_outputs"

class AIOrchestrator:
    def __init__(self):
        print("[*] Initializing AI Orchestrator...")
        self.intake_agent = IntakeAssistant()
        self.reasoning_engine = HybridReasoningEngine()
        self.user_language = 'en'
        # RAG and Responder are initialized/called as needed
        
    def _handle_session_resumption(self):
        """Checks for previous sessions and prompts user to resume."""
        latest_log = self.intake_agent.get_latest_session_log(LOGS_DIR)
        if latest_log:
            print(f"\n[!] Found a previous session from: {latest_log}")
            choice = input("Would you like to resume this session? (y/n): ").strip().lower()
            if choice == 'y':
                self.intake_agent.load_session_data(latest_log)
                return True
        
        # If no session or user chooses not to resume, force reset to fresh state
        self.intake_agent.reset_state()
        return False

    def run_intake_stage(self):
        """Step 1: Coordinate the interactive medical intake."""
        print("\n" + "="*40)
        print("STEP 1: MEDICAL INTAKE")
        print("="*40)
        
        self._handle_session_resumption()
        
        turn_count = 0
        MAX_TURNS = 5
        
        while True:
            # Check if complete
            if not self.intake_agent.state.get("missing_fields"):
                print("\n[+] Intake complete. Information gathered successfully.")
                break
            
            if turn_count >= MAX_TURNS:
                print("\n[!] Maximum intake turns reached. Proceeding with available data.")
                break

            user_msg = input("\nPatient: ").strip()
            if user_msg.lower() in ['exit', 'quit']:
                print("[*] Ending session. Saving progress...")
                self.intake_agent._save_state()
                sys.exit(0)

            if not user_msg: continue

            # Detect language on first interaction
            if turn_count == 0:
                self.user_language = translator.detect_language(user_msg)
                if self.user_language != 'en':
                    print(f"[*] Language detected: {self.user_language}")

            # Translate input to English for pipeline processing
            english_msg = translator.translate_to_english(user_msg)

            print(f"[*] Analyzing response...")
            state, questions = self.intake_agent.process_turn(english_msg)
            
            if questions:
                print("\n--- Follow-up ---")
                for q in questions:
                    # Translate follow-up questions back to user's language
                    translated_q = translator.translate_to_user_language(q, self.user_language)
                    print(f"- {translated_q}")
                turn_count += 1
            else:
                # If no questions but fields still missing, might be an extraction stall
                if state.get("missing_fields"):
                   print(f"[*] Still missing: {', '.join(state['missing_fields'][:3])}...")
                   turn_count += 1
                else:
                   break

        # Save the finalized intake data to a fixed location for the next agents
        final_intake_path = os.path.join(LOGS_DIR, f"final_intake_{uuid.uuid4().hex[:8]}.json")
        with open(final_intake_path, 'w', encoding='utf-8') as f:
            json.dump(self.intake_agent.state, f, indent=4)
        
        return final_intake_path

    def run_reasoning_stage(self, intake_path: str):
        """Step 2: Perform clinical reasoning classification."""
        print("\n" + "="*40)
        print("STEP 2: CLINICAL REASONING")
        print("="*40)
        
        with open(intake_path, 'r', encoding='utf-8') as f:
            intake_data = json.load(f)
            
        print("[*] Validating clinical data and determining severity...")
        report = self.reasoning_engine.analyze(intake_data)
        
        # Find the latest report file (most recent in reasoning_reports)
        latest_report = max([os.path.join(REPORTS_DIR, f) for f in os.listdir(REPORTS_DIR)], key=os.path.getctime)
        return latest_report

    def run_rag_stage(self, intake_path: str, reasoning_path: str):
        """Step 3: Retrieve knowledge and synthesize evidence."""
        print("\n" + "="*40)
        print("STEP 3: HYBRID RAG SYNTHESIS")
        print("="*40)
        
        print("[*] Running Dense + Sparse retrieval and reranking...")
        # Since we have the paths, we can use the existing run_pipeline helper
        run_rag_pipeline(intake_path, reasoning_path)
        
        # Find the latest RAG output
        latest_rag = max([os.path.join(RAG_OUTPUT_DIR, f) for f in os.listdir(RAG_OUTPUT_DIR)], key=os.path.getctime)
        return latest_rag

    def run_response_stage(self, rag_output_path: str):
        """Step 4: Generate patient-friendly structured response."""
        print("\n" + "="*40)
        print("STEP 4: FINAL GUIDANCE")
        print("="*40)
        
        with open(rag_output_path, 'r', encoding='utf-8') as f:
            rag_data = json.load(f)
            
        print("[*] Reformatting for patient guidance...")
        patient_view = patient_responder.generate_patient_response(rag_data)
        
        # Translate the final response back to user's language
        final_response = translator.translate_to_user_language(patient_view, self.user_language)
        
        print("\n" + "*"*50)
        print(final_response)
        print("*"*50)
        
        # Mandatory sources used
        try:
            raw_res = rag_data.get("final_llm_response", "{}")
            if isinstance(raw_res, str):
                summary_json = json.loads(raw_res)
            else:
                summary_json = raw_res
                
            sources = summary_json.get("sources_used", [])
            if sources:
                print(f"\n[!] Sources Used: {', '.join(sources)}")
        except:
            pass
        
        print(f"\n[!] DISCLAIMER: {rag_data.get('disclaimer', 'Medical insight for information only.')}")

    def execute_pipeline(self):
        """Main orchestrator execution logic."""
        try:
            # 1. Intake
            intake_path = self.run_intake_stage()
            
            # 2. Reasoning
            reasoning_path = self.run_reasoning_stage(intake_path)
            
            # 3. RAG
            rag_path = self.run_rag_stage(intake_path, reasoning_path)
            
            # 4. Response
            self.run_response_stage(rag_path)
            
            print("\n[✔] Full Clinical Workflow Completed Successfully.")
            
        except Exception as e:
            print(f"\n[✘] Orchestrator Error: {str(e)}")

if __name__ == "__main__":
    orchestrator = AIOrchestrator()
    orchestrator.execute_pipeline()
