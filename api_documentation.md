# API Architecture & Call Locations

This document maps the communication flow between the frontend, backend, and external LLM services in the MedAssist pipeline.

## 1. Frontend to Backend (React → Flask)

The frontend communicates with the Flask server through `axios` calls. These calls are proxied through the Vite dev server to `http://localhost:8000`.

### `POST /analyze`
- **Source File**: [ai-shoulder-assistant.jsx](file:///e:/Medathon/ai-shoulder-assistant.jsx)
- **Primary Function**: `sendMessage` (Lines 185–208)
- **Description**: 
    - Sends user input (text, images, or 3D positions) to the clinical orchestration engine.
    - **Payload Fields**:
        - `input` (String): The user's text message.
        - `image` (File): Optional image upload for MedCLIP analysis.
        - `language` (String): Preferred language code (`en`, `hi`, `ta`).
        - `pain_location` (String): Precise anatomical region identified via the 3D model.
    - Uses `FormData` when an image is attached.
    - Uses JSON for simple text/3D-click interactions.

---

## 2. Backend Gateway (Flask Endpoints)

The Flask server acts as the primary orchestrator, routing requests to the specialized medical agents.

### `api_server.py`
- **Location**: [api_server.py](file:///e:/Medathon/api_server.py)
- **Endpoints**:
    - `GET /health` (Line 57): Basic status check.
    - `POST /analyze` (Line 62): The main entry point. It triggers the following internal pipeline:
        1. **Language Detection**: Automatically detects user language and overrides defaults if necessary.
        2. **3D Context Injection**: If `pain_location` is present, it is injected into the reasoning prompt as virtual interaction context.
        3. **Translation**: `translator.translate_to_english` in `translation_utils.py`.
        4. **Intake**: `intake_agent.process_turn` in `intake_assistant.py`.
        5. **Reasoning**: `reasoning_engine.generate_report` in `reasoning_engine.py`.
        6. **RAG Integration**: `run_rag_pipeline` in `hybrid_rag.py`.

---

## 3. Specialized Pipeline Modules (Internal Logic)

These files handle the core medical logic and external model interactions.

### Intake Assistant
- **File**: [intake_assistant.py](file:///e:/Medathon/intake_assistant.py)
- **API Target**: Local **Ollama** API (`qwen2.5:7b-instruct`)
- **Key Calls**: 
    - `_extract_hopi`: Parses medical state from raw text.
    - `_generate_follow_up`: Requests clinical follow-up questions from the LLM.

### Hybrid Reasoning Engine
- **File**: [reasoning_engine.py](file:///e:/Medathon/reasoning_engine.py)
- **API Target**: Local **Ollama** API
- **Key Calls**: 
    - `generate_report`: Generates the final 4-point structured clinical assessment card.

### Hybrid RAG Pipeline
- **File**: [hybrid_rag.py](file:///e:/Medathon/hybrid_rag.py)
- **API Target**: Local LLM orchestrator.
- **Key Calls**: Runs the final synthesized report using the provided vector store context.

---

## 4. Multi-Modal Vision Processing

### MedCLIP Processor
- **File**: [medclip_processor.py](file:///e:/Medathon/medclip_processor.py)
- **Logic**: Process raw image bytes to extract clinical insights.
- **Location**: Called by `api_server.py` at the start of the `/analyze` turn if an image is detected.

---

## 5. Visual 3D Anatomical Interaction

### Shoulder Model Viewer
- **File**: [ShoulderModel.jsx](file:///e:/Medathon/ShoulderModel.jsx)
- **Tech**: Sketchfab Viewer API 1.12.1
- **Interaction**: 
    - Loads model `94489e01f40548b5a0b4f0a6477c36a7`.
    - Implements **Recursive Node Mapping**: Navigates the scene graph (parents up to 3 levels) to find medical terms if the direct hit returns generic labels like "Mat".
    - Implements **Annotation Snapping**: Prioritizes curated Sketchfab annotations within a 10.0 unit radius of a click.
    - Resulting label is sent to `/analyze` as `pain_location`.
