import json
import os
from reasoning_engine import HybridReasoningEngine

def test_scenarios():
    engine = HybridReasoningEngine()
    
    scenarios = [
        {
            "name": "Scenario A: Acute Severe Shoulder Injury",
            "data": {
                "condition": "Shoulder pain",
                "onset": "Sudden",
                "pain_severity": "10",
                "duration": "1 day",
                "pain_nature": "Sharp",
                "trigger_event": "Lifting a 50kg weight",
                "functional_limitations": "Inability to lift arm",
                "red_flags": []
            }
        },
        {
            "name": "Scenario B: Chronic Neurological Issue",
            "data": {
                "condition": "Lower Back pain",
                "onset": "Gradual",
                "pain_severity": "4",
                "duration": "6 months",
                "pain_nature": "Dull ache with tingling in left leg",
                "trigger_event": "",
                "functional_limitations": "Limited walking distance",
                "red_flags": ["tingling in left leg"]
            }
        },
        {
            "name": "Scenario C: Subacute Case with Red Flag Alert",
            "data": {
                "condition": "Cervical pain",
                "onset": "Sudden",
                "pain_severity": "6",
                "duration": "3 weeks",
                "pain_nature": "Sharp",
                "trigger_event": "Minor car accident",
                "functional_limitations": "Neck stiffness",
                "red_flags": ["numbness in fingers"]
            }
        }
    ]

    print("--- Clinical Reasoning Engine Test Suite ---")
    for scenario in scenarios:
        print(f"\n[*] Testing {scenario['name']}...")
        result = engine.analyze(scenario['data'])
        
        print(f"    - Final Condition: {result['final_condition']}")
        print(f"    - Final Stage: {result['final_stage']}")
        print(f"    - Validation: {result['validation_status']}")
        print(f"    - Red Flag Alert: {result['red_flag_alert']}")
        print(f"    - Explanation: {result['explanation'][:100]}...")

if __name__ == "__main__":
    test_scenarios()
