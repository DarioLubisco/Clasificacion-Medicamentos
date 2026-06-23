import os
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import json
import time

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def test():
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek/deepseek-v4-flash", 
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.1
    }
    
    print("Enviando petición a OpenRouter para deepseek/deepseek-v4-flash...")
    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            print(f"Respuesta recibida en {time.time() - t0:.2f}s:")
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error tras {time.time() - t0:.2f}s: {e}")

if __name__ == '__main__':
    test()
