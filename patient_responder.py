import os
import json
import requests
import datetime

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b-instruct" # Fast and good at structured reformatting
RAG_OUTPUT_DIR = "./hybrid_rag_outputs"

def get_latest_file(directory: str, extension: str = ".json") -> str:
    """Helper to find the most recently created file in a directory."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        return None
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]
    if not files:
        return None
    return max(files, key=os.path.getctime)

def generate_patient_response(rag_data: dict, target_lang_code: str = 'en') -> str:
    """Transform technical RAG result into patient-friendly format natively in the specified language."""
    
    lang_map = {'ta': 'Tamil', 'hi': 'Hindi', 'en': 'English'}
    lang_name = lang_map.get(target_lang_code, 'English')
    
    # Extract only what we need to minimize context and prevent hallucination
    summary = rag_data.get("final_llm_response", "")
    
    # If the response was a stringified JSON, parse it
    if isinstance(summary, str):
        try:
            summary_json = json.loads(summary)
            summary_text = summary_json.get("summary", "")
            insights_text = summary_json.get("insights", "")
            steps_text = ", ".join(summary_json.get("treatment_steps", []))
            sources_list = summary_json.get("sources_used", [])
            sources_text = ", ".join(sources_list) if sources_list else "Not specified"
            
            combined_context = f"Condition Summary: {summary_text}\nInsights: {insights_text}\nSuggested Steps: {steps_text}\nSources Used: {sources_text}"
        except:
            combined_context = summary
    else:
        combined_context = str(summary)

    if lang_name == "Tamil":
        structure_format = """
1. என்ன நடக்கிறது?
- [எளிமையான விளக்கம்]

2. நீங்கள் செய்ய வேண்டியவை
- [பரிந்துரைக்கப்பட்ட பாதுகாப்பான வழிமுறைகள்]

3. தவிர்க்க வேண்டியவை
- [செய்யக்கூடாதவை மற்றும் தவிர்க்க வேண்டியவை]

4. மருத்துவரை எப்போது சந்திக்கணும்?
- [அபாய அறிகுறிகள்]"""
    elif lang_name == "Hindi":
        structure_format = """
1. क्या हो रहा है?
- [स्थिति का सरल विवरण]

2. आपको क्या करना चाहिए
- [सुरक्षित और व्यावहारिक कदम]

3. क्या न करें
- [स्थिति को बिगाड़ने वाली गतिविधियाँ]

4. डॉक्टर से कब मिलें?
- [खतरे के संकेत]"""
    else:
        structure_format = """
1. What is happening?
- [Simple explanation of the condition]

2. What you should do?
- [Practical, safe steps from the context]

3. What to avoid?
- [Activities or actions that might worsen the condition]

4. When to see a doctor?
- [Safety-focused warning signs from context]"""

    prompt = f"""[INST] <<SYS>>
You are a medical response generation assistant.
Your task is to transform technical RAG outputs into a patient-friendly response natively in {lang_name}.
RULES:
- Respond ENTIRELY in {lang_name}.
- Use ONLY the provided Input Context. DO NOT add external information.
- DO NOT prescribe medications.
- Use simple, non-technical language.
- Strictly follow the numbered 4-point structure below.
<</SYS>>

INPUT CONTEXT:
{combined_context}

STRICT OUTPUT FORMAT IN {lang_name}:
{structure_format}
[/INST]"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2, # Improved creativity for multi-lingual fluency
            "num_predict": 768
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "Error: No response generated.")
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"

if __name__ == "__main__":
    print("[*] Finding latest RAG results...")
    latest_rag = get_latest_file(RAG_OUTPUT_DIR)
    
    if not latest_rag:
        print("[!] No RAG output files found in ./hybrid_rag_outputs/")
    else:
        print(f"[*] Reading: {latest_rag}")
        with open(latest_rag, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print("[*] Generating Patient-Friendly Response...")
        patient_view = generate_patient_response(data)
        
        print("\n" + "="*50)
        print("         PATIENT-FRIENDLY CLINICAL GUIDANCE")
        print("="*50 + "\n")
        print(patient_view)
        print("\n" + "="*50)
        print("Disclaimer: This is an AI-generated insight for informational purposes.")
        
        # Display Sources Used
        try:
            summary_json = json.loads(data.get("final_llm_response", "{}"))
            sources = summary_json.get("sources_used", [])
            if sources:
                print(f"Sources Used: {', '.join(sources)}")
        except:
            pass
            
        print("="*50)
