import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import re
from bs4 import BeautifulSoup
from thefuzz import fuzz
from duckduckgo_search import DDGS
from openai import OpenAI

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# --- CONFIGURACIÓN (desde .env) ---
SCRAPLING_API_URL = os.getenv("SCRAPLING_API_URL", "http://10.147.18.204:8005/scrape")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
INPUT_FILE = os.getenv("SCRAPING_INPUT_FILE", "input_scraper_v11.json")
OUTPUT_JSON = os.getenv("SCRAPING_OUTPUT_JSON", "investigacion_resultados_v11.json")
OUTPUT_SQL = os.getenv("SCRAPING_OUTPUT_SQL", "actualizacion_scraper_v11.sql")
SEARCH_ENGINE = os.getenv("SCRAPING_SEARCH_ENGINE", "valueserp")
VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY")
SEARCH_LOCATION = os.getenv("SEARCH_LOCATION", "Venezuela")

# Parametros operacionales desde .env
SCRAPING_TIMEOUT = int(os.getenv("TIMEOUT_RED", "15"))
SCRAPING_REINTENTOS = int(os.getenv("SCRAPING_REINTENTOS", "3"))
SCRAPING_DELAY = float(os.getenv("SCRAPING_DELAY", "0.5"))
SCRAPING_TEXTO_MAX = int(os.getenv("SCRAPING_TEXTO_MAX", "8000"))

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search", "pinterest", "youtube"]

def is_valid_url(url, title):
    url_lower = url.lower()
    title_lower = title.lower()
    for pd in PROHIBITED_DOMAINS:
        if pd in url_lower or pd in title_lower:
            return False
    return True

def buscar_en_internet(query: str, max_fuentes=10) -> list:
    fuentes = []
    if SEARCH_ENGINE == "valueserp":
        print(f"  Buscando en Google (ValueSERP): '{query}'")
        params = {
            "api_key": VALUESERP_API_KEY,
            "q": query,
            "location": SEARCH_LOCATION,
            "hl": "es",
            "num": max_fuentes
        }
        for intento in range(SCRAPING_REINTENTOS):
            try:
                res = requests.get("https://api.valueserp.com/search", params=params, timeout=SCRAPING_TIMEOUT)
                if res.status_code == 200:
                    data = res.json()
                    organic_results = data.get("organic_results", [])
                    for r in organic_results:
                        url = r.get('link', '')
                        title = r.get('title', '')
                        if url and is_valid_url(url, title):
                            fuentes.append(url)
                            if len(fuentes) >= max_fuentes:
                                break
                    return fuentes
                else:
                    print(f"  [Intento {intento+1}/{SCRAPING_REINTENTOS}] Error API ValueSERP (HTTP {res.status_code}): {res.text[:120]}")
            except Exception as e:
                print(f"  [Intento {intento+1}/{SCRAPING_REINTENTOS}] Error de red/timeout en búsqueda (ValueSERP): {e}")
            
            if intento < SCRAPING_REINTENTOS - 1:
                wait_time = (intento + 1) * SCRAPING_DELAY * 6
                print(f"  Esperando {wait_time} segundos antes de reintentar búsqueda...")
                time.sleep(wait_time)
        return fuentes
    else:
        print(f"  Buscando en DuckDuckGo: '{query}'")
        try:
            results = DDGS().text(query, max_results=10)
            for r in results:
                url = r.get('href', '')
                title = r.get('title', '')
                if url and is_valid_url(url, title):
                    fuentes.append(url)
                    if len(fuentes) >= max_fuentes:
                        break
            return fuentes
        except Exception as e:
            print(f"  Error en busqueda web (DuckDuckGo): {e}")
            return fuentes

