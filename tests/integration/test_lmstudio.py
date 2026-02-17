"""
Test LM Studio API connection
"""
import os
import json
from dotenv import load_dotenv
import requests
import urllib3

# Suppress warnings for localhost
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")
model = os.getenv("LMSTUDIO_MODEL", "lmstudio-community/gpt-oss-20b")

print("="*70)
print("LM STUDIO API TEST")
print("="*70)
print(f"\nBase URL: {base_url}")
print(f"Model: {model}\n")

# Test 1: Check if server is running
print("="*70)
print("TEST 1: Server Connection")
print("="*70)
print(f"Checking if LM Studio is running at {base_url}...")

try:
    # Try to list models first
    models_url = f"{base_url}/v1/models"
    response = requests.get(models_url, timeout=5)

    if response.status_code == 200:
        models_data = response.json()
        available_models = models_data.get("data", [])
        print(f"[OK] Server is running!")
        print(f"Available models: {len(available_models)}")
        for m in available_models[:5]:  # Show first 5
            print(f"  - {m.get('id', 'Unknown')}")
        if len(available_models) > 5:
            print(f"  ... and {len(available_models) - 5} more")
    else:
        print(f"[WARN] Server responded but with status {response.status_code}")

except requests.exceptions.ConnectionError:
    print(f"\n[ERROR] Cannot connect to LM Studio at {base_url}")
    print("\nPossible issues:")
    print("  1. LM Studio is not running")
    print("  2. LM Studio is running on a different port")
    print("  3. Server API is not enabled")
    print("\nTo fix:")
    print("  1. Open LM Studio application")
    print("  2. Load a model (e.g., gpt-oss-20b)")
    print("  3. Enable the API server:")
    print("     - Look for 'Server' or 'API' button in LM Studio")
    print("     - Make sure it's listening on port 1234")
    print("     - Or check what port it's using")
    exit(1)

except Exception as e:
    print(f"[ERROR] {str(e)}")
    exit(1)

# Test 2: Send a simple prompt
print("\n" + "="*70)
print("TEST 2: Text Generation")
print("="*70)
print("Sending test prompt...")

endpoint = f"{base_url}/v1/chat/completions"

headers = {
    "Content-Type": "application/json"
}

data = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "Please respond with 'SUCCESS' if you can read this message."
        }
    ],
    "stream": False,
    "temperature": 0.7
}

try:
    response = requests.post(
        endpoint,
        json=data,
        headers=headers,
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})

        print(f"[OK] Text generation successful!")
        print(f"\nResponse: {content}")
        print(f"\nToken Usage:")
        print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
        print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
        print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print("✓ LM Studio API is working correctly")
        print(f"✓ Server running at: {base_url}")
        print(f"✓ Model: {model}")
        print("✓ Text generation: Working")
        print("\n" + "="*70)
        print("Configuration Verified - Ready to Use!")
        print("="*70)

    elif response.status_code == 404:
        print(f"[ERROR] Model not found: {model}")
        print("\nPossible issues:")
        print("  1. The model name in .env doesn't match loaded model")
        print("  2. The model is not loaded in LM Studio")
        print("\nTo fix:")
        print("  1. Check what model is loaded in LM Studio")
        print("  2. Update LMSTUDIO_MODEL in .env to match")
        print(f"  3. Current setting: LMSTUDIO_MODEL={model}")

    else:
        print(f"[ERROR] HTTP {response.status_code}")
        try:
            error_json = response.json()
            print(f"Details: {json.dumps(error_json, indent=2)[:500]}")
        except:
            print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
