import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8001/api/chat',
    data=json.dumps({"message": "Tell a story where 3 friends share 12 apples equally.", "history": [], "use_rag": True}).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as r:
        print(r.read())
except Exception as e:
    print(e.read())
