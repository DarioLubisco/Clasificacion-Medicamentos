#!/usr/bin/env python3
"""Script simple para probar GLM-4.7 API sin restricciones"""
import urllib.request
import json
import os
from dotenv import load_dotenv

from synapse_cred import load_synapse_credentials
load_synapse_credentials()

GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_API_URL = os.getenv("GLM_API_URL")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4.7")

print(f"API URL: {GLM_API_URL}")
print(f"Model: {GLM_MODEL}")
print(f"API Key: {GLM_API_KEY[:20]}...")
print()

url = GLM_API_URL
headers = {
    "Authorization": f"Bearer {GLM_API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": GLM_MODEL,
    "messages": [
        {"role": "user", "content": "Test connection. Respond with 'OK'."}
    ],
    "temperature": 0.2,
    "max_tokens": 10
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode())
        print("✓ GLM-4.7 API connection successful!")
        print(f"Response: {result}")
except Exception as e:
    print(f"✗ GLM-4.7 API connection failed: {e}")
    import traceback
    traceback.print_exc()