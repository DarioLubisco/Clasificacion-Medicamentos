import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
socket.setdefaulttimeout(180)
from MDM_Unified_Mapper import MasterCatalog

gasto_lock = threading.Lock()

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GASTO_ACUMULADO_USD = 0.0
MAX_BUDGET_USD = 5.00

def obtener_taxonomias_estrictas():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
        conn.close()
        return "\n".join(tax)
    except Exception as e:
        print(f"Error cargando taxonomia: {e}")
        return ""

def llamar_openrouter_strict(batch_json_str, taxonomias_existentes, model="google/gemini-2.5-pro"):
    global GASTO_ACUMULADO_USD
    if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD:
        print("ALERTA: Presupuesto agotado.")
        return None
        
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
    - contenido_neto (float o null)
    - contenido_neto_unidad_Des (string o null)
    - fabricante (string o null)
    - marca (string o null)
    - origen (string o null)
    - codigo_atc (string o null)
    - blister (1 o 0)
    - generico (1 o 0)
    - clasificacion_insumo_Des (string o null, ej: Inyectadora, Pañal)

    REGLAS ESTRICTAS ANTI-ALUCINACIÓN:
    1. ATC: NO deduzcas el código ATC. Solo extráelo si aparece explícitamente.
    2. Contenido Neto vs Concentración: La concentración (ej. 500mg) NO es el contenido neto. El contenido neto es el volumen/peso total del envase (ej. 120ml).
    3. Marca / Fabricante / Origen: Si no hay información explícita, usa null. NO asumas 'Genérico' como marca.
    4. Segmento Etario: NO lo deduzcas sin evidencia (infantil, niños, pediátrico, adulto). Ante la duda, null.

    REGLA DE TAXONOMIA (INQUEBRANTABLE):
    ESTAS SON LAS ÚNICAS CATEGORÍAS Y SUBCATEGORÍAS PERMITIDAS. Tienes prohibido inventar o usar sinónimos.
    Si el producto no encaja, debes devolver SINEVAL en la categoría y/o subcategoría.
    {taxonomias_existentes}
    
    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web.
    4 - ALTA: Se deduce lógicamente con total certeza científica, aunque haya diferencias menores en campos no críticos.
    3 - MEDIA: Información suficiente pero con discrepancias entre sitios o ambigüedad leve.
    2 - BAJA: Inferencias o aproximaciones por información escasa o contradictoria.
    1 - NULA: Falta de información crítica. Obligado a usar null en la mayoría de campos.

    Debes generar una llave "razonamiento" explicando tu análisis paso a paso para cada producto.
    
    Devuelve ÚNICAMENTE un array JSON válido con este formato:
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
        "temperature": 0.1,
        "max_tokens": 8192
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tokens = usage.get('prompt_tokens', 0)
                c_tokens = usage.get('completion_tokens', 0)
                costo = (p_tokens * 1.25 + c_tokens * 5.00) / 1000000.0 # Aproximado Gemini
                
                with gasto_lock:
                    GASTO_ACUMULADO_USD += costo
                print(f"  [IA] {model} | Costo req: ${costo:.5f} | Acumulado: ${GASTO_ACUMULADO_USD:.5f}")
                
                content = result['choices'][0]['message']['content']
                if content.startswith("```json"): content = content[7:]
                if content.endswith("```"): content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            print(f"  Error llamando a OpenRouter ({model}): {e}")
            time.sleep(5)
    return None

