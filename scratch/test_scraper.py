import requests
import json
import re
VALUESERP_API_KEY = "9B1D5AA5918946FBBC1515858FB56E1A"
SCRAPLING_API_URL = "http://127.0.0.1:8005/scrape"
def buscar_en_internet(query):
    params = {"api_key": VALUESERP_API_KEY, "q": query, "location": "Mexico", "google_domain": "google.com.mx", "hl": "es", "num": 5}
    res = requests.get("https://api.valueserp.com/search", params=params, timeout=15)
    print("ValueSERP status:", res.status_code)
    urls = []
    if res.status_code == 200:
        for r in res.json().get("organic_results", []):
            urls.append(r.get('link', ''))
    return urls
urls = buscar_en_internet('DISCOLAYTE POLVO X medicamento precio')
print("URLs:", urls)
if urls:
    response = requests.post(SCRAPLING_API_URL, json={"url": urls[0]}, timeout=45)
    print("Scrapling status:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print("Scrapling output keys:", data.keys())
        if "error" in data:
            print("Error:", data["error"])
        else:
            content = data.get("content", "")
            print("Content length:", len(content))
