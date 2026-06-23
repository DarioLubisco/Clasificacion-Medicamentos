import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import time
import requests
import re
from duckduckgo_search import DDGS

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://127.0.0.1:8005/scrape"
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY", "9B1D5AA5918946FBBC1515858FB56E1A")

PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search", "pinterest", "youtube"]

def is_valid_url(url, title):
    url_lower = url.lower()
    title_lower = title.lower()
    for pd in PROHIBITED_DOMAINS:
        if pd in url_lower or pd in title_lower:
            return False
    return True

def buscar_en_internet(query: str, max_fuentes=10) -> list:
    print(f"  Buscando en Google (ValueSERP): '{query}'")
    fuentes = []
    try:
        params = {
            "api_key": VALUESERP_API_KEY,
            "q": query,
            "location": "Mexico",
            "google_domain": "google.com.mx",
            "hl": "es",
            "num": 20
        }
        res = requests.get("https://api.valueserp.com/search", params=params, timeout=15)
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
        else:
            print(f"  Error API ValueSERP (HTTP {res.status_code}): {res.text}")
        return fuentes
    except Exception as e:
        print(f"  Error en búsqueda web (ValueSERP): {e}")
        return fuentes

def limpiar_html_regex(html_content: str):
    text = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:8000]

def extraer_imagenes_regex(html_content: str, base_url: str):
    imgs = []
    matches = re.findall(r'<(?:img|picture)[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html_content, flags=re.IGNORECASE)
    for src in matches:
        if 'jpg' in src.lower() or 'png' in src.lower() or 'webp' in src.lower():
            if src.startswith('//'): src = 'https:' + src
            elif src.startswith('/'): src = base_url.rstrip('/') + src
            if len(src) < 300 and 'logo' not in src.lower() and 'icon' not in src.lower():
                imgs.append(src)
    return list(dict.fromkeys(imgs))[:5]

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
                "url": url,
                "texto": texto,
                "imagenes": imagenes
            }
    except Exception as e:
        print(f"    Fallo extraccion de {url}: {e}")
    return None

def main():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    # Obtener registros pendientes (Fase 1 completada, Fase 2 no completada), limitado a 5 para prueba final
    cursor.execute("""
        SELECT TOP 5 codbarras, descrip1art 
        FROM Procurement.por_aprobacion_equivalencias 
        WHERE procesado_fase1 = 1 AND procesado_fase2 = 0 AND fabricante_Des IS NULL
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No hay registros pendientes para la Fase 2 (Scraping).")
        return

    print(f"Iniciando Fase 2 (Scraping) para {len(rows)} registros...")

    for row in rows:
        codbarras = row.codbarras.strip()
        desc = row.descrip1art.strip()
        print(f"\nProcesando: {desc} (EAN: {codbarras})")

        is_bli = codbarras.startswith("BLI_")
        is_internal = is_bli or len(codbarras) != 13

        fuentes_extraidas = []

        if not is_internal:
            urls = buscar_en_internet(f"{codbarras}", max_fuentes=10)
            if not urls:
                print("  Buscando por EAN falló, intentando por descripción...")
                urls = buscar_en_internet(f"{desc} prospecto Vademecum", max_fuentes=10)
            
            for idx, u in enumerate(urls, 1):
                fuente_data = extraer_fuente_web(u, idx)
                if fuente_data:
                    # Parse domain
                    dominio_origen = re.search(r'https?://([^/]+)', u)
                    dominio_str = dominio_origen.group(1) if dominio_origen else "Desconocido"

                    img_url = fuente_data['imagenes'][0] if fuente_data['imagenes'] else None

                    # Insertar en BD
                    cursor.execute("""
                        INSERT INTO Procurement.scraping_farmacias_raw 
                        (codbarras, farmacia_origen, url_origen, url_imagen, texto_extraido, procesado_fase3)
                        VALUES (?, ?, ?, ?, ?, 0)
                    """, (codbarras, dominio_str, u, img_url, fuente_data['texto']))
                    
                    fuentes_extraidas.append(fuente_data)
                time.sleep(1) 

        # Marcar registro como Fase 2 terminada
        cursor.execute("UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase2 = 1 WHERE codbarras = ?", (codbarras,))
        print(f"  Fase 2 completada para {codbarras}. Fuentes guardadas: {len(fuentes_extraidas)}")

    conn.close()
    print("\nLote de Fase 2 completado.")

if __name__ == "__main__":
    main()
