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
from limpiador_farmaceutico_regex import procesar_farmacos

gasto_lock = threading.Lock()

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Global cost tracking
gasto_por_ciclo = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

def llamar_openrouter(batch_json_str, model, ciclo_actual):
    global gasto_por_ciclo
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Para cada producto, extrae los siguientes atributos basándote en la descripción:
    - principio_activo (string o null si no aplica/es material médico)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - fabricante (string o null)
    - marca (string o null, si es un medicamento genérico sin marca comercial aparente, escribe "Generico")
    - origen (string o null, nación o país de origen de fabricación, ej. 'VENEZUELA', 'USA')
    - segmento_etario (string o null, ej. 'ADULTO', 'PEDIATRICO', 'PEDIATRICO/ADULTO')
    - codigo_atc (string o null, puedes deducirlo de tu base de conocimientos si identificas el principio activo)
    - cantidad_presentacion (int o null, cantidad de unidades en el empaque, ej. 30 pastillas = 30)
    - contenido_neto (float o null, ej. 500 para 500ml)
    - contenido_neto_unidad_Des (string o null, ej. 'ml', 'g')
    - blister (1 o 0, 1 estrictamente si la descripción contiene la palabra "blister", 0 en caso contrario)

    Si el producto claramente no es un medicamento (ej. Teteros, Mamilas, Chupones, Toallas húmedas, Guata, Aspirador nasal, Tubos de ensayo, Bolsas recolectoras, Tapabocas, Centros de cama, Inyectadoras), debes poner:
    - principio_activo: null
    - concentracion: null
    - forma_farmaceutica: null
    - clasificacion_insumo_Des: "NO_MEDICAMENTO" (o el tipo de insumo)

    Para los productos farmacéuticos válidos, extrae la información técnica estrictamente si está presente en el texto de la descripción original. NO ASUMAS, NO ADIVINES y NO INFIERAS valores que no estén explícitamente escritos. Si un dato técnico (como la concentración o el principio activo) falta, tu obligación es usar null.

    IMPORTANTE: 
    - En la llave "atributos_ya_encontrados" te informaremos qué datos ya logramos extraer en intentos pasados. 
    - Por defecto, conserva esos valores. Sin embargo, si los 'atributos_ya_encontrados' contienen información que contradice el texto original o parece inventada/alucinada por un modelo anterior, TIENES AUTORIZACIÓN PARA SOBREESCRIBIRLA Y CORREGIRLA.
    - Para los datos faltantes (nulos), enfócate en extraerlos literalmente. No infieras datos que no puedas sustentar con la descripción original.
    - Devuelve ÚNICAMENTE un array JSON válido con este formato, sin markdown, sin texto adicional:
    [
      {{
        "registro": {{"codigo": "...", "codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0}},
        "atributos_ya_encontrados": {{}},
        "atributos_nuevos_consolidados": {{"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR:
    {batch_json_str}
    """
    
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tokens = usage.get('prompt_tokens', 0)
                c_tokens = usage.get('completion_tokens', 0)
                model_lower = model.lower()
                if "gemini-2.5-flash" in model_lower:
                    costo = (p_tokens * 0.075 + c_tokens * 0.30) / 1000000.0
                elif "gemini-2.5-pro" in model_lower:
                    costo = (p_tokens * 1.25 + c_tokens * 5.00) / 1000000.0
                elif "deepseek-v4-flash" in model_lower:
                    costo = (p_tokens * 0.09 + c_tokens * 0.18) / 1000000.0
                elif "deepseek-v4-pro" in model_lower:
                    costo = (p_tokens * 0.44 + c_tokens * 0.87) / 1000000.0
                elif "deepseek-r1" in model_lower:
                    costo = (p_tokens * 0.55 + c_tokens * 2.19) / 1000000.0
                elif "minimax-m3" in model_lower:
                    costo = (p_tokens * 0.30 + c_tokens * 1.20) / 1000000.0
                elif "mixtral-8x22b" in model_lower:
                    costo = (p_tokens * 0.90 + c_tokens * 0.90) / 1000000.0
                elif "qwen-2.5-72b" in model_lower:
                    costo = (p_tokens * 0.36 + c_tokens * 0.40) / 1000000.0
                elif "llama-3.3-70b" in model_lower:
                    costo = (p_tokens * 0.35 + c_tokens * 0.40) / 1000000.0
                else:
                    costo = (p_tokens * 1.25 + c_tokens * 10.00) / 1000000.0
                
                with gasto_lock:
                    gasto_por_ciclo[ciclo_actual] += costo
                print(f"    [IA] {model} | Tokens: In={p_tokens}, Out={c_tokens} | Costo: ${costo:.5f}")
                
                if 'choices' not in result or not result['choices']:
                    print(f"    ERROR: Respuesta inesperada de OpenRouter (sin choices): {json.dumps(result, indent=2)}")
                    return None
                    
                message = result['choices'][0].get('message', {})
                content = message.get('content')
                if content is None:
                    print(f"    ERROR: El content de la respuesta es None. Mensaje completo: {json.dumps(message, indent=2)}")
                    return None
                    
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            print(f"    [Intento {attempt+1}/{max_retries}] Error llamando a OpenRouter ({model}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
    return None

def calcular_score_calidad(atrib):
    score = 0
    es_medicamento = not bool(atrib.get('clasificacion_insumo_Des'))
    
    # SINE QUA NON: Condición indispensable para medicamentos
    if es_medicamento:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0
            
    # TABLA DE PUNTOS NORMALIZADA A 100 PUNTOS EXACTOS
    if atrib.get('cantidad_presentacion') is not None: score += 26
    if atrib.get('origen'): score += 19
    if atrib.get('segmento_etario'): score += 13
    if atrib.get('fabricante'): score += 10
    if atrib.get('codigo_atc'): score += 10
    if atrib.get('marca'): score += 7
    
    # Lógica de Volumen vs Forma Farmacéutica (Mutuamente excluyentes para el score)
    ff = str(atrib.get('forma_farmaceutica')).upper()
    solidos = ['TABLETA', 'PASTILLA', 'CAPSULA', 'GRAGEA', 'POLVO', 'SOBRE', 'PIZARRA', 'SUPOSITORIO', 'OVULO', 'COMPRIMIDO', 'GRANULADO']
    viales_inyectables = ['INYECTABLE', 'AMPOLLA', 'VIAL']
    
    if any(s in ff for s in solidos):
        # Los sólidos no necesitan declarar volumen líquido, ganan los puntos de contenido por defecto
        score += 15
    elif atrib.get('contenido_neto') is not None or any(v in ff for v in viales_inyectables):
        # Los líquidos o inyectables sí requieren declarar el contenido neto para ganar estos puntos
        score += 15
        
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val:
        return "NO_DEFINIDO"
    val_upper = str(val).upper().strip()
    val_upper = val_upper.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    if "ADULTO" in val_upper:
        return "ADULTO"
    if "PEDIATRICO" in val_upper or "INFANTIL" in val_upper or "NIÑO" in val_upper or "HIJO" in val_upper or "KID" in val_upper:
        return "PEDIATRICO"
    if "NEONATAL" in val_upper or "NEONATO" in val_upper or "BEBE" in val_upper:
        return "NEONATAL"
    if "MIXTO" in val_upper:
        return "MIXTO"
    if "GENERAL" in val_upper or "TODO" in val_upper or "TODOS" in val_upper or "PUBLICO" in val_upper:
        return "GENERAL"
    if val_upper in ["ADULTO", "PEDIATRICO", "NEONATAL", "MIXTO", "GENERAL", "NO_DEFINIDO"]:
        return val_upper
    return "NO_DEFINIDO"

def generar_y_ejecutar_sql(resultados_ia, catalog):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    count = 0
    
    for item in resultados_ia:
        codbarras = item.get('registro', {}).get('codbarras')
        ciclos_reproceso = item.get('registro', {}).get('ciclos_reproceso', 0)
        ya_enc = item.get('atributos_ya_encontrados', {})
        atrib = item.get('atributos_nuevos_consolidados', item.get('atributos', {}))
        
        # COALESCE
        for k in ya_enc:
            v_nuevo = atrib.get(k)
            if v_nuevo is None or str(v_nuevo).strip() == '':
                atrib[k] = ya_enc[k]
        
        if not codbarras: continue
        
        # Procesamiento y limpieza con Expresiones Regulares
        res_limpieza = procesar_farmacos(atrib.get('principio_activo'), atrib.get('concentracion'))
        
        observaciones = ""
        if res_limpieza["exito"]:
            atrib['principio_activo'] = res_limpieza["principio_activo"]
            atrib['concentracion'] = res_limpieza["concentracion"]
            if res_limpieza["observaciones"]:
                observaciones = res_limpieza["observaciones"]
        else:
            # FALLO POR MISMATCH: Dejamos PA y Conc nulos para forzar reintento, guardamos raw en observaciones
            atrib['principio_activo'] = None
            atrib['concentracion'] = None
            observaciones = res_limpieza["observaciones"]
            
        # Normalizar segmento etario
        atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
        
        # Normalizar Forma Farmaceutica (Plural a Singular)
        if atrib.get('forma_farmaceutica'):
            ff_upper = str(atrib.get('forma_farmaceutica')).upper().strip()
            reemplazos_ff = {
                'SOBRES': 'SOBRE', 'GOMITAS': 'GOMITA', 'TABLETAS': 'TABLETA',
                'ÓVULOS': 'ÓVULO', 'SUPOSITORIOS': 'SUPOSITORIO', 'CÁPSULAS': 'CÁPSULA',
                'COMPRIMIDOS': 'COMPRIMIDO', 'GRAGEAS': 'GRAGEA', 'APÓSITOS': 'APÓSITO',
                'PASTILLAS': 'PASTILLA', 'GASAS': 'GASA', 'CAPSULAS': 'CAPSULA',
                'GALLETAS': 'GALLETA', 'SACHETS': 'SACHET', 'CARAMELOS': 'CARAMELO'
            }
            if ff_upper in reemplazos_ff:
                atrib['forma_farmaceutica'] = reemplazos_ff[ff_upper]
        
        def fmt(val, is_string=True):
            if val is None or val == 'None' or str(val).strip() == '': return "NULL"
            val_str = str(val).strip()
            if val_str.lower() == 'true': return "1"
            if val_str.lower() == 'false': return "0"
            if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
            return val_str

        score_calidad = calcular_score_calidad(atrib)
        
        # Evaluar Estado
        es_med = not bool(atrib.get('clasificacion_insumo_Des'))
        if score_calidad >= 88 or (not es_med and score_calidad >= 70):
            estado_ciclo = 'CERRADO'
        else:
            if ciclos_reproceso >= 3: # MAX_REINTENTOS = 3 para 4 ciclos totales (0 a 3)
                estado_ciclo = 'AGOTADO'
            else:
                estado_ciclo = 'ABIERTO'
                ciclos_reproceso += 1

        set_clauses = [
            f"principio_activo_Des = {fmt(atrib.get('principio_activo'))}",
            f"concentracion_Des = {fmt(atrib.get('concentracion'))}",
            f"forma_farmaceutica_Des = {fmt(atrib.get('forma_farmaceutica'))}",
            f"fabricante_Des = {fmt(atrib.get('fabricante'))}",
            f"marca_Des = {fmt(atrib.get('marca'))}",
            f"codigo_atc_Des = {fmt(atrib.get('codigo_atc'))}",
            f"clasificacion_insumo_Des = {fmt(atrib.get('clasificacion_insumo_Des'))}",
            f"blister = {fmt(atrib.get('blister'), False)}",
            f"cantidad_presentacion = {fmt(atrib.get('cantidad_presentacion'), False)}",
            f"contenido_neto = {fmt(atrib.get('contenido_neto'), False)}",
            f"contenido_neto_unidad_Des = {fmt(atrib.get('contenido_neto_unidad_Des'))}",
            f"segmento_etario = {fmt(atrib.get('segmento_etario'))}",
            f"origen_Des = {fmt(atrib.get('origen'))}",
            f"score_calidad = {score_calidad}",
            f"estado_ciclo = '{estado_ciclo}'",
            f"ciclos_reproceso = {ciclos_reproceso}",
            f"observaciones_ia = {fmt(observaciones)}",
            "origen_dato = 'IA_INVESTIGATED_V10_AUTO'"
        ]
        
        # Mapeo de IDs usando catálogo
        if catalog:
            id_pa = catalog.find_id("principio_activo", atrib.get('principio_activo'))
            id_con = catalog.find_id("concentracion", atrib.get('concentracion'))
            id_ff = catalog.find_id("forma_farmaceutica", atrib.get('forma_farmaceutica'))
            id_fab = catalog.find_id("fabricante", atrib.get('fabricante'))
            id_marca = catalog.find_id("marca", atrib.get('marca'))
            id_atc = catalog.find_id("codigo_atc", atrib.get('codigo_atc'))
            id_clasif = catalog.find_id("clasificacion_insumo", atrib.get('clasificacion_insumo_Des'))
            id_origen = catalog.find_id("origen", atrib.get('origen'))
            id_unidad = catalog.find_id("contenido_neto_unidad", atrib.get('contenido_neto_unidad_Des'))
            
            set_clauses.extend([
                f"principio_activo = {fmt(id_pa, False)}",
                f"concentracion = {fmt(id_con, False)}",
                f"forma_farmaceutica = {fmt(id_ff, False)}",
                f"fabricante = {fmt(id_fab, False)}",
                f"marca = {fmt(id_marca, False)}",
                f"codigo_atc = {fmt(id_atc, False)}",
                f"clasificacion_insumo = {fmt(id_clasif, False)}",
                f"origen = {fmt(id_origen, False)}",
                f"contenido_neto_unidad = {fmt(id_unidad, False)}"
            ])
        
        if atrib.get('origen') == 'NO_MEDICAMENTO' or not atrib.get('principio_activo'):
             set_clauses.append("es_medicamento = 0")
        else:
             set_clauses.append("es_medicamento = 1")
             
        update_query = f"UPDATE Procurement.por_aprobacion_equivalencias SET {', '.join(set_clauses)} WHERE codbarras = '{codbarras}';"
        try:
            cursor.execute(update_query)
            count += 1
        except Exception as e:
            print(f"Error actualizando {codbarras}: {e}")
            
    conn.commit()
    conn.close()
    return count

def obtener_lote_especifico(codbarras_list, ciclo_esperado):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    
    # Formatear la lista de codbarras para la consulta
    codbarras_placeholders = ",".join([f"'{c}'" for c in codbarras_list])
    
    query = f"""
    SELECT codbarras, descrip1art, ISNULL(ciclos_reproceso, 0) as ciclos_reproceso,
        principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, fabricante_Des, marca_Des,
        codigo_atc_Des, clasificacion_insumo_Des, requiere_recipe, blister, generico, 
        cantidad_presentacion, contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des, estado_ciclo
    FROM Procurement.por_aprobacion_equivalencias 
    WHERE codbarras IN ({codbarras_placeholders})
    AND ISNULL(ciclos_reproceso, 0) = {ciclo_esperado}
    AND (estado_ciclo IS NULL OR estado_ciclo = 'ABIERTO')
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    lote = []
    for r in rows:
        ya_encontrados = {}
        keys = ['principio_activo', 'concentracion', 'forma_farmaceutica', 'fabricante', 'marca',
                'codigo_atc', 'clasificacion_insumo_Des', 'requiere_recipe', 'blister', 'generico',
                'cantidad_presentacion', 'contenido_neto', 'contenido_neto_unidad_Des', 'segmento_etario', 'origen']
        
        for idx, k in enumerate(keys):
            val = r[3+idx]
            if val is not None and str(val).strip() != '':
                ya_encontrados[k] = val
                
        lote.append({
            "registro": {"codigo": r[0], "codbarras": r[0], "descripcion_original": r[1], "ciclos_reproceso": r[2]},
            "atributos_ya_encontrados": ya_encontrados
        })
        
    conn.close()
    return lote

def main():
    print("=== INICIANDO EXPERIMENTO DE 15 PRODUCTOS NUEVOS (4 CICLOS COMPLETOS) ===")
    
    # 1. Obtener 15 productos limpios de la base de datos que estén en Ciclo 0
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT TOP 15 codbarras 
    FROM Procurement.por_aprobacion_equivalencias 
    WHERE (estado_ciclo IS NULL OR estado_ciclo = 'ABIERTO')
    AND ISNULL(ciclos_reproceso, 0) = 0
    AND (origen_dato IS NULL OR origen_dato NOT LIKE 'IA_INVESTIGATED_V10_AUTO')
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 15:
        print(f"Error: Solo se encontraron {len(rows)} productos en ciclo 0. Se requieren 15.")
        return
        
    test_codbarras = [r[0] for r in rows]
    print(f"Se seleccionaron 15 productos de prueba nuevos. Iniciando el flujo...")
    
    catalog = MasterCatalog(CONN_STR)
    chunk_size = 25
    
    resumen_ciclos = {}
    placeholders = ",".join([f"'{c}'" for c in test_codbarras])
    resultados_totales = []
    
    # --- CICLO 0 (Intento 1 - Qwen 2.5 72B Instruct) ---
    print("\n--- EJECUTANDO CICLO 0 (Intento 1 con Qwen 2.5 72B Instruct) ---")
    lote_c0 = obtener_lote_especifico(test_codbarras, ciclo_esperado=0)
    print(f"Total registros a procesar en Ciclo 0: {len(lote_c0)}")
    
    resultados_c0 = []
    for i in range(0, len(lote_c0), chunk_size):
        chunk = lote_c0[i:i+chunk_size]
        print(f"  Procesando chunk {i//chunk_size + 1} ({len(chunk)} items)...")
        res = llamar_openrouter(json.dumps(chunk, indent=2), model="qwen/qwen-2.5-72b-instruct", ciclo_actual=0)
        if res: resultados_c0.extend(res)
        time.sleep(2)
        
    if resultados_c0:
        resultados_totales.extend(resultados_c0)
        with open('debug_resultados_15.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_totales, f, indent=2)
        generar_y_ejecutar_sql(resultados_c0, catalog)
    
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c0 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c0 = stats_c0.get('CERRADO', 0)
    abiertos_c0 = stats_c0.get('ABIERTO', 0)
    print(f"Resultados Ciclo 0: Cerrados: {cerrados_c0} | Abiertos: {abiertos_c0}")
    resumen_ciclos[0] = {"modelo": "Qwen 2.5 72B Instruct", "costo": gasto_por_ciclo[0], "cerrados": cerrados_c0, "abiertos": abiertos_c0}
    
    # --- CICLO 1 (Intento 2 - MiniMax M3) ---
    print("\n--- EJECUTANDO CICLO 1 (Intento 2 con MiniMax M3) ---")
    lote_c1 = obtener_lote_especifico(test_codbarras, ciclo_esperado=1)
    print(f"Total registros a procesar en Ciclo 1 (siguen abiertos): {len(lote_c1)}")
    
    if len(lote_c1) > 0:
        resultados_c1 = []
        for i in range(0, len(lote_c1), chunk_size):
            chunk = lote_c1[i:i+chunk_size]
            print(f"  Procesando chunk {i//chunk_size + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), model="minimax/minimax-m3", ciclo_actual=1)
            if res: resultados_c1.extend(res)
            time.sleep(2)
            
        if resultados_c1:
            resultados_totales.extend(resultados_c1)
            with open('debug_resultados_15.json', 'w', encoding='utf-8') as f:
                json.dump(resultados_totales, f, indent=2)
            generar_y_ejecutar_sql(resultados_c1, catalog)
            
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c1 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c1 = stats_c1.get('CERRADO', 0) - cerrados_c0
    abiertos_c1 = stats_c1.get('ABIERTO', 0)
    print(f"Resultados Ciclo 1: Nuevos Cerrados: {cerrados_c1} | Total Cerrados: {stats_c1.get('CERRADO', 0)} | Abiertos: {abiertos_c1}")
    resumen_ciclos[1] = {"modelo": "MiniMax M3", "costo": gasto_por_ciclo[1], "cerrados": cerrados_c1, "abiertos": abiertos_c1}
 
    # --- CICLO 2 (Intento 3 - Mixtral 8x22B Instruct) ---
    print("\n--- INICIANDO FASE 3: Ciclo 2 (Mixtral 8x22B Instruct) ---")
    lote_c2 = obtener_lote_especifico(test_codbarras, ciclo_esperado=2)
    print(f"Total registros a procesar en Ciclo 2 (siguen abiertos): {len(lote_c2)}")
    
    if lote_c2:
        for i in range(0, len(lote_c2), chunk_size):
            chunk = lote_c2[i:i+chunk_size]
            print(f"Fase 3 - Chunk {i//chunk_size + 1} de {(len(lote_c2)-1)//chunk_size + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), model="mistralai/mixtral-8x22b-instruct", ciclo_actual=2)
            if res:
                resultados_totales.extend(res)
                with open('debug_resultados_15.json', 'w', encoding='utf-8') as f:
                    json.dump(resultados_totales, f, indent=2)
                generar_y_ejecutar_sql(res, catalog)
            time.sleep(2)
    else:
        print("No hay registros en Ciclo 2 para la Fase 3.")
            
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c2 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c2 = stats_c2.get('CERRADO', 0) - stats_c1.get('CERRADO', 0)
    abiertos_c2 = stats_c2.get('ABIERTO', 0)
    print(f"Resultados Ciclo 2: Nuevos Cerrados: {cerrados_c2} | Total Cerrados: {stats_c2.get('CERRADO', 0)} | Abiertos: {abiertos_c2}")
    resumen_ciclos[2] = {"modelo": "Mixtral 8x22B Instruct", "costo": gasto_por_ciclo[2], "cerrados": cerrados_c2, "abiertos": abiertos_c2}
 
    # --- CICLO 3 (Intento 4 - Gemini 2.5 Pro) ---
    print("\n--- EJECUTANDO CICLO 3 (Intento 4 con Gemini 2.5 Pro - Ciclo Final) ---")
    lote_c3 = obtener_lote_especifico(test_codbarras, ciclo_esperado=3)
    print(f"Total registros a procesar en Ciclo 3 (siguen abiertos): {len(lote_c3)}")
    
    if len(lote_c3) > 0:
        chunk_size_gemini = 15
        chunks = [lote_c3[i:i+chunk_size_gemini] for i in range(0, len(lote_c3), chunk_size_gemini)]
        
        for idx, chunk in enumerate(chunks):
            print(f"  Procesando chunk {idx + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), model="google/gemini-2.5-pro", ciclo_actual=3)
            if res:
                resultados_totales.extend(res)
                with open('debug_resultados_15.json', 'w', encoding='utf-8') as f:
                    json.dump(resultados_totales, f, indent=2)
                db_updated = generar_y_ejecutar_sql(res, catalog)
                print(f"    Chunk {idx+1} finalizado. {db_updated} registros actualizados en BD.")
            time.sleep(5)
            
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c3 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c3 = stats_c3.get('CERRADO', 0) - stats_c2.get('CERRADO', 0)
    agotados_c3 = stats_c3.get('AGOTADO', 0)
    print(f"Resultados Ciclo 3: Nuevos Cerrados: {cerrados_c3} | Total Cerrados: {stats_c3.get('CERRADO', 0)} | Agotados: {agotados_c3}")
    resumen_ciclos[3] = {"modelo": "Gemini 2.5 Pro", "costo": gasto_por_ciclo[3], "cerrados": cerrados_c3, "agotados": agotados_c3}

    # --- TABLA RESUMEN FINAL ---
    print("\n" + "="*70)
    print("         RESUMEN FINAL DEL EXPERIMENTO (4 CICLOS COMPLETOS)")
    print("="*70)
    print(f"{'Ciclo':<8}{'Modelo Usado':<25}{'Costo':<12}{'Resueltos':<12}{'Estado Restante':<15}")
    print("-"*70)
    
    total_gasto = 0.0
    total_resueltos = 0
    
    for c in range(4):
        rc = resumen_ciclos.get(c, {"modelo": "-", "costo": 0.0, "cerrados": 0})
        total_gasto += rc["costo"]
        total_resueltos += rc["cerrados"]
        
        restante_str = ""
        if c < 3:
            restante_str = f"{rc.get('abiertos', 0)} Abiertos"
        else:
            restante_str = f"{rc.get('agotados', 0)} Agotados"
            
        print(f"Ciclo {c:<3} {rc['modelo']:<25} ${rc['costo']:.5f} {rc['cerrados']:<12} {restante_str:<15}")
        
    print("-"*70)
    print(f"{'TOTAL':<8} {'':<25} ${total_gasto:.4f} {total_resueltos:<12} (Eficacia del {total_resueltos}%)")
    print("="*70)

if __name__ == "__main__":
    main()