def extraer_fuente_web(url: str, idx: int, desc_maestra: str = None) -> dict:
    print(f"    Extrayendo Fuente {idx}: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=SCRAPING_TIMEOUT)
        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remover tags ruidosos
            for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                tag.decompose()
                
            # Extraer imagenes con Filtro de Proximidad y ALT (Tecnicas 1 y 2).
            # Por página/fuente conservamos SOLO la mejor imagen (mayor score de
            # proximidad con la descripción) para garantizar independencia de
            # fuentes en el consenso de imágenes downstream.
            mejor_img = None
            mejor_score = -1
            for img in soup.find_all(['img', 'picture']):
                src = img.get('src') or img.get('data-src')
                if not src: continue
                if 'jpg' in src.lower() or 'png' in src.lower() or 'webp' in src.lower():
                    if 'logo' in src.lower() or 'icon' in src.lower(): continue

                    alt_text = img.get('alt', '')
                    parent = img.find_parent()
                    parent_text = parent.get_text(separator=' ', strip=True) if parent else ''

                    if desc_maestra:
                        score_alt = fuzz.partial_ratio(desc_maestra.lower(), alt_text.lower()) if alt_text else 0
                        score_prox = fuzz.partial_ratio(desc_maestra.lower(), parent_text.lower()) if parent_text else 0
                        score = max(score_alt, score_prox)
                        matches_filter = (score_alt > 40 or score_prox > 40 or not parent_text)
                    else:
                        score = 0
                        matches_filter = True

                    if matches_filter:
                        if src.startswith('//'): src = 'https:' + src
                        elif src.startswith('/'): src = 'https://' + url.split('/')[2] + src
                        if len(src) < 300 and score > mejor_score:
                            mejor_score = score
                            mejor_img = src

            imgs = [mejor_img] if mejor_img else []

            # Texto extraido
            texto = soup.get_text(separator=' ', strip=True)
            texto = re.sub(r'\s+', ' ', texto)[:SCRAPING_TEXTO_MAX]

            return {
                "fuente": idx,
                "url": url,
                "texto_extraido": texto,
                "imagenes_encontradas": imgs
            }
    except Exception as e:
        print(f"    Fallo extraccion de {url}: {e}")
    return None

def procesar_lote():
    if not os.path.exists(INPUT_FILE):
        print(f"Archivo {INPUT_FILE} no encontrado. Creando dummy para pruebas...")
        with open(INPUT_FILE, "w") as f:
            json.dump([{"codigo": "123", "codbarras": "0021281086200", "descrip1art": "Empagliflozina 10 mg"}], f)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lote = json.load(f)

    resultados = []
    
    for i, item in enumerate(lote):
        codbarras = item.get("codbarras", "").strip()
        desc = item.get("descrip1art", "").strip()
        codigo = item.get("codigo", "")
        
        print(f"\n[{i+1}/{len(lote)}] Analizando: {desc} (EAN: {codbarras})")
        
        is_bli = codbarras.startswith("BLI_")
        is_internal = is_bli or len(codbarras) != 13

        fuentes_extraidas = []
        todas_imagenes = []

        if not is_internal:
            urls = buscar_en_internet(f'"{codbarras}"')
            if not urls:
                print("  Buscando por EAN falló, intentando por nombre del producto...")
                urls = buscar_en_internet(desc)
            if not urls:
                print("  Búsqueda por nombre también falló, saltando búsqueda web.")

            for idx, u in enumerate(urls, 1):
                fuente_data = extraer_fuente_web(u, idx, desc)
                if fuente_data:
                    fuentes_extraidas.append(fuente_data)
                    todas_imagenes.extend(fuente_data['imagenes_encontradas'])
                    if len(set(todas_imagenes)) >= int(os.getenv("MAX_FOTOS_TOTALES", "10")):
                        break
                time.sleep(SCRAPING_DELAY)
        else:
            print(f"  Código interno ({codbarras}). Sin búsqueda web.")
                
        # Estructuramos para el Mega Orquestador V3
        context_block = {
            "registro": {
                "codigo": codigo, 
                "codbarras": codbarras, 
                "descripcion_original": desc,
                "is_blister": 1 if is_bli else 0
            },
            "fuentes_web": fuentes_extraidas
        }
        
        # En la V11 solo extraemos el contexto y guardamos el JSON para que el Mega Orquestador lo procese.
        # No hacemos LLM de clasificacion aquí para mantener responsabilidades separadas.
        resultados.append(context_block)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nProceso completado. Datos web y bloques de imágenes guardados en {OUTPUT_JSON}")

if __name__ == "__main__":
    procesar_lote()
