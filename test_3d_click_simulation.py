import requests
import json

BASE_URL = "http://localhost:8000"

def test_3d_click():
    print("Testing 3D Click Interaction Simulation...")
    
    # 0. Health check
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except:
        print("[!] Error: API server not running on localhost:8000. Start it with 'python api_server.py'")
        return

    # 1. Simulate selecting a region (e.g., Rotator Cuff) on turn 1
    payload = {
        "input": "",
        "language": "en",
        "pain_location": "Rotator Cuff"
    }
    
    print(f"[*] Sending 3D click payload: {json.dumps(payload)}")
    response = requests.post(f"{BASE_URL}/analyze", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("\n--- API Success ---")
        print(f"Detected Language: {data.get('language')}")
        
        # Check if follow-up questions ask about location
        fups = data.get('follow_up_questions', [])
        print("\nFollow-up Questions:")
        for q in fups:
            print(f"- {q}")
            if "where" in q.lower() or "location" in q.lower():
                print("[!] FAILURE: AI asked about location despite 3D input!")
                return
        
        print("\n[+] SUCCESS: AI correctly skipped the location question.")
    else:
        print(f"[!] Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_3d_click()
