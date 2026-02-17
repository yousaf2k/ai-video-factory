"""
Test Z.AI API with correct endpoint and model
"""
import os
import json
from dotenv import load_dotenv
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

api_key = os.getenv("ZHIPU_API_KEY")
model = os.getenv("ZHIPU_MODEL")

print("="*70)
print("Z.AI API TEST - CORRECT CONFIGURATION")
print("="*70)
print(f"\nAPI Key: {api_key[:20]}...{api_key[-10:]}")
print(f"Model: {model}\n")

# Correct Z.AI endpoint
endpoint = "https://api.z.ai/api/coding/paas/v4/chat/completions"
print(f"Testing endpoint: {endpoint}\n")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": model,
    "messages": [{"role": "user", "content": "Please respond with 'SUCCESS' if you can read this."}],
    "stream": False
}

try:
    print("Sending request...")
    response = requests.post(
        endpoint,
        json=data,
        headers=headers,
        timeout=30,
        verify=False
    )

    print(f"Status Code: {response.status_code}\n")

    if response.status_code == 200:
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})

        print("="*70)
        print("SUCCESS! Z.AI API is working correctly")
        print("="*70)
        print(f"\nResponse: {content}")
        print(f"\nToken Usage:")
        print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
        print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
        print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")

        print("\n" + "="*70)
        print("Configuration Verified:")
        print("="*70)
        print(f"  Endpoint: {endpoint}")
        print(f"  Model: {model}")
        print(f"  Status: WORKING")
        print("="*70)

    elif response.status_code == 401:
        error_json = response.json()
        print("[ERROR] Authentication failed")
        print(f"Details: {json.dumps(error_json, indent=2)}")

    elif response.status_code == 429:
        error_json = response.json()
        error_msg = error_json.get("error", {}).get("message", "")
        print("[INFO] Quota/balance issue")
        print(f"Message: {error_msg}")
        print("\nThis means:")
        print("  - The endpoint is correct")
        print("  - Your API key is valid")
        print("  - But account has insufficient balance")

    elif response.status_code == 400:
        error_json = response.json()
        print("[ERROR] Bad request")
        print(f"Details: {json.dumps(error_json, indent=2)}")
        print("\nPossible issues:")
        print("  - Model name might be wrong")
        print("  - Request format might be incorrect")

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
