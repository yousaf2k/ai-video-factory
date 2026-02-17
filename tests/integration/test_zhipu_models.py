"""
Test Zhipu API with the correct endpoint and different model names
"""
import os
import json
from dotenv import load_dotenv
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

api_key = os.getenv("ZHIPU_API_KEY")

print("="*70)
print("ZHIPU API - CORRECT ENDPOINT & MODEL VERIFICATION")
print("="*70)
print(f"\nAPI Key: {api_key[:20]}...{api_key[-10:]}\n")

# Correct endpoint from our tests
endpoint = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# Common model names for Zhipu
models_to_test = [
    "glm-4",
    "glm-4-flash",
    "glm-4-plus",
    "glm-4-air",
    "glm-3-turbo",
    "glm-4.7",  # Current config
]

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print(f"Testing endpoint: {endpoint}\n")

for model in models_to_test:
    print(f"{'='*70}")
    print(f"Testing model: {model}")
    print(f"{'='*70}")

    data = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False
    }

    try:
        response = requests.post(
            endpoint,
            json=data,
            headers=headers,
            timeout=30,
            verify=False
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = result.get("usage", {})
            print(f"[SUCCESS] Model works!")
            print(f"Response: {content[:100]}...")
            print(f"Tokens used: {usage.get('total_tokens', 'N/A')}")
            print(f"\n*** '{model}' is the correct model name! ***")
            break
        elif response.status_code == 429:
            error_json = response.json()
            error_msg = error_json.get("error", {}).get("message", "")
            print(f"[INFO] Quota/balance issue: {error_msg}")
            print(f"[INFO] This endpoint is correct, but account needs recharge")
        elif response.status_code == 401:
            print(f"[ERROR] Authentication failed - check API key")
        elif response.status_code == 400:
            error_json = response.json()
            print(f"[ERROR] Bad request - model might not exist")
            print(f"Details: {json.dumps(error_json, indent=2)[:300]}...")
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            try:
                error_json = response.json()
                print(f"Details: {json.dumps(error_json, indent=2)[:200]}...")
            except:
                pass

    except Exception as e:
        print(f"[ERROR] {str(e)[:200]}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("\nCorrect endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions")
print("\nIf you see 429 errors:")
print("  - Your API key is valid")
print("  - The endpoint is correct")
print("  - But your account balance is insufficient")
print("  - Visit https://open.bigmodel.cn/ to recharge")
print("\nIf you see 400 errors:")
print("  - The model name is incorrect")
print("  - Try 'glm-4', 'glm-4-flash', or 'glm-4-plus'")
print("="*70)
