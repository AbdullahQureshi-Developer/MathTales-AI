import urllib.request
import json
import traceback

req = urllib.request.Request(
    'http://localhost:8000/api/chat',
    data=b'{"message": "Tell me a story about predicting the next number in 2, 4, 8, 16?"}',
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode())
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
    else:
        traceback.print_exc()
