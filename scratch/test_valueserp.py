import requests
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY", "9B1D5AA5918946FBBC1515858FB56E1A")
query = "0000000030373"

params = {
    "api_key": VALUESERP_API_KEY,
    "q": query,
    "location": "Mexico",
    "google_domain": "google.com.mx",
    "hl": "es",
    "num": 10
}

try:
    print(f"Testing ValueSerp with key: {VALUESERP_API_KEY[:4]}...")
    res = requests.get("https://api.valueserp.com/search", params=params, timeout=15)
    print("Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("Organic results count:", len(data.get("organic_results", [])))
        if data.get("organic_results"):
            for idx, r in enumerate(data.get("organic_results")[:3]):
                print(f"  {idx}: {r.get('link')} - {r.get('title')}")
        else:
            print("Response details:", data.keys())
            if "request_info" in data:
                print("Request info:", data["request_info"])
except Exception as e:
    print("Error:", e)
