import os
from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import requests
import re
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from openai import OpenAI
from limpiador_farmaceutico_regex import procesar_farmacos

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
INPUT_FILE = "input_scraper_v10.json"
OUTPUT_JSON = "investigacion_resultados_v10.json"
OUTPUT_SQL = "actualizacion_scraper_v10.sql"

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
        from duckduckgo_search import DDGS
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

def pre_clasificar_medicamento(desc: str) -> bool:
    # prompt simple para determinar si es medicamento o insumo
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

def analizar_con_llm(texto_contexto: str, desc: str, codbarras: str, is_web: bool, is_med: bool) -> dict:
    contexto = f"TEXTO EXTRAÍDO DE LA WEB:\n---\n{texto_contexto}\n---\n" if is_web else "NO HAY CONTEXTO WEB, DEDUCE ÚNICAMENTE DE LA DESCRIPCIÓN.\n"
    
    is_med_str = "MEDICAMENTO" if is_med else "INSUMO MÉDICO / DERMOCOSMÉTICA / EQUIPO"
    
    prompt = f"""
    Eres el Agente Autónomo de Investigación Farmacéutica V.10.1.
    Analiza el producto con código de barras "{codbarras}" y descripción original "{desc}".
    El producto ha sido pre-clasificado como: {is_med_str}.
    
    {contexto}
    
    Extrae y normaliza los siguientes atributos:
    SI ES MEDICAMENTO:
    1. principio_activo: Nombres químicos. Si hay varios, extráelos crudos separados por guion o coma, sin ordenarlos.
    2. concentracion: Si hay varios, extráelos crudos en el mismo orden. No uses '/' para separar ingredientes.
    3. forma_farmaceutica.
    4. codigo_atc.
    5. requiere_recipe: 1 o 0.
    6. generico: 1 o 0.
    7. segmento_etario.
    
    SI ES INSUMO/COSMÉTICO/EQUIPO:
    1. clasificacion_insumo: Taxonomía principal (ej: Protector Solar, Jeringa, Crema Hidratante, Gasa, Leche de Fórmula).
    (Los atributos exclusivos de medicamento como principio_activo, concentracion, atc, receta van en null).
    
    PARA AMBOS (Si aplican):
    - blister: 1 o 0. (Si el código empieza por BLI_, es 1).
    - origen: País de fabricación.
    - marca: Nombre comercial.
    - fabricante: Laboratorio fabricante.
    - cantidad_presentacion: Entero (Ej: 30).
    - contenido_neto: Volumen o peso (Ej: 120ML, 30G). Sólidos = null.
    - url_imagen: URL a imagen.
    
    Devuelve ÚNICAMENTE un JSON válido con estas llaves exactas. Las llaves que no apliquen, ponlas en null.
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"  Error en OpenRouter: {e}")
        return {}

def procesar_lote():
    if not os.path.exists(INPUT_FILE):
        print(f"Archivo {INPUT_FILE} no encontrado.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lote = json.load(f)

    resultados = []
    
    for i, item in enumerate(lote):
        codbarras = item.get("codbarras", "").strip()
        desc = item.get("descrip1art", "").strip()
        codigo = item.get("codigo", "")
        
        print(f"\n[{i+1}/{len(lote)}] Analizando: {desc} (EAN: {codbarras})")
        
        # Paso 1: Validación EAN-13
        is_bli = codbarras.startswith("BLI_")
        is_internal = is_bli or len(codbarras) != 13
        
        # Paso 2: Triaje (¿Es medicamento?)
        is_med = pre_clasificar_medicamento(desc)
        
        if not is_med:
            print("  Clasificado como INSUMO MEDICO. Saltando busqueda web.")
            url_fuente = "N/A (Insumo)"
            texto_web = ""
        else:
            url_fuente = "N/A (Código Interno)"
            texto_web = ""
            
            if not is_internal:
                # Paso 3: Investigación Web (Solo EAN-13 válidos)
                url = buscar_en_internet(f"{codbarras}")
                if not url:
                    print("  Buscando por EAN falló, intentando por descripción...")
                    url = buscar_en_internet(f"{desc} prospecto Vademecum")
                
                if url:
                    url_fuente = url
                    texto_web = extraer_texto_web(url)
                    if not texto_web:
                        url_fuente = "Extracción Fallida"
                else:
                    url_fuente = "No se encontraron URLs"
            else:
                print(f"  Código interno ({codbarras}). Extrayendo atributos solo desde la descripción.")
                
        # Paso 4: Extracción de Atributos LLM
        datos = analizar_con_llm(texto_web, desc, codbarras, bool(texto_web), is_med)
        if is_bli:
            datos["blister"] = 1
            
        resultados.append({
            "registro": { "codigo": codigo, "codbarras": codbarras, "descripcion_original": desc, "fuente_web_consultada": url_fuente },
            "atributos": datos,
            "investigacion_exitosa": bool(datos),
            "es_medicamento": 1 if is_med else 0
        })
        
        time.sleep(1)

    # Guardar JSON final
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nProceso completado. JSON guardado en {OUTPUT_JSON}")

    # Generar SQL de Actualización
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("BEGIN TRANSACTION;\n\n")
        for res in resultados:
            cod = res["registro"]["codigo"]
            attr = res["atributos"]
            es_med = res["es_medicamento"]
            
            # Limpieza con regex de PA y Conc
            observaciones = ""
            if es_med == 1:
                res_limpieza = procesar_farmacos(attr.get('principio_activo'), attr.get('concentracion'))
                if res_limpieza["exito"]:
                    attr['principio_activo'] = res_limpieza["principio_activo"]
                    attr['concentracion'] = res_limpieza["concentracion"]
                    if res_limpieza["observaciones"]:
                        observaciones = res_limpieza["observaciones"]
                else:
                    attr['principio_activo'] = None
                    attr['concentracion'] = None
                    observaciones = res_limpieza["observaciones"]
            
            # Truncate helpers
            def t(val, length):
                if val is None: return "NULL"
                s = str(val).replace("'", "''")
                return f"'{s[:length]}'"
            
            f.write(f"UPDATE Procurement.por_aprobacion_equivalencias SET ")
            
            if es_med == 0:
                f.write(f"es_medicamento = 0, ")
                f.write(f"clasificacion_insumo_Des = {t(attr.get('clasificacion_insumo'), 255)}, ")
                f.write(f"principio_activo_Des = NULL, concentracion_Des = NULL, forma_farmaceutica_Des = NULL, codigo_atc_Des = NULL, requiere_recipe_Des = NULL, segmento_etario_Des = NULL, generico_Des = NULL, ")
            else:
                f.write(f"es_medicamento = 1, ")
                f.write(f"clasificacion_insumo_Des = NULL, ")
                f.write(f"principio_activo_Des = {t(attr.get('principio_activo'), 255)}, ")
                f.write(f"concentracion_Des = {t(attr.get('concentracion'), 255)}, ")
                f.write(f"forma_farmaceutica_Des = {t(attr.get('forma_farmaceutica'), 255)}, ")
                f.write(f"codigo_atc_Des = {t(attr.get('codigo_atc'), 50)}, ")
                
                rec = attr.get('requiere_recipe')
                f.write(f"requiere_recipe_Des = {1 if rec else 0}, ")
                
                gen = attr.get('generico')
                f.write(f"generico_Des = {1 if gen else 0}, ")
                
                f.write(f"segmento_etario_Des = {t(attr.get('segmento_etario'), 100)}, ")
                
            # Common attributes
            f.write(f"origen_Des = {t(attr.get('origen'), 100)}, ")
            f.write(f"fabricante_Des = {t(attr.get('fabricante'), 255)}, ")
            f.write(f"marca_Des = {t(attr.get('marca'), 255)}, ")
            f.write(f"contenido_neto_Des = {t(attr.get('contenido_neto'), 100)}, ")
            
            bl = attr.get('blister')
            f.write(f"blister_Des = {1 if bl else 0}, ")
            
            cp = attr.get('cantidad_presentacion')
            f.write(f"cantidad_presentacion_Des = {int(cp) if cp is not None and str(cp).isdigit() else 'NULL'}, ")
            
            f.write(f"url_imagen = {t(attr.get('url_imagen'), 500)}, ")
            f.write(f"observaciones_ia = {t(observaciones, 500)}, ")
            f.write(f"origen_dato = 'IA_INVESTIGATED_V10' ")
            f.write(f"WHERE codigo = '{cod}';\n")
                
        f.write("\nCOMMIT;\n")
    print(f"SQL generado en {OUTPUT_SQL}")

if __name__ == "__main__":
    procesar_lote()
