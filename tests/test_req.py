import urllib.request
import json
import urllib.error

url = "http://127.0.0.1:8000/api/projects/session_20260226_135450/shots/11/regenerate-image"
data = json.dumps({"force": True, "image_mode": "geminiweb"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print("Response body:", e.read().decode())
except urllib.error.URLError as e:
    print("Connection error:", e.reason)
except Exception as e:
    print("Other error:", e)
