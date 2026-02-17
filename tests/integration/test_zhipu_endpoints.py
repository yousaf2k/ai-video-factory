"""
Test different Zhipu API endpoints to find the correct one
"""
import os
import json
from dotenv import load_dotenv
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

api_key = os.getenv("ZHIPU_API_KEY")
model = os.getenv("ZHIPU_MODEL", "glm-4.7")

print("="*70)
print("TESTING DIFFERENT ZHIPU API ENDPOINTS")
print("="*70)
print(f"\nAPI Key: {api_key[:20]}...{api_key[-10:]}")
print(f"Model: {model}\n")

# Different possible endpoints
endpoints_to_test = [
    ("https://api.zhipu.ai/v1/chat/completions", "OpenAI-compatible endpoint (current)"),
    ("https://open.bigmodel.cn/api/paas/v4/chat/completions", "BigModel.cn endpoint"),
    ("https://api.bigmodel.cn/v4/chat/completions", "BigModel alternative"),
    ("https://api.zhipu.ai/paas/v4/chat/completions", "Zhipu PAAS v4"),
]

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": model,
    "messages": [{"role": "user", "content": "Test"}],
    "stream": False
}

for endpoint, description in endpoints_to_test:
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"URL: {endpoint}")
    print(f"{'='*70}")

    try:
        response = requests.post(
            endpoint,
            json=data,
            headers=headers,
            timeout=30,
            verify=False
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"[SUCCESS] Response: {content[:100]}...")
            print(f"\n*** This is the CORRECT endpoint! ***")
            break
        elif response.status_code == 401:
            print(f"[ERROR] Authentication failed - API key issue")
        elif response.status_code == 404:
            print(f"[ERROR] Not Found - Endpoint or model incorrect")
            try:
                error_json = response.json()
                print(f"Error details: {json.dumps(error_json, indent=2)[:200]}...")
            except:
                pass
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            try:
                error_json = response.json()
                print(f"Error details: {json.dumps(error_json, indent=2)[:300]}...")
            except:
                print(f"Response: {response.text[:200]}...")

    except Exception as e:
        print(f"[ERROR] {str(e)[:200]}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nRECOMMENDATION:")
print("If all endpoints failed, check:")
print("1. Your API key is valid and active")
print("2. The model name 'glm-4.7' is correct (should be 'glm-4', 'glm-4-flash', etc.)")
print("3. Your account has API access enabled")
print("\nVisit https://open.bigmodel.cn/ for correct API documentation")
