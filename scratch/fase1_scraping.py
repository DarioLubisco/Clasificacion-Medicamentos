import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import socket
import sys
import os
import requests
import re
import base64
from dotenv import load_dotenv

socket.setdefaulttimeout(180)

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY", "9B1D5AA5918946FBBC1515858FB56E1A")
SCRAPLING_API_URL = "http://127.0.0.1:8005/scrape"
PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search", "pinterest", "youtube"]

EANS_TEST = [
    '0000000030373', # DISCOLAYTE POLVO 69.7 G X 10 SOBRES
    '0000000163774', # Oxacilina 1g polvo para solución inyectable (IM/IV) x 10 viales Zakimed
    '0000000201629', # Metotrexato 50 mg/2 ml solución inyectable (IV/IM) en ampolla.
    '0000000206815', # Gemcitabina 1 g polvo para solución inyectable, 1 ampolla
    '0000025525755', # Jarabe de achicoria Farmagenik 120 ml
    '0000025525762', # Jarabe Lamedor 120 ml Farmagenik
    '0000075971199', # PENASTIM 500 mg solución inyectable
    '0004',          # AMP BETAMETASONA 4 MGX1 FV
    '0008',          # AMP BETAMETASONA 8 MG X1 FV
    '001004002941515'# Hidrocortisona 500mg inyectable (IV/IM) de Drotafarma
]

def is_valid_url(url, title):
    url_lower = url.lower()
    title_lower = title.lower()
    for pd in PROHIBITED_DOMAINS:
        if pd in url_lower or pd in title_lower:
            return False
    return True

def buscar_en_internet(query: str, max_fuentes=6) -> list:
    print(f"  [Scraper] Buscando en Google: '{query}'")
    fuentes = []
    try:
        params = {
            "api_key": VALUESERP_API_KEY,
            "q": query,
            "location": "Mexico",
            "google_domain": "google.com.mx",
            "hl": "es",
            "num": 10
        }
        res = requests.get("https://api.valueserp.com/search", params=params, timeout=15)
        if res.status_code == 200:
             organic_results = res.json().get("organic_results", [])
             for r in organic_results:
                 url = r.get('link', '')
                 title = r.get('title', '')
                 if url and is_valid_url(url, title):
                     fuentes.append(url)
                     if len(fuentes) >= max_fuentes: break
        return fuentes
    except Exception as e:
        print(f"  Error búsqueda: {e}")
        return fuentes

def limpiar_html_regex(html_content: str):
    text = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()[:8000]

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

