"""
Test script to verify Z.AI (Zhipu) API connection and glm-4.7 model
"""
import os
import json
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Get credentials
api_key = os.getenv("ZHIPU_API_KEY")
model = os.getenv("ZHIPU_MODEL", "glm-4.7")

print("="*70)
print("ZHIPU (Z.AI) API TEST")
print("="*70)

# Check credentials
print("\n1. Checking credentials:")
if not api_key:
    print("   [ERROR] ZHIPU_API_KEY not set in .env file")
    exit(1)
else:
    print(f"   [OK] API Key found: {api_key[:20]}...{api_key[-10:]}")
    print(f"   [OK] Model: {model}")

# API endpoint
base_url = "https://api.zhipu.ai/v1"
endpoint = f"{base_url}/chat/completions"
print(f"\n2. API Endpoint:")
print(f"   URL: {endpoint}")

# Test request
print(f"\n3. Testing API connection...")
print(f"   Model: {model}")
print(f"   Sending test request...")

headers = {
    "Authorization": f"Bearer {api_key}",
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
    "stream": False
}

try:
    # First try with SSL verification
    print(f"   Attempting with SSL verification enabled...")
    try:
        response = requests.post(
            endpoint,
            json=data,
            headers=headers,
            timeout=30
        )
    except Exception as ssl_error:
        if "SSL" in str(ssl_error) or "certificate" in str(ssl_error):
            print(f"   SSL Error detected: {str(ssl_error)[:100]}...")
            print(f"\n   Retrying with SSL verification DISABLED...")
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.post(
                endpoint,
                json=data,
                headers=headers,
                timeout=30,
                verify=False
            )
        else:
            raise

    if response.status_code == 200:
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"\n   [OK] SUCCESS! API is working")
        print(f"   Response: {content}")

        # Show full response details
        print(f"\n4. Response Details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Model returned: {result.get('model', 'N/A')}")
        print(f"   Usage: {json.dumps(result.get('usage', {}), indent=6)}")

    else:
        print(f"\n   [ERROR] HTTP {response.status_code}")
        try:
            error_json = response.json()
            print(f"   Error Response: {json.dumps(error_json, indent=6, ensure_ascii=False)}")
        except:
            # Fallback to raw text but limit length to avoid encoding errors
            error_text = response.text[:500]
            print(f"   Error Response (first 500 chars): {error_text}")

except requests.exceptions.Timeout:
    print(f"\n   [ERROR] Request timed out after 30 seconds")
    print(f"   The API server might be slow or unreachable")

except requests.exceptions.ConnectionError as e:
    print(f"\n   [ERROR] Connection error: {e}")
    print(f"   Check your internet connection")

except Exception as e:
    print(f"\n   [ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
