import pdfplumber
import re
import json
import os
from typing import List, Optional

# Optional: Using NLTK for better sentence splitting
try:
    import nltk
    from nltk.tokenize import sent_tokenize
    # Ensure punkt is downloaded (uncomment if running for the first time)
    # nltk.download('punkt', quiet=True)
except ImportError:
    nltk = None

def extract_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF file page by page using pdfplumber.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        String containing the raw text from all pages.
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the PDF is empty or cannot be read.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file '{pdf_path}' was not found.")

    raw_text_parts = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                raise ValueError("The PDF file appears to be empty (no pages found).")
            
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    raw_text_parts.append(page_text)
                else:
                    print(f"Warning: Could not extract text from page {i+1}. Skipping.")
                    
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")

    if not raw_text_parts:
        raise ValueError("No text could be extracted from the PDF.")

    return "\n".join(raw_text_parts)

def clean_text(text: str) -> str:
    """
    Cleans raw text by removing noise, unwanted characters, and normalizing.
    
    Args:
        text: The raw string to clean.
        
    Returns:
        Cleaned and normalized string.
    """
    # 1. Remove repetitive headers/footers (simplified: remove lines that look like page numbers)
    # Match patterns like "Page 1 of 10" or just numbers on a single line
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip lines that are just numbers (potential page numbers)
        if re.match(r'^\s*\d+\s*$', line):
            continue
        cleaned_lines.append(line)
    
    text = " ".join(cleaned_lines)

    # 2. Convert to lowercase
    text = text.lower()

    # 3. Remove special symbols (keeping basic punctuation for sentence integrity)
    # Retaining: letters, numbers, spaces, and . ! ? , ; : ' " ( )
    text = re.sub(r'[^a-z0-9\s\.!\?\(\),;:\'\"]', ' ', text)

    # 4. Remove extra whitespaces and newline characters
    text = re.sub(r'\s+', ' ', text)

    # 5. Strip leading and trailing spaces
    return text.strip()

def chunk_text(text: str, min_words: int = 200, max_words: int = 500) -> List[str]:
    """
    Splits cleaned text into chunks of 200-500 words while maintaining sentence integrity.
    
    Args:
        text: The cleaned text string.
        min_words: Minimum target word count per chunk.
        max_words: Maximum word count per chunk.
        
    Returns:
        A list of text chunks.
    """
    # Tokenize into sentences
    if nltk:
        try:
            sentences = sent_tokenize(text)
        except Exception:
            # Fallback if NLTK data isn't loaded
            sentences = re.split(r'(?<=[.!?])\s+', text)
    else:
        # Basic regex split for sentences if NLTK is not available
        sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = sentence.split()
        sentence_word_count = len(sentence_words)

        # If adding this sentence exceeds max_words and we already have a meaningful chunk, store it
        if current_word_count + sentence_word_count > max_words and current_word_count >= min_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_word_count = 0

        current_chunk.append(sentence)
        current_word_count += sentence_word_count

    # Add the last remaining chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def save_chunks(chunks: List[str], output_path: str, format: str = 'json'):
    """Saves chunks to a file in either JSON or TXT format."""
    if format.lower() == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"chunks": chunks, "count": len(chunks)}, f, indent=4)
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(chunks):
                f.write(f"--- Chunk {i+1} ---\n{chunk}\n\n")

def run_pipeline(pdf_path: str, output_file: Optional[str] = None):
    """Orchestrates the extraction, cleaning, and chunking process."""
    try:
        print(f"[*] Extracting text from: {pdf_path}")
        raw_text = extract_text(pdf_path)
        
        print("[*] Cleaning text...")
        cleaned_text = clean_text(raw_text)
        
        print("[*] Creating chunks...")
        chunks = chunk_text(cleaned_text)
        
        print(f"\n[+] Success! Created {len(chunks)} chunks.")
        
        if chunks:
            print("\n--- Sample Chunk (First 200 chars) ---")
            print(chunks[0][:200] + "...")
            
            if output_file:
                fmt = 'json' if output_file.endswith('.json') else 'txt'
                save_chunks(chunks, output_file, format=fmt)
                print(f"\n[+] Chunks saved to: {output_file}")
                
        return chunks

    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        return []

def process_folder(folder_path: str, output_dir: Optional[str] = None, format: str = 'json'):
    """
    Processes all PDF files within a specified folder and its subdirectories.
    
    Args:
        folder_path: Path to the folder containing PDF files.
        output_dir: Directory to save the chunked output files.
        format: Output format ('json' or 'txt').
    """
    if not os.path.isdir(folder_path):
        print(f"[!] Error: '{folder_path}' is not a valid directory.")
        return

    # Create output directory if it doesn't exist
    if not output_dir:
        output_dir = "chunks"
        
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[*] Created output directory: {output_dir}")

    # Discover all PDF files recursively
    pdf_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print(f"[!] No PDF files found in '{folder_path}' or its subdirectories.")
        return

    print(f"[*] Found {len(pdf_files)} PDF files. Starting batch processing...\n")

    for i, pdf_path in enumerate(pdf_files):
        filename = os.path.basename(pdf_path)
        
        # Determine unique output filename
        base_name = os.path.splitext(filename)[0]
        out_ext = f".{format.lower()}"
        out_filename = f"{base_name}_chunks{out_ext}"
        output_path = os.path.join(output_dir, out_filename)
        
        # Handle duplicate filenames in different subfolders
        counter = 1
        while os.path.exists(output_path):
            output_path = os.path.join(output_dir, f"{base_name}_chunks_{counter}{out_ext}")
            counter += 1
        
        print(f"--- Processing [{i+1}/{len(pdf_files)}]: {filename} ---")
        run_pipeline(pdf_path, output_path)
        print("-" * 40 + "\n")

    print(f"[+] Batch processing complete. Results saved in: {output_dir}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract and chunk text from PDF files.")
    parser.add_argument("path", help="Path to a PDF or Folder (defaults to 'Data_sources')", nargs="?", default="Data_sources")
    parser.add_argument("--output", help="Output directory (defaults to 'chunks')", default="chunks")
    parser.add_argument("--format", help="Output format: json or txt", choices=['json', 'txt'], default='json')
    
    args = parser.parse_args()
    
    # If the default folder doesn't exist, try common variations (e.g., 'Data source' vs 'Data_sources')
    input_path = args.path
    if input_path == "Data_sources" and not os.path.exists(input_path):
        if os.path.exists("Data source"):
            input_path = "Data source"
            print(f"[*] Found 'Data source' folder instead of 'Data_sources'. Using it...")

    if os.path.isdir(input_path):
        # Process as a folder
        process_folder(input_path, output_dir=args.output, format=args.format)
    elif os.path.isfile(input_path):
        # Process as a single file
        run_pipeline(input_path, args.output)
    else:
        print(f"[!] Error: '{input_path}' is not a valid file or directory.")
        print("Usage: python pdf_pipeline.py [path] [--output chunks] [--format json]")
