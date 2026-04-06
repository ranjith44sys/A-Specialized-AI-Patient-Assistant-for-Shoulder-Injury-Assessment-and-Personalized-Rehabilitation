import os
import json
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional

# --- Configuration ---
PERSISTENT_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    """
    Generates embeddings for a list of text chunks using Hugging Face Sentence Transformers.
    
    Args:
        chunks: List of text strings.
        
    Returns:
        List of embedding vectors (list of floats).
    """
    print(f"[*] Generating embeddings using '{EMBEDDING_MODEL_NAME}'...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # Generate embeddings and convert to list format if necessary
    embeddings = model.encode(chunks, convert_to_numpy=True).tolist()
    return embeddings

def load_chunks_from_folder(folder_path: str) -> tuple[List[str], List[Dict]]:
    """
    Reads all .json chunk files from a directory.
    
    Returns:
        A tuple of (list of text chunks, list of metadata dictionaries).
    """
    all_chunks = []
    all_metadata = []
    
    if not os.path.isdir(folder_path):
        print(f"[!] Error: '{folder_path}' is not a directory.")
        return [], []

    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.json')]
    if not files:
        print(f"[!] No JSON chunk files found in '{folder_path}'.")
        return [], []

    print(f"[*] Loading chunks from {len(files)} files in '{folder_path}'...")
    
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                file_chunks = data.get("chunks", [])
                for i, chunk in enumerate(file_chunks):
                    all_chunks.append(chunk)
                    all_metadata.append({
                        "source": filename,
                        "chunk_index": i
                    })
        except Exception as e:
            print(f"Warning: Failed to load {filename}: {str(e)}")

    print(f"[+] Loaded total of {len(all_chunks)} chunks.")
    return all_chunks, all_metadata

def store_in_chroma(chunks: List[str], embeddings: List[List[float]], metadata: Optional[List[Dict]] = None):
    """
    Stores chunks and their corresponding embeddings in a persistent Chroma vector database.
    
    Args:
        chunks: List of original text chunks.
        embeddings: List of embedding vectors.
        metadata: Optional list of dictionaries containing metadata for each chunk.
    """
    # Initialize persistent client
    client = chromadb.PersistentClient(path=PERSISTENT_DIRECTORY)
    
    # Delete and recreate the collection for a fresh re-index if requested
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except:
        pass # Collection didn't exist
    
    # Create or get the collection
    collection = client.create_collection(name=COLLECTION_NAME)
    
    # Generate unique IDs using UUID
    ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
    
    # Prepare metadata if not provided
    if metadata is None:
        metadata = [{"index": i} for i in range(len(chunks))]

    print(f"[*] Storing {len(chunks)} chunks in Chroma DB collection: '{COLLECTION_NAME}'...")
    
    # Add to collection
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadata
    )
    
    print(f"[+] Successfully stored {len(chunks)} chunks.")
    print(f"[+] Persistent database located at: {os.path.abspath(PERSISTENT_DIRECTORY)}")

def run_storage_pipeline(source_folder: str = "chunks"):
    """
    Orchestrates loading, embedding, and storing process.
    """
    # 1. Load Chunks
    chunks, metadata = load_chunks_from_folder(source_folder)
    if not chunks:
        return

    # 2. Generate Embeddings
    embeddings = generate_embeddings(chunks)
    
    # 3. Store in Chroma
    store_in_chroma(chunks, embeddings, metadata=metadata)

if __name__ == "__main__":
    print("--- Knowledge Base Vector Storage ---")
    # Defaulting to the 'chunks' folder as requested
    run_storage_pipeline("chunks")
