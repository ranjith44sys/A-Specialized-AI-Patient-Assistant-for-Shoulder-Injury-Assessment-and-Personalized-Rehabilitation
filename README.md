# Medathon: Hybrid Clinical Decision Support System

A state-of-the-art Clinical Decision Support System (CDSS) designed for medical practitioners and patients. It combines rule-based clinical logic with advanced RAG (Retrieval-Augmented Generation), multimodal analysis, and native language support to provide highly accurate, evidence-based insights with **0% hallucination tolerance**.

## 🚀 Key Features

- **Interactive 3D Anatomical Localization**: High-precision 3D shoulder model for precise pain pinpointing, using recursive scene graph traversal and Sketchfab annotations for medical-grade terminology.
- **Native Localization**: Generates patient-facing responses natively in English, Hindi, and Tamil, eliminating translation leakage and leveraging a specialized model.
- **End-to-End Orchestration**: Seamless state management between Intake, Reasoning, RAG, and Output phases via an intelligent API and orchestrator. 
- **Multimodal AI**: Seamless image-to-text clinical analysis using MedCLIP for patient image and scan assessment.
- **Hybrid Reasoning Engine**: Combines deterministic clinical rules with MedLLaMA2 validation for robust classification of injuries and severity.
- **Advanced RAG Pipeline**: Utilizes both Dense (semantic) and Sparse (keyword) retrieval, coupled with PDF parsing, followed by neural reranking with a Cross-Encoder for maximum relevance.
- **Hallucination Hardening**: Programmatic enforcement and structural prompt isolation to prevent the invention of patient demographics (age/gender).
- **Dynamic Frontend UX**: Interactive Chat UI separated into conversational intake balloons and premium structured 4-point clinical assessment cards for the final report.

---

## 🛠️ System Architecture

### 1. Frontend & UI Layer (`frontend/`, `ai-shoulder-assistant.jsx`, `main.jsx`)
- **Role**: Modern user interface and user interaction bridge.
- **Logic**: Separates conversational intake chat from structured clinical guidance.
- **Tech**: React 19, Vite, Tailwind CSS v4.

### 2. 3D Localization Layer (`ShoulderModel.jsx`)
- **Role**: Visual pain pinpointing and anatomical identification.
- **Features**: Embedded Sketchfab viewer with custom recursive node mapping and annotation sniffing to identify precise surgical regions.

### 3. API & Orchestration Layer (`api_server.py`, `orchestrator.py`)
- **Role**: Process lifecycle, orchestration, and seamless data flow. 
- **Features**: Robust session management, state-reset logic, and routing down the pipeline.

### 4. Intake Layer (`intake_assistant.py`)
- **Role**: Conversational data gathering.
- **Storage**: Extracts structured data into `intake_logs/`.
- **Schema**: Uses `intake_schema.json` to ensure consistency.

### 5. Multimodal Layer (`medclip_processor.py`)
- **Role**: Analyzes uploaded patient images or scans.
- **Features**: Translates visual clinical indicators into textual context for reasoning.

### 6. Knowledge Base & PDF Pipeline (`vector_store.py`, `pdf_pipeline.py`)
- **Role**: Persistent storage of semantic knowledge and data ingestion of clinical PDF guidelines.
- **Database**: Persistent ChromaDB vector store and Rank-BM25 matching.

### 7. Clinical Reasoning & RAG Synthesis (`reasoning_engine.py`, `hybrid_rag.py`)
- **Role**: Core intelligence layer.
- **Features**: Hybrid classification (Rules + LLM), Hybrid Search (Dense + Sparse) + Reranking.
- **Models**: MiniLM for embeddings/reranking, MedLLaMA2 for clinical synthesis.

### 8. Native Patient Responder (`patient_responder.py`, `translation_utils.py`)
- **Role**: Final output formatting and translation into the patient's language.
- **Structure**: Generates a 4-point guide:
  1. What is happening?
  2. What you should do?
  3. What to avoid?
  4. When to see a doctor?

---

## 💻 Tech Stack

### Frontend
- **React 19** & **Vite**: Fast, modern frontend framework and build tool.
- **Tailwind CSS v4**: Utility-first styling for UI components.
- **Framer Motion**: For smooth and dynamic UI animations.
- **Lucide React**: Clean and consistent iconography.
- **Sketchfab Viewer API**: High-fidelity 3D model rendering and interaction.

### Backend & API
- **Python 3.10+**: Core backend logic.
- **Flask** & **Flask-CORS**: Lightweight RESTful API serving the frontend.
- **PyMuPDF**: Robust PDF documentation ingestion.

### AI & Machine Learning
- **Ollama**: Local and private inference for LLMs.
- **MedLLaMA2**: Clinical reasoning, classification, and RAG synthesis.
- **Qwen2.5 (7B Instruct)**: Conversational data gathering, patient guide rendering, and multilingual translation.
- **MedCLIP**: Multimodal image-to-text clinical analysis.
- **Sentence-Transformers**: Generating dense embeddings and neural reranking.

### Data Storage & Retrieval
- **ChromaDB**: Persistent vector database for semantic knowledge retrieval.
- **Rank-BM25**: Keyword-based sparse retrieval.
- **Scikit-Learn**: Core utilities for machine learning operations.

---

## 🚦 Getting Started

### Prerequisites
- Node.js & npm (for frontend)
- Python 3.10+
- Ollama (running locally)
- Required Python dependencies

### Models Required (Ollama)
- `medllama2`: For clinical reasoning and RAG.
- `qwen2.5:7b-instruct`: For conversational intake and localization.

### Running the Application

To execute the full end-to-end clinical workflow:

```powershell
# 0. Knowledge Base Ingestion (Extract and chunk clinical PDFs)
# Ensure your PDF guidelines are in the 'Data_sources/' directory
python main.py

# 1. Start the Backend API server
python api_server.py

# 2. In a separate terminal, install Node dependencies (if you haven't yet)
npm install

# 3. Start the Vite Frontend Development Server
npx vite
```

Once running, navigate to the local Vite URL (e.g., `http://localhost:5173`) in your browser to begin interaction!

---

## 🛡️ Safety & Disclaimer
This system is a **Decision Support Tool** and not a diagnostic replacement. Every output includes a mandatory safety disclaimer:
> *"This is a computer-generated clinical insight, not a replacement for professional medical advice."*
