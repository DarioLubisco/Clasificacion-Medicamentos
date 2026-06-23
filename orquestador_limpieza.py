import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import csv
from duckduckgo_search import DDGS
from openai import OpenAI

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
INPUT_CSV = "medicinas_a_limpiar.csv"
OUTPUT_JSON = "investigacion_limpieza_v10.json"
OUTPUT_SQL = "actualizacion_limpieza_v10.sql"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

PROHIBITED_DOMAINS = ["barcode", "upc", "ean", "lookup", "database", "upcitemdb", "ean-search"]

def is_valid_url(url, title):
    url_lower = url.lower()
    title_lower = title.lower()
    for pd in PROHIBITED_DOMAINS:
        if pd in url_lower or pd in title_lower:
            return False
    return True

def buscar_en_internet(query: str) -> str:
    print(f"  Buscando en DuckDuckGo: '{query}'")
    try:
        results = DDGS().text(query, max_results=5)
        for r in results:
            url = r.get('href', '')
            title = r.get('title', '')
            if url and is_valid_url(url, title):
                return url
        return None
    except Exception as e:
        print(f"  Error en busqueda web: {e}")
        return None

def extraer_texto_web(url: str) -> str:
    print(f"  Extrayendo datos (Scrapling) de: {url}")
    try:
        payload = {"url": url}
        response = requests.post(SCRAPLING_API_URL, json=payload, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                print(f"  Error Scrapling interno: {data['error']}")
                return ""
            html_content = data.get("content", "")
            return html_content[:20000] # Limitar tokens
        else:
            print(f"  Error en Scrapling (HTTP {response.status_code}): {response.text}")
            return ""
    except Exception as e:
        print(f"  Excepción en Scrapling: {e}")
        return ""

def analizar_con_llm(texto_contexto: str, desc: str, codbarras: str, is_web: bool) -> dict:
    contexto = f"TEXTO EXTRAÍDO DE LA WEB:\n---\n{texto_contexto}\n---\n" if is_web else "NO HAY CONTEXTO WEB, DEDUCE ÚNICAMENTE DE LA DESCRIPCIÓN.\n"
    
    prompt = f"""
    Eres el Agente Autónomo de Investigación Farmacéutica V.10.1.
    Analiza el MEDICAMENTO FARMACÉUTICO con código de barras "{codbarras}" y descripción original "{desc}".
    
    {contexto}
    
    Extrae y normaliza los siguientes atributos (SOBREESCRIBIENDO con la mejor información posible):
    1. principio_activo: Nombres químicos.
    2. concentracion: Sin espacios.
    3. forma_farmaceutica.
    4. codigo_atc (Búscalo, pero sin prioridad. Si no lo encuentras fácil, déjalo en null. NO te estanques en esto).
    5. requiere_recipe: 1 o 0.
    6. generico: 1 o 0.
    7. segmento_etario.
    
    OTROS ATRIBUTOS:
    - blister: 1 o 0. (Si el código empieza por BLI_, es 1).
    - origen: País de fabricación.
    - marca: Nombre comercial.
    - fabricante: Laboratorio fabricante.
    - cantidad_presentacion: Entero (Ej: 30).
    - contenido_neto: Volumen o peso (Ej: 120ML, 30G). Sólidos = null.
    - url_imagen: URL a imagen del producto real.
    
    Devuelve ÚNICAMENTE un JSON válido con estas llaves exactas. Las llaves que no apliquen o no encuentres, ponlas en null. No inventes datos.
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"  Error en OpenRouter: {e}")
        return {}

def leer_csv_y_procesar():
    if not os.path.exists(INPUT_CSV):
        print(f"Archivo {INPUT_CSV} no encontrado.")
        return

    # Leer CSV y filtrar filas malas
    lote = []
    with open(INPUT_CSV, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["codigo"].startswith("---") or "rows affected" in row["codigo"]:
                continue
            lote.append(row)
            
    resultados = []
    
    import concurrent.futures
    import threading

    resultados = []
    lock = threading.Lock()
    procesados = 0

    def procesar_item(item):
        nonlocal procesados
        codbarras = item.get("codbarras", "").strip()
        desc = item.get("descrip1art", "").strip()
        codigo = item.get("codigo", "").strip()
        
        is_bli = codbarras.startswith("BLI_")
        is_internal = is_bli or len(codbarras) != 13
        
        url_fuente = "N/A (Código Interno)"
        texto_web = ""
        
        if not is_internal:
            url = buscar_en_internet(f"{codbarras}")
            if not url:
                url = buscar_en_internet(f"{desc} prospecto Vademecum")
            
            if url:
                url_fuente = url
                texto_web = extraer_texto_web(url)
                if not texto_web:
                    url_fuente = "Extracción Fallida"
            else:
                url_fuente = "No se encontraron URLs"
            
        datos = analizar_con_llm(texto_web, desc, codbarras, bool(texto_web))
        if is_bli:
            datos["blister"] = 1
            
        res = {
            "registro": { "codigo": codigo, "codbarras": codbarras, "descripcion_original": desc, "fuente_web_consultada": url_fuente },
            "atributos": datos,
            "investigacion_exitosa": bool(datos),
            "es_medicamento": 1
        }

        with lock:
            resultados.append(res)
            procesados += 1
            if procesados % 10 == 0:
                print(f"[{procesados}/{len(lote)}] Procesados. (Último: {desc})")
                if procesados % 100 == 0:
                    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"Iniciando procesamiento de {len(lote)} items con 20 hilos...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(procesar_item, lote)

    # Guardar JSON final
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nProceso completado. JSON guardado en {OUTPUT_JSON}")

    # Generar SQL de Actualización
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("BEGIN TRANSACTION;\n\n")
        for res in resultados:
            cod = res["registro"]["codigo"]
            codbarras = res["registro"]["codbarras"]
            attr = res["atributos"]
            
            def t(val, length):
                if val is None: return "NULL"
                s = str(val).replace("'", "''")
                return f"'{s[:length]}'"
            
            f.write(f"UPDATE Procurement.por_aprobacion_equivalencias SET ")
            f.write(f"principio_activo_Des = {t(attr.get('principio_activo'), 255)}, ")
            f.write(f"concentracion_Des = {t(attr.get('concentracion'), 255)}, ")
            f.write(f"forma_farmaceutica_Des = {t(attr.get('forma_farmaceutica'), 255)}, ")
            f.write(f"codigo_atc_Des = {t(attr.get('codigo_atc'), 50)}, ")
            
            rec = attr.get('requiere_recipe')
            f.write(f"requiere_recipe_Des = {1 if rec else 0}, ")
            
            gen = attr.get('generico')
            f.write(f"generico_Des = {1 if gen else 0}, ")
            
            f.write(f"segmento_etario_Des = {t(attr.get('segmento_etario'), 100)}, ")
            f.write(f"origen_Des = {t(attr.get('origen'), 100)}, ")
            f.write(f"fabricante_Des = {t(attr.get('fabricante'), 255)}, ")
            f.write(f"marca_Des = {t(attr.get('marca'), 255)}, ")
            f.write(f"contenido_neto_Des = {t(attr.get('contenido_neto'), 100)}, ")
            
            bl = attr.get('blister')
            f.write(f"blister_Des = {1 if bl else 0}, ")
            
            cp = attr.get('cantidad_presentacion')
            f.write(f"cantidad_presentacion_Des = {int(cp) if cp is not None and str(cp).isdigit() else 'NULL'}, ")
            
            f.write(f"url_imagen = {t(attr.get('url_imagen'), 500)}, ")
            f.write(f"origen_dato = 'IA_INVESTIGATED_V10_CLEANSE' ")
            
            if cod != 'NULL':
                f.write(f"WHERE codigo = '{cod}';\n")
            else:
                f.write(f"WHERE codbarras = '{codbarras}' AND codigo IS NULL;\n")
                
        f.write("\nCOMMIT;\n")
    print(f"SQL generado en {OUTPUT_SQL}")

if __name__ == "__main__":
    leer_csv_y_procesar()
