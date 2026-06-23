import os
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def test_model(model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    content_payload = [{"type": "text", "text": "Hello, please reply with a JSON object: {\"reply\": \"hi\"}"}]
    
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            res_str = response.read().decode()
            print(f"--- MODEL: {model} ---")
            print(res_str)
    except Exception as e:
        print(f"Error for {model}: {e}")

test_model("google/gemini-2.5-pro")
test_model("google/gemini-3.1-pro-preview")