def llamar_vision_multimodal(codbarras, desc, url_imagenes, model="google/gemini-2.5-flash"):
    """
    Fase 2 Visual: Si falla la extracción de texto, enviamos las imágenes codificadas en Base64.
    """
    import base64
    
    valid_urls = [u for u in url_imagenes if u and u.strip().startswith(('http://', 'https://'))]
    if not valid_urls:
        print(f"  [Vision] Sin URLs de imagen válidas y absolutas para EAN {codbarras}")
        return None
        
    base64_imgs = []
    for img_url in valid_urls[:5]: # Evaluamos hasta 5 por si algunas fallan la descarga
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
            with urllib.request.urlopen(req, timeout=8) as response:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                if 'image' not in content_type and 'octet-stream' not in content_type:
                    continue
                img_data = response.read()
                # Si el tipo es octet-stream o no se pudo determinar, forzamos image/jpeg
                if 'image' not in content_type:
                    content_type = 'image/jpeg'
                encoded = base64.b64encode(img_data).decode('utf-8')
                base64_imgs.append(f"data:{content_type};base64,{encoded}")
                if len(base64_imgs) >= 3: # Max 3 imagenes base64
                    break
        except Exception as e:
            continue

    if not base64_imgs:
        print(f"  [Vision] No se pudo descargar ninguna imagen para EAN {codbarras}")
        return None

    print(f"  [Vision] Analizando {len(base64_imgs)} imagenes en Base64 para EAN {codbarras} usando {model}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Armamos contenido multimodal
    content_payload = [
        {"type": "text", "text": f"Observa esta caja de medicamento/producto (EAN: {codbarras}, Desc: {desc}) en sus distintos ángulos. Extrae ÚNICAMENTE el nombre comercial (Marca), el laboratorio (Fabricante) y el país o región de manufactura (Origen) que ves impreso explícitamente en el empaque. Devuelve JSON: {{\"marca\": \"...\", \"fabricante\": \"...\", \"origen\": \"...\", \"razonamiento_visual\": \"...\"}}"}
    ]
    for b64_img in base64_imgs:
        content_payload.append({"type": "image_url", "image_url": {"url": b64_img}})

    data = {
        "model": model,
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content']
            return json.loads(content)
    except Exception as e:
        print(f"  Error Vision: {e}")
        return None

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
    es_med = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    
    # 1. Filtro Sine qua non (Zero-Tolerance)
    if es_med:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
            
    # 2. Puntos
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

def procesar_bloque_con_bd(lote_scraper_json):
    """
    Toma el archivo investigacion_resultados_v11.json (que tiene los bloques de texto + array de imagenes)
    y orquesta todo el pipeline: Textual -> Score -> Si Falla -> Multimodal Visual -> Genera SQL.
    """
    taxonomias_str = obtener_taxonomias_estrictas()
    if not taxonomias_str:
        print("ERROR CRITICO: Taxonomia vacía. Ejecuta seed_taxonomia.py primero.")
        return

    with open(lote_scraper_json, "r", encoding="utf-8") as f:
        lote_web = json.load(f)

    resultados_finales = []
    chunk_size = 5
    
    print(f"\n--- MEGA ORQUESTADOR V3 INICIADO ---")
    for i in range(0, len(lote_web), chunk_size):
        chunk = lote_web[i:i+chunk_size]
        print(f"Procesando Chunk {i//chunk_size + 1}...")
        
        # Le enviamos el chunk con sus bloques de texto a Gemini Pro
        res_textual = llamar_openrouter_strict(json.dumps(chunk, indent=2), taxonomias_str)
        if not res_textual: continue
        
        for item_txt in res_textual:
            codbarras = item_txt.get('registro', {}).get('codbarras')
            if not codbarras: continue
            
            atrib = item_txt.get('atributos_nuevos_consolidados', {})
            
            # Buscar el bloque original para sacar las imagenes_urls
            bloque_orig = next((x for x in chunk if x['registro']['codbarras'] == codbarras), None)
            url_imagenes_todas = []
            if bloque_orig and 'fuentes_web' in bloque_orig:
                for fte in bloque_orig['fuentes_web']:
                    if fte and 'imagenes_encontradas' in fte:
                        url_imagenes_todas.extend(fte['imagenes_encontradas'])
                        
            # Evaluar Score para ver si aplicamos Vision
            score = calcular_score_calidad(atrib)
            
            necesita_vision = False
            if score < 100:
                # Si es medicina y le falta marca/fabricante/origen, intentar vision
                if not atrib.get('marca') or not atrib.get('fabricante') or not atrib.get('origen'):
                    necesita_vision = True
                    
            if necesita_vision and url_imagenes_todas:
                desc_orig = item_txt['registro'].get('descripcion_original', '')
                res_visual = llamar_vision_multimodal(codbarras, desc_orig, url_imagenes_todas)
                if res_visual:
                    # Mezclamos
                    if res_visual.get('marca') and not atrib.get('marca'):
                        atrib['marca'] = res_visual['marca']
                    if res_visual.get('fabricante') and not atrib.get('fabricante'):
                        atrib['fabricante'] = res_visual['fabricante']
                    if res_visual.get('origen') and not atrib.get('origen'):
                        atrib['origen'] = res_visual['origen']
                    atrib['razonamiento'] = atrib.get('razonamiento','') + " | VISUAL: " + res_visual.get('razonamiento_visual', '')
                    
                    # Recalcular score
                    score = calcular_score_calidad(atrib)
            
            item_txt['score_calidad'] = score
            item_txt['url_imagenes'] = url_imagenes_todas
            resultados_finales.append(item_txt)
            
    # --- GENERACION SQL ---
    if resultados_finales:
        catalog = MasterCatalog(CONN_STR)
        sql_stmts = []
        for item in resultados_finales:
            atrib = item.get('atributos_nuevos_consolidados', {})
            codbarras = item['registro']['codbarras']
            score = item['score_calidad']
            urls_img = item.get('url_imagenes', [])
            
            atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
            
            def fmt(val, is_string=True):
                if val is None or str(val).strip() == '' or str(val).lower() == 'null': return "NULL"
                val_str = str(val).strip()
                if val_str.lower() == 'true': return "1"
                if val_str.lower() == 'false': return "0"
                if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
                return val_str
                
            dominio = atrib.get('dominio', 'SINEVAL')
            categoria = atrib.get('categoria', 'SINEVAL')
            subcategoria = atrib.get('subcategoria', 'SINEVAL')
            es_med = (dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO'])
            
            # Estado estricto
            if score >= 85 or (not es_med and score >= 60):
                estado_ciclo = 'CERRADO'
            else:
                estado_ciclo = 'REVISION_MANUAL' # Falló las pruebas rigurosas
                
            obs = fmt(atrib.get('razonamiento')[:1999]) if atrib.get('razonamiento') else "NULL"
            img_json = fmt(json.dumps(urls_img)) if urls_img else "NULL"
            
            set_clauses = [
                f"principio_activo_Des = {fmt(atrib.get('principio_activo'))}",
                f"concentracion_Des = {fmt(atrib.get('concentracion'))}",
                f"forma_farmaceutica_Des = {fmt(atrib.get('forma_farmaceutica'))}",
                f"fabricante_Des = {fmt(atrib.get('fabricante'))}",
                f"marca_Des = {fmt(atrib.get('marca'))}",
                f"origen_Des = {fmt(atrib.get('origen'))}",
                f"codigo_atc_Des = {fmt(atrib.get('codigo_atc'))}",
                f"requiere_recipe = {fmt(atrib.get('requiere_recipe'), False)}",
                f"generico = {fmt(atrib.get('generico'), False)}",
                f"cantidad_presentacion = {fmt(atrib.get('cantidad_presentacion'), False)}",
                f"contenido_neto = {fmt(atrib.get('contenido_neto'), False)}",
                f"contenido_neto_unidad_Des = {fmt(atrib.get('contenido_neto_unidad_Des'))}",
                f"segmento_etario = {fmt(atrib.get('segmento_etario'))}",
                f"clasificacion_insumo_Des = {fmt(atrib.get('clasificacion_insumo_Des'))}",
                f"es_medicamento = {1 if es_med else 0}",
                f"score_calidad = {score}",
                f"estado_ciclo = '{estado_ciclo}'",
                f"observaciones_ia = {obs}",
                f"origen_dato = 'IA_INVESTIGATED_V11_MULTIMODAL'",
                f"imagen_urls = {img_json}"
            ]
            
            # IDs
            id_pa = catalog.find_id("principio_activo", atrib.get('principio_activo'))
            id_con = catalog.find_id("concentracion", atrib.get('concentracion'))
            id_ff = catalog.find_id("forma_farmaceutica", atrib.get('forma_farmaceutica'))
            set_clauses.extend([
                f"principio_activo = {fmt(id_pa, False)}",
                f"concentracion = {fmt(id_con, False)}",
                f"forma_farmaceutica = {fmt(id_ff, False)}"
            ])
            
            sql_block = f"""
            BEGIN
                DECLARE @id_taxonomia INT;
                SELECT @id_taxonomia = id_taxonomia FROM Procurement.Taxonomia 
                WHERE dominio = {fmt(dominio)} AND ISNULL(categoria, 'SINEVAL') = {fmt(categoria)} AND ISNULL(subcategoria, 'SINEVAL') = {fmt(subcategoria)};
                  
                UPDATE Procurement.por_aprobacion_equivalencias 
                SET {', '.join(set_clauses)}, id_taxonomia = @id_taxonomia
                WHERE codbarras = '{codbarras}';
            END
            """
            sql_stmts.append(sql_block)
            
        with open("actualizacion_v3.sql", "w", encoding="utf-8") as f:
            f.write('\nGO\n'.join(sql_stmts))
            
        print("Ejecutando SQL en la base de datos...")
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        for stmt in sql_stmts:
            try: cursor.execute(stmt)
            except Exception as e: print(f"Error SQL: {e}")
        conn.commit()
        conn.close()
        print(f"Completado. Actualizados {len(sql_stmts)} registros.")

if __name__ == "__main__":
    import sys
    file_in = sys.argv[1] if len(sys.argv) > 1 else "investigacion_resultados_v11.json"
    procesar_bloque_con_bd(file_in)
