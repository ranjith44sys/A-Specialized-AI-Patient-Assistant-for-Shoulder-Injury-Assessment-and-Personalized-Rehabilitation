import json
import os
import datetime
import uuid
import requests
import chromadb
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

# --- Configuration ---
PERSISTENT_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "knowledge_base"
DENSE_MODEL_NAME = "all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "medllama2"
OUTPUT_DIR = "./hybrid_rag_outputs"

class HybridRAGPipeline:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        print(f"[*] Initializing Dense Retriever ({DENSE_MODEL_NAME})...")
        self.dense_model = SentenceTransformer(DENSE_MODEL_NAME)
        
        print(f"[*] Initializing Reranker ({RERANKER_MODEL_NAME})...")
        self.reranker = CrossEncoder(RERANKER_MODEL_NAME)
        
        self.client = chromadb.PersistentClient(path=PERSISTENT_DIRECTORY)
        self.collection = self.client.get_collection(name=COLLECTION_NAME)

    def build_query(self, intake_path: str, reasoning_path: str) -> str:
        """Step 1: Construct a rich query from clinical reports."""
        with open(intake_path, 'r', encoding='utf-8') as f:
            intake = json.load(f)
        with open(reasoning_path, 'r', encoding='utf-8') as f:
            reasoning = json.load(f)
            
        # Combine key clinical features
        query_parts = [
            f"Condition: {reasoning.get('final_condition', '')}",
            f"Stage: {reasoning.get('final_stage', '')}",
            f"Symptoms: {intake.get('pain_nature', '')} in {intake.get('pain_location', '')}",
            f"Onset: {intake.get('onset', '')}",
            f"Functional Limitations: {intake.get('functional_limitations', '')}"
        ]
        
        if reasoning.get('red_flag_alert'):
            query_parts.append(f"Red Flags: {intake.get('red_flags', '')}")
            
        return " | ".join([p for p in query_parts if p.strip()])

    def dense_retrieval(self, query: str, top_k: int = 10) -> List[Dict]:
        """Step 2: Semantic search using ChromaDB."""
        print(f"[*] Executing Dense Retrieval for: {query[:50]}...")
        query_embedding = self.dense_model.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "score": 1 - results['distances'][0][i], # Convert distance to similarity
                    "method": "dense"
                })
        return formatted_results

    def sparse_retrieval(self, query: str, top_k: int = 10) -> List[Dict]:
        """Step 3: Keyword search using BM25."""
        print(f"[*] Executing Sparse Retrieval...")
        
        # Fetch all documents from Chroma for BM25
        all_docs = self.collection.get(include=["documents", "metadatas"])
        documents = all_docs['documents']
        metadatas = all_docs['metadatas']
        
        if not documents:
            return []
            
        # Tokenize
        tokenized_corpus = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Get top indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        formatted_results = []
        for i in top_indices:
            if scores[i] > 0:
                formatted_results.append({
                    "content": documents[i],
                    "metadata": metadatas[i],
                    "score": float(scores[i]),
                    "method": "sparse"
                })
        return formatted_results

    def rerank_results(self, query: str, candidates: List[Dict], top_k: int = 3) -> List[Dict]:
        """Step 4 & 5: Merge and Rerank results."""
        print(f"[*] Reranking {len(candidates)} candidates...")
        
        # Deduplicate by content
        unique_candidates = {}
        for cand in candidates:
            unique_candidates[cand['content']] = cand
        
        deduped_list = list(unique_candidates.values())
        
        # Prepare pairs for cross-encoder
        pairs = [[query, cand['content']] for cand in deduped_list]
        rerank_scores = self.reranker.predict(pairs)
        
        for i, score in enumerate(rerank_scores):
            deduped_list[i]['rerank_score'] = float(score)
            
        # Sort and select top K
        final_results = sorted(deduped_list, key=lambda x: x['rerank_score'], reverse=True)[:top_k]
        return final_results

    def generate_response(self, query: str, context_docs: List[Dict], intake_path: str, reasoning_path: str) -> str:
        """Step 6 & 7: LLM Generation with Context."""
        print(f"[*] Generating Final LLM Response...")
        
        with open(intake_path, 'r', encoding='utf-8') as f:
            intake_data = f.read()
        with open(reasoning_path, 'r', encoding='utf-8') as f:
            reasoning_data = f.read()

        context_text = "\n\n".join([f"Source: {d['metadata'].get('source', 'Unknown')}\n{d['content']}" for d in context_docs])
        
        prompt = f"""[INST] <<SYS>>
You are a highly accurate Clinical Decision Support System.
You must strictly adhere to the provided PATIENT DATA.
HALLUCINATION IS STRICTLY FORBIDDEN (0% tolerance).

### PROHIBITED ACTIONS ###
1. DO NOT invent or assume patient demographics (Age, Gender, Name) if they are not explicitly provided in the "CURRENT PATIENT DATA".
2. If age and gender are missing, refer to the individual ONLY as "The patient".
3. DO NOT confuse details from the "GENERAL MEDICAL GUIDELINES" (research populations or case studies) with the current patient's profile.
4. DO NOT assume physical exam findings or imaging results if not present in the "CURRENT PATIENT DATA".
5. Provide your analysis in valid JSON format only.
<</SYS>>

### CURRENT PATIENT DATA ###
{intake_data}

### CLINICAL REASONING LOGIC ###
{reasoning_data}

### GENERAL MEDICAL GUIDELINES (DO NOT APPLY TO PATIENT PROFILE) ###
{context_text}

TASK:
Based on the evidence above, generate a clinical insight report.
Ensure 0% hallucination regarding patient demographics.
You MUST cite the source name (e.g., [Source: Document Name]) for each key observation in the "insights" section.

REQUIRED JSON FORMAT:
{{
  "summary": "...",
  "insights": "Evidence-based observations with [Source: Original Title] citations...",
  "treatment_steps": ["...", "..."],
  "sources_used": ["Exact Title from Context 1", "Exact Title from Context 2"]
}}
[/INST]"""
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": 1024,
                "num_ctx": 4096,
                "temperature": 0.3
            }
        }
        
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            raw_res = response.json().get("response", "{}")
            
            # Post-processing: Programmatic Enforcement (0% Hallucination)
            try:
                data = json.loads(raw_res)
            except:
                data = {"raw_output": raw_res}
                
            # Force the exact disclaimer
            data["disclaimer"] = "This is a computer-generated clinical insight, not a replacement for professional medical advice."
            
            # Demographic Scrubber: Remove common hallucinated placeholders if not in intake
            scrub_patterns = ["35-year-old", "35 year old", "male", "female", "man", "woman"]
            intake_lower = intake_data.lower()
            import re
            for key in ["summary", "insights"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        # Handle case where LLM returns a list of strings
                        new_list = []
                        for item in val:
                            if isinstance(item, str):
                                for pattern in scrub_patterns:
                                    regex = re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)
                                    if regex.search(item) and pattern not in intake_lower:
                                        item = regex.sub("the patient", item)
                                new_list.append(item)
                            else:
                                new_list.append(item)
                        data[key] = new_list
                    elif isinstance(val, str):
                        # Original string handling
                        for pattern in scrub_patterns:
                            regex = re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)
                            if regex.search(val) and pattern not in intake_lower:
                                val = regex.sub("the patient", val)
                        data[key] = val
            
            # Source Cleaner: Add explicit sources_used if missing, and clean names
            if "sources_used" not in data or not data["sources_used"]:
                sources = set()
                for doc in context_docs:
                    src = doc['metadata'].get('source', 'Unknown')
                    # Clean internal suffixes like '_chunks_1.json'
                    clean_src = src.replace("_chunks", "").replace(".json", "").replace("_1", "").strip()
                    sources.add(clean_src)
                data["sources_used"] = list(sources)
            
            return json.dumps(data)
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def save_outputs(self, query: str, retrieved_docs: List[Dict], final_response: str):
        """Step 8: Persistence."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = str(uuid.uuid4())[:8]
        
        output_data = {
            "timestamp": timestamp,
            "query_used": query,
            "retrieved_documents": retrieved_docs,
            "final_llm_response": final_response
        }
        
        filename = f"rag_result_{timestamp}_{run_id}.json"
        path = os.path.join(self.output_dir, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4)
            
        print(f"[+] Results saved to: {path}")

def run_pipeline(intake_file: str, reasoning_file: str):
    pipeline = HybridRAGPipeline()
    
    # 1. Build Query
    query = pipeline.build_query(intake_file, reasoning_file)
    print(f"\n[QUERY]: {query}\n")
    
    # 2. Dense Retrieval
    dense_results = pipeline.dense_retrieval(query)
    
    # 3. Sparse Retrieval
    sparse_results = pipeline.sparse_retrieval(query)
    
    # 4 & 5. Merge & Rerank
    candidates = dense_results + sparse_results
    final_docs = pipeline.rerank_results(query, candidates, top_k=3)
    
    print("\n--- Top Retrieved Documents ---")
    for i, doc in enumerate(final_docs):
        print(f"{i+1}. [{doc['method']}] Score: {doc.get('rerank_score', 'N/A'):.4f} - {doc['content'][:100]}...")
        
    # 6 & 7. Generate Response
    response = pipeline.generate_response(query, final_docs, intake_file, reasoning_file)
    
    # 8. Store
    pipeline.save_outputs(query, final_docs, response)
    
    print("\n--- Final Clinical Insights ---")
    try:
        # Try to pretty-print if it's JSON
        parsed_res = json.loads(response)
        print(json.dumps(parsed_res, indent=2))
    except:
        print(response)

def get_latest_file(directory: str, extension: str = ".json") -> str:
    """Helper to find the most recently created file in a directory."""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(extension)]
    if not files:
        raise FileNotFoundError(f"No {extension} files found in {directory}")
    return max(files, key=os.path.getctime)

if __name__ == "__main__":
    try:
        # Use a specifically selected set of files or the absolute latest
        LATEST_INTAKE = get_latest_file("intake_logs")
        LATEST_REASONING = get_latest_file("reasoning_reports")
        
        print(f"[*] Processing Latest Intake: {LATEST_INTAKE}")
        print(f"[*] Processing Latest Reasoning: {LATEST_REASONING}")
        
        run_pipeline(LATEST_INTAKE, LATEST_REASONING)
    except Exception as e:
        print(f"[!] Error: {str(e)}")
