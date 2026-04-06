# Hybrid Clinical Reasoning Engine Implementation Plan

This plan outlines the development of a clinical reasoning module that classifies patient conditions and determines their diagnostic stage (Acute/Chronic/Severe) using a multi-layered hybrid approach.

## Goal
To build a `reasoning_engine.py` script that processes structured patient data, applies rule-based logic, integrates ML predictions (where available), and validates the final output using an LLM (Ollama).

## Proposed Changes

### [NEW] [reasoning_engine.py](file:///e:/Medathon/reasoning_engine.py)

#### 1. Rule-Based Segment
- Implement a series of boolean matches based on the user's provided criteria:
  - **Acute**: `duration < 2 weeks` + `sudden onset` + `trigger_event`.
  - **Chronic**: `duration > 6 weeks` + `gradual onset`.
  - **Neurological**: Presence of "numbness" or "tingling" in `pain_nature` or `red_flags`.
  - **Severe**: `pain_severity >= 8` OR major `functional_limitations`.

#### 2. ML Integration Layer
- The engine will accept optional `ml_prediction` and `ml_confidence` parameters.
- If `rule_confidence` is "Low", the system will default to the ML prediction.

#### 3. Stage 
- Logic to map combinations of duration and severity into a unified `final_stage` (Acute / Subacute / Chronic / Severe).

#### 4. LLM Validation (Ollama)
- Use the local **Qwen 2.5 7B** (or Llama 3) to:
  - Review the rule-based conclusion.
  - Check for contradictions (e.g., "Severe" pain but "No functional limitations").
  - Produce the final JSON output with a detailed `explanation`.

---

## 3. Workflow Example

1. **Input**: Load `intake_schema.json` (Shoulder pain, 3 weeks, 8/10 severity, numbness).
2. **Rule Step**: Categorized as **Severe** (due to severity) and **Subacute** (3 weeks). Confidence: Medium.
3. **ML Step**: If ML predicts "Rotator Cuff Tear" with 0.95 confidence, it may be used.
4. **LLM Validation**: Ollama reviews the data, confirms the "Severe" status due to numbness (neurological) and high pain, and outputs the final report.

---

## 4. Verification Plan

### Automated Tests
- Create a `test_reasoning.py` with mock patient scenarios:
  - **Scenario A**: Clear Acute Injury (Sudden, 4 days, 10/10 pain).
  - **Scenario B**: Vague Chronic Issue (Gradual, 1 year, 3/10 pain).
  - **Scenario C**: Red Flag Case (Numbness included).

### Manual Verification
- Run the engine on existing `intake_logs/output_*.json` files to see real-world performance on previous sessions.
