import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import csv
import concurrent.futures
import threading
from duckduckgo_search import DDGS
from openai import OpenAI

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
INPUT_CSV = "medicinas_incompletas_lote2.csv"
OUTPUT_JSON = "investigacion_lote2_v10.json"
OUTPUT_SQL = "actualizacion_lote2_v10.sql"

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
    try:
        results = DDGS().text(query, max_results=3)
        for r in results:
            url = r.get('href', '')
            title = r.get('title', '')
            if url and is_valid_url(url, title):
                return url
        return None
    except:
        return None

def extraer_texto_web(url: str) -> str:
    try:
        payload = {"url": url}
        response = requests.post(SCRAPLING_API_URL, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")[:15000]
        return ""
    except:
        return ""

def analizar_con_llm(texto_contexto: str, desc: str, codbarras: str, is_web: bool) -> dict:
    contexto = f"CONTEXTO WEB:\n{texto_contexto}\n" if is_web else "SIN CONTEXTO WEB.\n"
    
    prompt = f"""
    Eres el Agente Experto de Clasificación Farmacéutica V.10.3.
    Analiza el producto: "{desc}" (EAN: {codbarras}).
    
    {contexto}
    
    TAREAS:
    1. Clasifica como MEDICAMENTO o INSUMO.
    
    SI ES MEDICAMENTO:
    - Extrae: principio_activo, concentracion, forma_farmaceutica, requiere_recipe (1/0), generico (1/0), segmento_etario.
    - codigo_atc: Búscalo pero NO te detengas si no es obvio.
    
    SI ES INSUMO MÉDICO / OTRO:
    - clasificacion_insumo: Crea una taxonomía detallada: "Categoría > Subcategoría > Tipo" 
      (Ej: "Consumible Médico > Catéteres > Jelco", "Cuidado Personal > Capilar > Champú").
    
    PARA AMBOS:
    - marca, fabricante, origen, cantidad_presentacion (entero), contenido_neto (volumen/peso), url_imagen, blister (1/0).
    
    Responde ÚNICAMENTE en JSON con estas llaves:
    {{
      "es_medicamento": 1/0,
      "principio_activo": str,
      "concentracion": str,
      "forma_farmaceutica": str,
      "codigo_atc": str,
      "requiere_recipe": 1/0,
      "generico": 1/0,
      "segmento_etario": str,
      "clasificacion_insumo": str,
      "marca": str,
      "fabricante": str,
      "origen": str,
      "cantidad_presentacion": int,
      "contenido_neto": str,
      "url_imagen": str,
      "blister": 1/0
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {}

def procesar():
    lote = []
    with open(INPUT_CSV, "r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["codigo"].startswith("---") or "rows affected" in row["codigo"]: continue
            lote.append(row)

    resultados = []
    lock = threading.Lock()
    procesados = 0

    def task(item):
        nonlocal procesados
        codbarras = item["codbarras"].strip()
        desc = item["descrip1art"].strip()
        codigo = item["codigo"].strip()
        
        is_internal = codbarras.startswith("BLI_") or len(codbarras) != 13
        texto_web = ""
        url_f = "N/A"
        
        if not is_internal:
            url = buscar_en_internet(f"{codbarras}")
            if not url: url = buscar_en_internet(f"{desc} prospecto")
            if url:
                url_f = url
                texto_web = extraer_texto_web(url)

        datos = analizar_con_llm(texto_web, desc, codbarras, bool(texto_web))
        
        with lock:
            resultados.append({
                "registro": {"codigo": codigo, "codbarras": codbarras, "desc": desc, "url": url_f},
                "atributos": datos
            })
            procesados += 1
            if procesados % 20 == 0:
                print(f"[{procesados}/{len(lote)}] Procesados...")
                if procesados % 100 == 0:
                    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"Procesando {len(lote)} items con 20 hilos...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(task, lote)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    # Generar SQL
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("BEGIN TRANSACTION;\n")
        for res in resultados:
            cod = res["registro"]["codigo"]
            cb = res["registro"]["codbarras"]
            attr = res["atributos"]
            if not isinstance(attr, dict): continue
            
            def t(val, length):
                if val is None or val == "": return "NULL"
                s = str(val).replace("'", "''")
                return f"'{s[:length]}'"
            
            es_med = attr.get("es_medicamento", 1)
            
            f.write("UPDATE Procurement.por_aprobacion_equivalencias SET ")
            f.write(f"es_medicamento = {1 if es_med else 0}, ")
            f.write(f"clasificacion_insumo_Des = {t(attr.get('clasificacion_insumo'), 255)}, ")
            f.write(f"principio_activo_Des = {t(attr.get('principio_activo'), 255)}, ")
            f.write(f"concentracion_Des = {t(attr.get('concentracion'), 255)}, ")
            f.write(f"forma_farmaceutica_Des = {t(attr.get('forma_farmaceutica'), 255)}, ")
            f.write(f"codigo_atc_Des = {t(attr.get('codigo_atc'), 50)}, ")
            f.write(f"requiere_recipe_Des = {1 if attr.get('requiere_recipe') else 0}, ")
            f.write(f"generico_Des = {1 if attr.get('generico') else 0}, ")
            f.write(f"segmento_etario_Des = {t(attr.get('segmento_etario'), 100)}, ")
            f.write(f"origen_Des = {t(attr.get('origen'), 100)}, ")
            f.write(f"fabricante_Des = {t(attr.get('fabricante'), 255)}, ")
            f.write(f"marca_Des = {t(attr.get('marca'), 255)}, ")
            f.write(f"contenido_neto_Des = {t(attr.get('contenido_neto'), 100)}, ")
            f.write(f"blister_Des = {1 if attr.get('blister') else 0}, ")
            f.write(f"cantidad_presentacion_Des = {int(attr.get('cantidad_presentacion')) if str(attr.get('cantidad_presentacion')).isdigit() else 'NULL'}, ")
            f.write(f"url_imagen = {t(attr.get('url_imagen'), 500)}, ")
            f.write(f"origen_dato = 'IA_INVESTIGATED_V10_LOTE2' ")
            
            if cod != 'NULL':
                f.write(f"WHERE codigo = '{cod}';\n")
            else:
                f.write(f"WHERE codbarras = '{cb}' AND codigo IS NULL;\n")
        f.write("COMMIT;\n")
    print("Listo.")

if __name__ == "__main__":
    procesar()
