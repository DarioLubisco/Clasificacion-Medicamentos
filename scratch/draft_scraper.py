import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import re
from bs4 import BeautifulSoup
from openai import OpenAI
import pyodbc

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search", "pinterest", "youtube"]

def is_valid_url(url, title):
    url_lower = url.lower()
    title_lower = title.lower()
    for pd in PROHIBITED_DOMAINS:
        if pd in url_lower or pd in title_lower:
            return False
    return True

def buscar_multiples_fuentes(query: str, max_fuentes=3):
    print(f"  Buscando en DuckDuckGo: '{query}'")
    fuentes = []
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=10)
        for r in results:
            url = r.get('href', '')
            title = r.get('title', '')
            if url and is_valid_url(url, title):
                fuentes.append(url)
                if len(fuentes) >= max_fuentes:
                    break
    except Exception as e:
        print(f"  Error en busqueda web: {e}")
    return fuentes

def extraer_html(url: str):
    print(f"    Extrayendo: {url}")
    try:
        response = requests.post(SCRAPLING_API_URL, json={"url": url}, timeout=45)
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")
    except Exception as e:
        print(f"    Fallo extraccion de {url}: {e}")
    return ""

def parsear_html_texto_imagenes(html_content, base_url):
    if not html_content: return "", []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract text
    for script in soup(["script", "style", "nav", "footer"]):
        script.extract()
    text = soup.get_text(separator=' ')
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Extract images
    imgs = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src')
        if src and ('jpg' in src.lower() or 'png' in src.lower() or 'webp' in src.lower()):
            if src.startswith('//'): src = 'https:' + src
            elif src.startswith('/'): src = base_url.rstrip('/') + src
            if len(src) < 300 and 'logo' not in src.lower() and 'icon' not in src.lower():
                imgs.append(src)
    
    # deduplicate and limit
    imgs = list(dict.fromkeys(imgs))[:5]
    return text[:8000], imgs

def obtener_taxonomias():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        taxonomias = []
        for r in cursor.fetchall():
            taxonomias.append(f"- Dominio: {r[0]} | Categoria: {r[1] or 'SINEVAL'} | Subcategoria: {r[2] or 'SINEVAL'}")
        conn.close()
        return "\n".join(taxonomias)
    except Exception as e:
        print(f"Error taxonomias: {e}")
        return ""

print("Test draft scraper logic loaded.")
