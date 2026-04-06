import io
import traceback
from PIL import Image
from typing import Dict, Any, List

# Try to import torch and transformers, gracefully fail if missing
try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

# Default Model - MedCLIP or a biomedical CLIP variant
# flaviagiammarino/pubmed-clip-vit-base-patch32 is a popular open-source medical clip model
MODEL_NAME = "flaviagiammarino/pubmed-clip-vit-base-patch32"

# Shoulder specific tags as requested
SHOULDER_TAGS = [
    "normal shoulder joint",
    "rotator cuff tear",
    "shoulder dislocation",
    "bone fracture",
    "inflammation and swelling",
    "tendonitis",
    "bursitis"
]

class MedCLIPProcessor:
    def __init__(self):
        self.device = "cuda" if HAS_DEPENDENCIES and torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.is_loaded = False
        
    def load_model(self):
        """Loads the model from HuggingFace automatically on first run."""
        if not HAS_DEPENDENCIES:
            raise ImportError("PyTorch or Transformers not installed. Please run: pip install torch transformers Pillow")
        
        if self.is_loaded:
            return
            
        print(f"[*] Loading MedCLIP Model ({MODEL_NAME}) on {self.device}...")
        try:
            self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
            self.is_loaded = True
            print("[+] MedCLIP Model loaded successfully.")
        except Exception as e:
            print(f"[!] Failed to load MedCLIP Model: {e}")
            raise e

    def process_image(self, file_bytes: bytes) -> Image.Image:
        """Processes an image from bytes directly in memory."""
        try:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            # Basic validation
            image.verify() # verifies it's an image
            # re-open because verify() can leave the file pointer in a bad state
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return image
        except Exception as e:
            raise ValueError(f"Invalid image format or corrupted file: {e}")

    def extract_image_features(self, image: Image.Image, threshold: float = 0.2) -> Dict[str, Any]:
        """Extracts text predictions from the image."""
        if not self.is_loaded:
            self.load_model()
            
        # Format the tags to improve zero-shot accuracy
        text_prompts = [f"an x-ray or MRI showing {tag}" for tag in SHOULDER_TAGS]
        
        inputs = self.processor(
            text=text_prompts, 
            images=image, 
            return_tensors="pt", 
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image  # image-text similarity score
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
            
        # Map back to original tags and filter by probability threshold
        findings = []
        scores = []
        for tag, prob in zip(SHOULDER_TAGS, probs):
            if prob >= threshold:
                findings.append(tag)
                scores.append(float(prob))
                
        # If nothing passed the threshold, take the highest one anyway if it's kinda close
        if not findings and len(probs) > 0:
            best_idx = probs.argmax()
            if probs[best_idx] > 0.1:
                findings.append(SHOULDER_TAGS[best_idx])
                scores.append(float(probs[best_idx]))

        return {
            "image_findings": findings,
            "confidence_scores": scores
        }

    def convert_to_text(self, findings: List[str]) -> str:
        """Translates extracted findings into natural language."""
        if not findings:
            return ""
        
        clean_findings = [f.replace("normal shoulder joint", "a normal presentation without major defects") for f in findings]
        
        if len(clean_findings) == 1:
            return f"Medical image analysis suggests {clean_findings[0]}."
        else:
            joined = ", ".join(clean_findings[:-1]) + f" and {clean_findings[-1]}"
            return f"Medical image analysis highlights possible {joined}."

    def get_image_insights(self, file_bytes: bytes) -> str:
        """End-to-end pipeline for memory bytes."""
        try:
            image = self.process_image(file_bytes)
            results = self.extract_image_features(image)
            text_insights = self.convert_to_text(results["image_findings"])
            return text_insights
        except Exception as e:
            print(f"[!] Image Processing Error via MedCLIP: {e}")
            traceback.print_exc()
            return ""

def merge_with_user_input(text_input: str, image_insights: str) -> str:
    """Combines user text input with MedCLIP insights."""
    if not image_insights:
        return text_input.strip()
        
    combined = f"{text_input.strip()}\n\n[SUPPORTING EVIDENCE FROM UPLOADED IMAGE: {image_insights}]"
    return combined.strip()

# Singleton instance to expose
medclip_processor = MedCLIPProcessor()
