import os
import time
from pdf_pipeline import process_folder
from vector_store import run_storage_pipeline

def main():
    """
    Main entry point for the Knowledge Base Ingestion Pipeline.
    1. Extracts and chunks text from PDFs in 'Data_sources'.
    2. Generates embeddings and stores them in ChromaDB.
    """
    print("=" * 40)
    print("🚀 Knowledge Base Ingestion Pipeline")
    print("=" * 40)
    
    # Define paths
    input_folder = "Data_sources"
    chunks_folder = "chunks"
    vector_db_folder = "chroma_db"
    
    # Start timer
    start_time = time.time()
    
    # --- Step 1: PDF Chunking ---
    print("\n--- [Step 1/2] PDF Extraction & Chunking ---")
    if not os.path.exists(input_folder):
        print(f"[!] Error: Input folder '{input_folder}' not found. Please add your PDFs there.")
        return
        
    process_folder(input_folder, output_dir=chunks_folder, format='json')
    
    # --- Step 2: Vector Storage ---
    print("\n--- [Step 2/2] Embedding Generation & Vector Storage ---")
    if not os.listdir(chunks_folder):
        print(f"[!] Error: No chunks found in '{chunks_folder}'. Skipping storage.")
        return
        
    run_storage_pipeline(source_folder=chunks_folder)
    
    # End timer
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 40)
    print(f"✅ Ingestion Complete in {duration:.2f} seconds.")
    print(f"📁 Source: {input_folder}")
    print(f"📁 Chunks: {chunks_folder}")
    print(f"📁 Vector DB: {vector_db_folder}")
    print("=" * 40)

if __name__ == "__main__":
    main()