def extraer_fuente_web(url: str) -> dict:
    try:
        # Intento 1: API de Scrapling
        response = requests.post(SCRAPLING_API_URL, json={"url": url}, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if "error" not in data:
                return {
                    "url": url,
                    "texto": limpiar_html_regex(data.get("content", "")),
                    "imagenes": extraer_imagenes_regex(data.get("content", ""), url)
                }
        else:
            print(f"    [Aviso] Scrapling devolvió error {response.status_code}. Usando fallback requests directo...")
            
        # Intento 2 (Fallback): requests directo
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        fallback_res = requests.get(url, headers=headers, timeout=15)
        if fallback_res.status_code == 200:
            content = fallback_res.text
            return {
                "url": url,
                "texto": limpiar_html_regex(content),
                "imagenes": extraer_imagenes_regex(content, url)
            }
    except Exception as e:
        print(f"    [Error] Falló extracción para {url}: {e}")
        pass
    return None

def obtener_imagenes_b64(urls):
    valid_urls = [u for u in urls if u and u.strip().startswith(('http://', 'https://'))]
    base64_imgs = []
    for img_url in valid_urls[:3]:
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                img_data = response.read()
                encoded = base64.b64encode(img_data).decode('utf-8')
                base64_imgs.append(f"data:{content_type};base64,{encoded}")
        except:
            continue
    return base64_imgs

def procesar_ean(conn, cursor, codbarras, desc):
    print(f"\n[Scraping] Extrayendo información de: {desc} ({codbarras})")
    
    is_internal = len(codbarras) < 12 or codbarras.startswith('00000') or codbarras.startswith('BLI_')
    urls = []
    
    if not is_internal:
        urls = buscar_en_internet(f"{codbarras}", max_fuentes=6)
        
    if not urls:
        cleaned_desc = desc
        cleaned_desc = re.sub(r'\b\d+(?:\.\d+)?\s*(?:g|mg|ml|mcg|kg|l|sob|sobres|amp|ampollas|cap|capsulas|tab|tabletas|comp|comprimidos|vial|viales|f\.v|fv)\b', '', cleaned_desc, flags=re.IGNORECASE)
        cleaned_desc = re.sub(r'\bx\s*\d+\b', '', cleaned_desc, flags=re.IGNORECASE)
        cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc).strip()
        
        search_query = f"{cleaned_desc} medicamento precio"
        print(f"  [Scraper] Fallback de búsqueda: '{search_query}'")
        urls = buscar_en_internet(search_query, max_fuentes=6)
        
        if not urls:
            search_query_vademecum = f"{cleaned_desc} prospecto vademecum"
            print(f"  [Scraper] Fallback secundario: '{search_query_vademecum}'")
            urls = buscar_en_internet(search_query_vademecum, max_fuentes=6)
            
    if not urls:
        print(f"  [Error] No se encontraron fuentes para {codbarras}")
        return None

    fuentes_web = []
    todas_imagenes = []
    
    # Prevenir duplicados de URL de imagen globalmente para este EAN
    imagenes_vistas = set()

    for idx, u in enumerate(urls, 1):
        fd = extraer_fuente_web(u)
        if fd and fd['texto']:
            dom = re.search(r'https?://([^/]+)', u)
            dom_str = dom.group(1) if dom else "Desconocido"
            
            img_url = fd['imagenes'][0] if fd['imagenes'] else None
            
            # Guardamos en BD la traza original de extracción para QA/Auditoría
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM Procurement.scraping_farmacias_raw WHERE codbarras = ? AND url_origen = ?)
                BEGIN
                    INSERT INTO Procurement.scraping_farmacias_raw 
                    (codbarras, farmacia_origen, url_origen, url_imagen, texto_extraido, procesado_fase3)
                    VALUES (?, ?, ?, ?, ?, 0)
                END
            """, (codbarras, u, codbarras, dom_str, u, img_url, fd['texto']))
            conn.commit()

            fuentes_web.append({
                "url": fd['url'],
                "texto": fd['texto']
            })
            
            for img in fd['imagenes']:
                if img not in imagenes_vistas:
                    imagenes_vistas.add(img)
                    todas_imagenes.append(img)
    
    # Marcar el EAN como extraído localmente (aunque el motor IA use la tabla, en nuestra prueba multimodal usamos JSON)
    cursor.execute("UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase2 = 1 WHERE codbarras = ?", (codbarras,))
    conn.commit()

    print(f"  Descargando y codificando hasta 3 imágenes en Base64...")
    imagenes_b64 = obtener_imagenes_b64(todas_imagenes)
    
    # Devolver estructura empaquetada
    return {
        "ean": codbarras,
        "descripcion": desc,
        "fuentes_web": fuentes_web,
        "imagenes_b64": imagenes_b64
    }

def main():
    print("INICIANDO FASE 1: Scraping y Acumulación de Datos")
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    resultados_json = []
    
    for ean in EANS_TEST:
        cursor.execute("SELECT descrip1art FROM Procurement.por_aprobacion_equivalencias WHERE codbarras = ?", (ean,))
        row = cursor.fetchone()
        if row:
            desc = row[0]
            resultado_ean = procesar_ean(conn, cursor, ean, desc)
            if resultado_ean:
                resultados_json.append(resultado_ean)
                
    # Guardar un JSON consolidado, esto es la "foto" exacta que se le pasará a la IA.
    output_path = "scratch/scraping_multimodal_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados_json, f, indent=2, ensure_ascii=False)
        
    print(f"\nFase 1 completada. Resultados consolidados guardados en {output_path}")
    conn.close()

if __name__ == "__main__":
    main()
