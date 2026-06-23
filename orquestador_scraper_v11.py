import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import re
from duckduckgo_search import DDGS
from openai import OpenAI

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
INPUT_FILE = "input_scraper_v11.json"
OUTPUT_JSON = "investigacion_resultados_v11.json"
OUTPUT_SQL = "actualizacion_scraper_v11.sql"

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

def buscar_en_internet(query: str, max_fuentes=3) -> list:
    print(f"  Buscando en DuckDuckGo: '{query}'")
    fuentes = []
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
        print(f"  Error en busqueda web: {e}")
        return fuentes

def limpiar_html_regex(html_content: str):
    # Remover etiquetas script y style
    text = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Extraer texto limpio
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:8000]

def extraer_imagenes_regex(html_content: str, base_url: str):
    imgs = []
    # Buscar atributos src o data-src
    matches = re.findall(r'<(?:img|picture)[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html_content, flags=re.IGNORECASE)
    for src in matches:
        if 'jpg' in src.lower() or 'png' in src.lower() or 'webp' in src.lower():
            if src.startswith('//'): src = 'https:' + src
            elif src.startswith('/'): src = base_url.rstrip('/') + src
            if len(src) < 300 and 'logo' not in src.lower() and 'icon' not in src.lower():
                imgs.append(src)
    return list(dict.fromkeys(imgs))[:5] # deduplicate, limit to 5

def extraer_fuente_web(url: str, idx: int) -> dict:
    print(f"    Extrayendo (Scrapling) Fuente {idx}: {url}")
    try:
        payload = {"url": url}
        response = requests.post(SCRAPLING_API_URL, json=payload, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                return None
            html_content = data.get("content", "")
            texto = limpiar_html_regex(html_content)
            imagenes = extraer_imagenes_regex(html_content, url)
            return {
                "fuente": idx,
                "url": url,
                "texto_extraido": texto,
                "imagenes_encontradas": imagenes
            }
    except Exception as e:
        print(f"    Fallo extraccion de {url}: {e}")
    return None

def pre_clasificar_medicamento(desc: str) -> bool:
    prompt = f"""
    Eres un experto en farmacia. Analiza la siguiente descripción de producto de inventario:
    "{desc}"
    ¿Es esto un MEDICAMENTO FARMACÉUTICO (que contiene principios activos, ej. pastillas, jarabes, inyecciones) o es un INSUMO MEDICO / MISCELÁNEO (ej. jeringas, termómetros, gasas, champú, cosméticos)?
    Responde ÚNICAMENTE con la palabra "MEDICAMENTO" o "INSUMO".
    """
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
        )
        res = response.choices[0].message.content.strip().upper()
        return "MEDICAMENTO" in res
    except:
        return True

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
        is_med = pre_clasificar_medicamento(desc)
        
        fuentes_extraidas = []
        todas_imagenes = []
        
        if not is_med:
            print("  Clasificado como INSUMO MEDICO. Saltando busqueda web profunda.")
        else:
            if not is_internal:
                urls = buscar_en_internet(f"{codbarras}")
                if not urls:
                    print("  Buscando por EAN falló, intentando por descripción...")
                    urls = buscar_en_internet(f"{desc} prospecto Vademecum")
                
                for idx, u in enumerate(urls, 1):
                    fuente_data = extraer_fuente_web(u, idx)
                    if fuente_data:
                        fuentes_extraidas.append(fuente_data)
                        todas_imagenes.extend(fuente_data['imagenes_encontradas'])
                    time.sleep(1) # delay between scraping
            else:
                print(f"  Código interno ({codbarras}). Sin búsqueda web.")
                
        # Estructuramos para el Mega Orquestador V3
        context_block = {
            "registro": {
                "codigo": codigo, 
                "codbarras": codbarras, 
                "descripcion_original": desc,
                "es_medicamento": 1 if is_med else 0,
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
