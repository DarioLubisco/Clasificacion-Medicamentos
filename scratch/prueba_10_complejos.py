import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import socket
import threading
import sys
import os
import requests
import re
from duckduckgo_search import DDGS
from dotenv import load_dotenv

socket.setdefaulttimeout(180)

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MDM_Unified_Mapper import MasterCatalog

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
VALUESERP_API_KEY = os.getenv("VALUESERP_API_KEY", "9B1D5AA5918946FBBC1515858FB56E1A")
SCRAPLING_API_URL = "http://127.0.0.1:8005/scrape"
PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search", "pinterest", "youtube"]

EANS_TEST = [
    '0000000072410', # Amoxicilina/Ácido Clavulánico
    '0000000104098', # Diosmina y Hesperidina
    '0000020000264', # Nifedipino LP
    '0000001100181', # Jarabe de Passiflora Plus
    '0000001100198', # Senolax Jarabe
    '0000025525748', # Jarabe de berro
    '000000000130',  # Ondansetrón ampollas
    '0000000107839', # Vancomicina ampollas
    '0000000193009', # Lidocaína crema
    '0000075970543'  # Crema Sulfurcis azufre ivermectina
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

def extraer_fuente_web(url: str, idx: int) -> dict:
    try:
        response = requests.post(SCRAPLING_API_URL, json={"url": url}, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if "error" not in data:
                return {
                    "url": url,
                    "texto": limpiar_html_regex(data.get("content", "")),
                    "imagenes": extraer_imagenes_regex(data.get("content", ""), url)
                }
    except Exception as e:
        pass
    return None

def obtener_taxonomias_estrictas():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
        conn.close()
        return "\n".join(tax)
    except Exception as e:
        return ""

def llamar_openrouter_strict(batch_json_str, taxonomias_existentes, model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Tu único objetivo es la PRECISIÓN ABSOLUTA (Zero-Tolerance). Extraer un dato que no está explícitamente en la descripción o en el contexto web adjunto es un ERROR CRÍTICO. Ante la menor duda, debes devolver null.

    Para cada producto, extrae los siguientes atributos:
    - dominio (string OBLIGATORIO)
    - categoria (string OBLIGATORIO)
    - subcategoria (string OBLIGATORIO)
    - principio_activo (string o null si no aplica/es insumo)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - cantidad_presentacion (int o null)
    - contenido_neto (float o null, formato numérico entero si no tiene decimales ej. 500)
    - contenido_neto_unidad_Des (string o null)
    - fabricante (string o null)
    - marca (string o null)
    - origen (string o null)
    - codigo_atc (string o null)
    - blister (1 o 0)
    - generico (1 o 0)
    - clasificacion_insumo_Des (string o null, ej: Inyectadora, Pañal)

    REGLAS ESTRICTAS ANTI-ALUCINACIÓN Y DE NEGOCIO:
    1. ATC: NO deduzcas el código ATC. Solo extráelo si aparece explícitamente.
    2. Sólidos vs Líquidos/Tópicos: 
       - Sólidos (Tabletas/Cápsulas): cantidad_presentacion = total de unidades (ej. 20), contenido_neto = 1, contenido_neto_unidad_Des = 'Caja' o 'Blister'.
       - Líquidos/Cremas/Pomadas: cantidad_presentacion = total de envases (ej. 1), contenido_neto = volumen/peso (ej. 120 o 500 sin decimales '.0'), contenido_neto_unidad_Des = 'ml' o 'g'.
    3. Forma Farmacéutica: Simplifica formas complejas a su familia base (ej. "Comprimido de liberación prolongada" -> "Comprimido"). MANTÉN la vía de administración si es crítica (ej. "Solución Oftálmica").
    4. Marca / Fabricante / Origen: Si no hay información explícita, usa null. NO asumas 'Genérico' como marca.
    5. Segmento Etario: NO lo deduzcas sin evidencia (infantil, niños, pediátrico, adulto). Ante la duda, null.

    REGLA DE TAXONOMIA (INQUEBRANTABLE):
    {taxonomias_existentes}
    
    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web.
    4 - ALTA: Se deduce lógicamente con total certeza científica, aunque haya diferencias menores en campos no críticos.
    3 - MEDIA: Información suficiente pero con discrepancias entre sitios o ambigüedad leve.
    2 - BAJA: Inferencias o aproximaciones por información escasa o contradictoria.
    1 - NULA: Falta de información crítica.
    
    Devuelve ÚNICAMENTE un array JSON válido con este formato exacto:
    [
      {{
        "registro": {{"codbarras": "...", "descripcion_original": "..."}},
        "atributos_nuevos_consolidados": {{"razonamiento": "...", "confianza_nivel": 5, "confianza_razonamiento": "...", "dominio": "...", "categoria": "...", "subcategoria": "...", "principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR (Contexto Web Incluido en Bloques):
    {batch_json_str}
    """
    
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content']
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip())
    except Exception as e:
        print(f"    Error {model}: {e}")
        return None

def llamar_vision_multimodal(codbarras, desc, url_imagenes):
    import base64
    valid_urls = [u for u in url_imagenes if u and u.strip().startswith(('http://', 'https://'))]
    if not valid_urls: return None
    
    base64_imgs = []
    for img_url in valid_urls[:3]:
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                img_data = response.read()
                encoded = base64.b64encode(img_data).decode('utf-8')
                base64_imgs.append(f"data:{content_type};base64,{encoded}")
        except: continue
        
    if not base64_imgs: return None
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    content_payload = [
        {"type": "text", "text": f"Observa esta caja de medicamento (EAN: {codbarras}, Desc: {desc}). Extrae: marca, fabricante, origen, principio_activo, concentracion, forma_farmaceutica, cantidad_presentacion, contenido_neto. Devuelve JSON: {{\"marca\": \"...\", \"fabricante\": \"...\", \"origen\": \"...\", \"principio_activo\": \"...\", \"concentracion\": \"...\", \"forma_farmaceutica\": \"...\", \"cantidad_presentacion\": \"...\", \"contenido_neto\": \"...\", \"confianza_nivel\": 5, \"confianza_razonamiento\": \"...\"}}"}
    ]
    for b64_img in base64_imgs:
        content_payload.append({"type": "image_url", "image_url": {"url": b64_img}})
        
    data = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            return json.loads(result['choices'][0]['message']['content'])
    except: return None

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
    es_med = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    
    if es_med:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
            
    if atrib.get('principio_activo'): score += 15
    if atrib.get('concentracion'): score += 15
    if atrib.get('forma_farmaceutica'): score += 15
    if tiene_cant: score += 10
    if atrib.get('contenido_neto'): score += 5
    if atrib.get('origen'): score += 10
    if atrib.get('segmento_etario'): score += 10
    if atrib.get('fabricante'): score += 5
    if atrib.get('marca'): score += 5
    if atrib.get('codigo_atc'): score += 5
    if atrib.get('generico') in [1, 0]: score += 5
    
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val: return "NO_DEFINIDO"
    v = str(val).upper().strip()
    if "ADULTO" in v: return "ADULTO"
    if "PEDIATRICO" in v or "INFANTIL" in v or "NIÑO" in v: return "PEDIATRICO"
    if "NEONATAL" in v or "BEBE" in v: return "NEONATAL"
    if "MIXTO" in v: return "MIXTO"
    if "GENERAL" in v or "TODO" in v: return "GENERAL"
    return "NO_DEFINIDO"

def fmt(val, is_string=True):
    if val is None or str(val).strip() == '' or str(val).lower() == 'null': return "NULL"
    val_str = str(val).strip()
    if val_str.lower() == 'true': return "1"
    if val_str.lower() == 'false': return "0"
    if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
    
    try:
        num_clean = val_str.replace(',', '.')
        float(num_clean)
        return num_clean
    except ValueError:
        import re
        nums = re.findall(r'\d+(?:\.\d+)?', val_str)
        if nums: return nums[0]
        return "NULL"

def run_fase2_for_ean(conn, cursor, codbarras, desc):
    # Verificar si ya existe en raw
    cursor.execute("SELECT COUNT(*) FROM Procurement.scraping_farmacias_raw WHERE codbarras = ?", (codbarras,))
    if cursor.fetchone()[0] > 0:
        return
        
    print(f"  [Scraping] Scrapeando {desc} ({codbarras})...")
    urls = buscar_en_internet(f"{codbarras}", max_fuentes=6)
    if not urls:
        urls = buscar_en_internet(f"{desc} prospecto Vademecum", max_fuentes=6)
        
    for idx, u in enumerate(urls, 1):
        fd = extraer_fuente_web(u, idx)
        if fd:
            dom = re.search(r'https?://([^/]+)', u)
            dom_str = dom.group(1) if dom else "Desconocido"
            img = fd['imagenes'][0] if fd['imagenes'] else None
            cursor.execute("""
                INSERT INTO Procurement.scraping_farmacias_raw 
                (codbarras, farmacia_origen, url_origen, url_imagen, texto_extraido, procesado_fase3)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (codbarras, dom_str, u, img, fd['texto']))
            
    cursor.execute("UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase2 = 1 WHERE codbarras = ?", (codbarras,))

def main():
    taxonomias_str = obtener_taxonomias_estrictas()
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    # 1. Asegurar scraping de las 10 medicinas
    print("--- FASE 1: Asegurando Scraping para los 10 EANs ---")
    for ean in EANS_TEST:
        cursor.execute("SELECT descrip1art FROM Procurement.por_aprobacion_equivalencias WHERE codbarras = ?", (ean,))
        row = cursor.fetchone()
        if row:
            desc = row[0]
            run_fase2_for_ean(conn, cursor, ean, desc)
            
    print("\n--- FASE 2: Extrayendo Datos con ambos Modelos ---")
    
    modelos = {
        "gemini_2_5_pro": "google/gemini-2.5-pro",
        "gemini_3_1_pro": "google/gemini-3.1-pro-preview"
    }
    
    resultados_comparativa = {}
    
    for ean in EANS_TEST:
        cursor.execute("SELECT descrip1art FROM Procurement.por_aprobacion_equivalencias WHERE codbarras = ?", (ean,))
        desc = cursor.fetchone()[0]
        
        cursor.execute("SELECT texto_extraido, url_imagen FROM Procurement.scraping_farmacias_raw WHERE codbarras = ?", (ean,))
        bloques = cursor.fetchall()
        
        fuentes_web = [{"url": "http://mock", "texto": b[0]} for b in bloques if b[0]]
        imagenes = [b[1] for b in bloques if b[1]]
        
        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]
        
        res_ean = {"descripcion": desc}
        
        for key, model_id in modelos.items():
            print(f"  Evaluando {ean} con {key}...")
            res_txt = llamar_openrouter_strict(json.dumps(context_block, indent=2), taxonomias_str, model_id)
            if res_txt and len(res_txt) > 0:
                atrib = res_txt[0].get('atributos_nuevos_consolidados', {})
                score = calcular_score_calidad(atrib)
                
                # Fallback Visión
                necesita_vision = score < 100 and (not atrib.get('marca') or not atrib.get('fabricante') or not atrib.get('principio_activo'))
                if necesita_vision and imagenes:
                    res_vis = llamar_vision_multimodal(ean, desc, imagenes)
                    if res_vis:
                        for campo in ['marca', 'fabricante', 'origen', 'principio_activo', 'concentracion', 'forma_farmaceutica', 'cantidad_presentacion', 'contenido_neto']:
                            if res_vis.get(campo) and not atrib.get(campo):
                                atrib[campo] = res_vis[campo]
                        score = calcular_score_calidad(atrib)
                        
                atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
                res_ean[key] = {
                    "atrib": atrib,
                    "score": score
                }
            else:
                res_ean[key] = None
                
        resultados_comparativa[ean] = res_ean
        
    # Guardar comparativa en JSON local para no perder datos
    with open("scratch/resultados_comparativa.json", "w", encoding="utf-8") as f:
        json.dump(resultados_comparativa, f, indent=2, ensure_ascii=False)
        
    print("\n--- COMPARACIÓN DE MODELOS ---")
    for ean, res in resultados_comparativa.items():
        print(f"\nEAN: {ean} - {res['descripcion']}")
        p25 = res.get('gemini_2_5_pro')
        p31 = res.get('gemini_3_1_pro')
        
        if p25 and p31:
            a25 = p25['atrib']
            a31 = p31['atrib']
            print(f"  | Atributo | Gemini 2.5 Pro | Gemini 3.1 Pro |")
            print(f"  |---|---|---|")
            print(f"  | Dominio | {a25.get('dominio')} | {a31.get('dominio')} |")
            print(f"  | P. Activo | {a25.get('principio_activo')} | {a31.get('principio_activo')} |")
            print(f"  | Concentración | {a25.get('concentracion')} | {a31.get('concentracion')} |")
            print(f"  | Forma Farm. | {a25.get('forma_farmaceutica')} | {a31.get('forma_farmaceutica')} |")
            print(f"  | Cant. Pres. | {a25.get('cantidad_presentacion')} | {a31.get('cantidad_presentacion')} |")
            print(f"  | Cont. Neto | {a25.get('contenido_neto')} {a25.get('contenido_neto_unidad_Des')} | {a31.get('contenido_neto')} {a31.get('contenido_neto_unidad_Des')} |")
            print(f"  | Confianza | {a25.get('confianza_nivel')} | {a31.get('confianza_nivel')} |")
            print(f"  | Calidad Score | {p25['score']} | {p31['score']} |")
        else:
            print("  [Error] Uno de los modelos falló en retornar respuesta.")
            
    conn.close()

if __name__ == "__main__":
    main()
