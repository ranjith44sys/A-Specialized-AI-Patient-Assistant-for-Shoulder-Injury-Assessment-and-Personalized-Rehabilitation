import requests
import json
import re

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
# qwen2.5:7b-instruct is highly optimized for fast inference and multilingual accuracy
OLLAMA_MODEL = "qwen2.5:7b-instruct"

class TranslationService:
    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.supported_languages = {'ta': 'Tamil', 'hi': 'Hindi', 'en': 'English'}
        # 1. Translation Cache (Speed)
        self.cache = {}
        # 2. Bypass Dictionary (0 Latency for standard phrases)
        self.bypass = {
            'ta': {
                '0 to 10': '0 முதல் 10', 'pain scale': 'வலி அளவுகோல்',
                'medical intake': 'மருத்துவ ஆய்வு', 'follow-up': 'தொடர்பு கேள்வி'
            },
            'hi': {
                '0 to 10': '0 से 10', 'pain scale': 'दर्द पैमाना',
                'medical intake': 'मेडिकल इनटेक', 'follow-up': 'अगला सवाल'
            }
        }
        # 3. Clinical Glossary (Consistency)
        self.glossary = {
            'ta': {
                'pain': 'வலி', 'onset': 'தொடக்கம்', 'severity': 'தீவிரம்',
                'injury': 'காயம்', 'swelling': 'வீக்கம்', 'movement': 'அசைவு',
                'numbness': 'மரத்துப்போதல்', 'symptoms': 'அறிகுறிகள்'
            },
            'hi': {
                'pain': 'दर्द', 'onset': 'शुरुआत', 'severity': 'गंभीरता',
                'injury': 'चोट', 'swelling': 'सूजन', 'movement': 'गति',
                'numbness': 'सुन्न होना', 'symptoms': 'लक्षण'
            }
        }
        
    def _call_ollama(self, prompt: str, num_predict: int = 512) -> str:
        """Helper for low-latency Ollama generation."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,        # Deterministic and faster
                "num_predict": num_predict, # Limit length for latency
                "top_k": 20,
                "top_p": 0.9,
            }
        }
        try:
            # Short timeout for faster failure handling
            response = requests.post(OLLAMA_URL, json=payload, timeout=20)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"[!] Ollama Translation Service Error: {str(e)}")
            return ""

    def detect_language(self, text: str) -> str:
        """
        Reliable script-based detection for Tamil, Hindi, and English.
        Zero latency and 100% accuracy for these specific scripts.
        """
        if not text:
            return 'en'
            
        # Tamil Unicode Range: 0B80–0BFF
        if re.search(r'[\u0B80-\u0BFF]', text):
            return 'ta'
        
        # Devanagari (Hindi) Unicode Range: 0900–097F
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
            
        # Default to English (Latin script)
        return 'en'

    def translate_to_english(self, text: str) -> str:
        """Translates non-English text to English using the LLM's multilingual knowledge."""
        if not text: return ""
        
        lang_code = self.detect_language(text)
        if lang_code == 'en':
            return text
            
        lang_name = self.supported_languages.get(lang_code, "Unknown")
        print(f"[*] Translating from {lang_name} to English...")
        
        prompt = f"""Task: Translate {lang_name} to English.
Return ONLY the English translation. No preamble or other text.

Input Text: {text}
English Translation:"""
        
        return self._call_ollama(prompt, num_predict=256)

    def translate_to_user_language(self, text: str, target_lang_code: str) -> str:
        """High-speed, high-fluency clinical translation (Single Pass)."""
        if not text or target_lang_code == 'en' or target_lang_code not in self.supported_languages:
            return text
            
        # 1. Check Cache (Zero Latency)
        cache_key = f"{target_lang_code}:{text}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # 2. Check Bypass Dictionary (Near-Zero Latency)
        for en_phrase, target_phrase in self.bypass.get(target_lang_code, {}).items():
            if en_phrase.lower() in text.lower() and len(text) < len(en_phrase) + 5:
                return target_phrase
                
        lang_name = self.supported_languages.get(target_lang_code)
        
        # 3. Few-Shot Context for High Fluency
        few_shot = {
            'Tamil': """Examples:
English: 0 to 10 on a scale.
Tamil: 0 முதல் 10 வரையிலான அளவுகோல்.
English: When did your symptoms start?
Tamil: உங்கள் அறிகுறிகள் எப்போது தொடங்கின?
English: Where is the pain?
Tamil: வலி எங்கே இருக்கிறது?""",
            'Hindi': """Examples:
English: 0 to 10 on a scale.
Hindi: 0 से 10 के पैमाने पर।
English: When did your symptoms start?
Hindi: आपके लक्षण कब शुरू हुए?
English: Where is the pain?
Hindi: दर्द कहाँ है?"""
        }.get(lang_name, "")

        # Target glossary for context
        terms = self.glossary.get(target_lang_code, {})
        glossary_context = f"Internal Glossary: {', '.join([f'{k}:{v}' for k, v in terms.items()])}."

        prompt = f"""Task: Translate the clinical text precisely into {lang_name}.
{few_shot}

{glossary_context}
- Tone: Empathetic doctor.
- Rule: Return ONLY the {lang_name} translation.
- Script Check: No Arabic/Urdu question marks.

English: {text}
{lang_name} Translation:"""
            
        result = self._call_ollama(prompt, num_predict=512)
        
        # Fast Post-Cleanup
        result = result.replace('؟', '?').strip()
        
        # Store in Cache
        self.cache[cache_key] = result
        return result

    def _refine_translation(self, text: str, lang_name: str) -> str:
        """
        Uses a second NLP pass to refine the translation for natural flow,
        grammatical correctness, and removal of mixed-script hallucinations.
        """
        if not text or len(text) < 10: return text
        
        # Clean known script hallucinations immediately (e.g., Urdu/Arabic question marks in Tamil)
        text = text.replace('؟', '?')
        
        # Get target glossary terms for context
        lang_code = 'ta' if lang_name == 'Tamil' else 'hi' if lang_name == 'Hindi' else None
        glossary_context = ""
        if lang_code and lang_code in self.glossary:
            terms = self.glossary[lang_code]
            glossary_context = f"Ensure you use these natural medical terms: {', '.join([f'{k}:{v}' for k, v in terms.items()])}."

        prompt = f"""Refine the following {lang_name} translation to sound as natural and professional as a doctor speaking to a patient.
- Fix grammar and clunky phrasing.
- Remove any characters not belonging to the {lang_name} script (like '؟').
- {glossary_context}
- Return ONLY the refined {lang_name} text, NO English.

Draft Translation: {text}
Refined {lang_name}:"""
        
        # Lower latency refinement with temperature 0.0
        return self._call_ollama(prompt, num_predict=len(text) + 128)

# Singleton instance
translator = TranslationService()

if __name__ == "__main__":
    # Test cases
    test_tamil = "எனக்கு தோல் வலி இருக்கிறது"
    test_hindi = "मेरे कंधे में दर्द है"
    
    print(f"Detecting Tamil: {translator.detect_language(test_tamil)}")
    print(f"Translate Tamil to EN: {translator.translate_to_english(test_tamil)}")
    
    structured_en = """1. What is happening?
- Rotator cuff injury.

2. What you should do?
- Apply ice and rest.

3. What to avoid?
- Lifting heavy weights.

4. When to see a doctor?
- If pain is severe."""

    print(f"\nTranslating structured guide to Hindi:")
    print(translator.translate_to_user_language(structured_en, 'hi'))
