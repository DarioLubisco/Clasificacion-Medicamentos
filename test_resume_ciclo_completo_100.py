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
socket.setdefaulttimeout(180) # 3 minutes read timeout
from MDM_Unified_Mapper import MasterCatalog
from limpiador_farmaceutico_regex import procesar_farmacos

gasto_lock = threading.Lock()

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialized with costs and results from previous runs
gasto_por_ciclo = {
    0: 0.00825,
    1: 0.00986,
    2: 0.05941,
    3: 0.06105,
    4: 0.24327,
    5: 0.0
}

resumen_ciclos = {
    0: {"modelo": "DeepSeek V4-Flash", "costo": 0.00825, "cerrados": 16, "abiertos": 84},
    1: {"modelo": "DeepSeek V4-Flash", "costo": 0.00986, "cerrados": 0, "abiertos": 84},
    2: {"modelo": "DeepSeek V4-Pro", "costo": 0.05941, "cerrados": 3, "abiertos": 81},
    3: {"modelo": "MiniMax M3", "costo": 0.06105, "cerrados": 18, "abiertos": 63}
}

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
    - marca (string o null)
    - codigo_atc (string o null)
    - cantidad_presentacion (int o null, cantidad de unidades en el empaque, ej. 30 pastillas = 30)
    - contenido_neto (float o null, ej. 500 para 500ml)
    - contenido_neto_unidad_Des (string o null, ej. 'ml', 'g')
    - blister (1 o 0, si viene en blister)
    - generico (1 o 0, si es genérico)

    Si el producto claramente no es un medicamento (ej. Teteros, Mamilas, Chupones, Toallas húmedas, Guata, Aspirador nasal, Tubos de ensayo, Bolsas recolectoras, Tapabocas, Centros de cama, Inyectadoras), debes poner:
    - principio_activo: null
    - concentracion: null
    - forma_farmaceutica: null
    - requiere_recipe: 0
    - origen: "NO_MEDICAMENTO" (o el tipo de insumo)

    Si es medicamento, extrae el principio activo y concentración de la descripción.

    IMPORTANTE: 
    - En la llave "atributos_ya_encontrados" te informaremos qué datos ya logramos extraer en intentos pasados. 
    - Debes CONSERVAR esos valores exactamente iguales en tu respuesta y enfocarte ÚNICAMENTE en intentar inferir o completar las llaves que aún están en nulo (elementos faltantes).
    - Devuelve ÚNICAMENTE un array JSON válido con este formato, sin markdown, sin texto adicional:
    [
      {{
        "registro": {{"codigo": "...", "codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0}},
        "atributos_ya_encontrados": {{}},
        "atributos_nuevos_consolidados": {{"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": "ADULTO", "origen": "IA", "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR:
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
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tokens = usage.get('prompt_tokens', 0)
                c_tokens = usage.get('completion_tokens', 0)
                
                model_lower = model.lower()
                if "deepseek-v4-flash" in model_lower:
                    costo = (p_tokens * 0.09 + c_tokens * 0.18) / 1000000.0
                elif "deepseek-v4-pro" in model_lower:
                    costo = (p_tokens * 0.44 + c_tokens * 0.87) / 1000000.0
                elif "deepseek-r1" in model_lower:
                    costo = (p_tokens * 0.55 + c_tokens * 2.19) / 1000000.0
                elif "minimax-m3" in model_lower:
                    costo = (p_tokens * 0.30 + c_tokens * 1.20) / 1000000.0
                elif "flash" in model_lower:
                    costo = (p_tokens * 0.30 + c_tokens * 2.50) / 1000000.0
                elif "glm-5.2" in model_lower:
                    costo = (p_tokens * 1.30 + c_tokens * 4.20) / 1000000.0
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
    es_medicamento = atrib.get('origen') != 'NO_MEDICAMENTO' and atrib.get('principio_activo') is not None
    
    if es_medicamento:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0
            
    if es_medicamento: score += 5
    if atrib.get('clasificacion_insumo_Des'): score += 3
    if atrib.get('marca'): score += 3
    if atrib.get('cantidad_presentacion') is not None: score += 26
    
    ff = str(atrib.get('forma_farmaceutica')).upper()
    solidos = ['TABLETA', 'PASTILLA', 'CAPSULA', 'GRAGEA', 'POLVO', 'SOBRE', 'PIZARRA', 'SUPOSITORIO', 'OVULO']
    if any(s in ff for s in solidos):
        score += 13
    elif atrib.get('contenido_neto') is not None:
        score += 13
        
    if atrib.get('fabricante'): score += 6
    if atrib.get('origen'): score += 19
    if atrib.get('generico') in [1, 0, True, False]: score += 6
    if atrib.get('codigo_atc'): score += 6
    if atrib.get('segmento_etario'): score += 13
    
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
        
        def fmt(val, is_string=True):
            if val is None or val == 'None' or str(val).strip() == '': return "NULL"
            val_str = str(val).strip()
            if val_str.lower() == 'true': return "1"
            if val_str.lower() == 'false': return "0"
            if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
            return val_str

        score_calidad = calcular_score_calidad(atrib)
        
        # Evaluar Estado
        if score_calidad >= 88:
            estado_ciclo = 'CERRADO'
        else:
            if ciclos_reproceso >= 5: # MAX_REINTENTOS = 5 para 6 ciclos totales (0 a 5)
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
            f"requiere_recipe = {fmt(atrib.get('requiere_recipe'), False)}",
            f"blister = {fmt(atrib.get('blister'), False)}",
            f"generico = {fmt(atrib.get('generico'), False)}",
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
    print("=== REANUDANDO EXPERIMENTO DE 100 PRODUCTOS (CICLOS 4 y 5 RESTANTES) ===")
    
    # 1. Recuperar los 100 productos bajo prueba usando la marca origen_dato
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT codbarras FROM Procurement.por_aprobacion_equivalencias 
    WHERE origen_dato = 'IA_INVESTIGATED_V10_AUTO'
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) != 100:
        print(f"Error: Se encontraron {len(rows)} productos en lugar de los 100 del lote original.")
        return
        
    test_codbarras = [r[0] for r in rows]
    print(f"Lote original de 100 productos recuperado exitosamente.")
    
    catalog = MasterCatalog(CONN_STR)
    placeholders = ",".join([f"'{c}'" for c in test_codbarras])
    
    # --- CICLO 4 (Intento 5 - DeepSeek R1) ---
    print("\n--- EJECUTANDO CICLO 4 (Intento 5 con DeepSeek R1) ---")
    lote_c4 = obtener_lote_especifico(test_codbarras, ciclo_esperado=4)
    print(f"Total registros a procesar en Ciclo 4 (siguen abiertos): {len(lote_c4)}")
    
    if len(lote_c4) > 0:
        resultados_c4 = []
        chunk_size_r1 = 5 # Optimización: chunk size de 5 para DeepSeek R1
        for i in range(0, len(lote_c4), chunk_size_r1):
            chunk = lote_c4[i:i+chunk_size_r1]
            print(f"  Procesando chunk {i//chunk_size_r1 + 1} de {(len(lote_c4)-1)//chunk_size_r1 + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), model="deepseek/deepseek-r1", ciclo_actual=4)
            if res: resultados_c4.extend(res)
            time.sleep(2)
            
        if resultados_c4:
            generar_y_ejecutar_sql(resultados_c4, catalog)
            
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c4 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c4 = stats_c4.get('CERRADO', 0) - resumen_ciclos[3]["cerrados"] - resumen_ciclos[2]["cerrados"] - resumen_ciclos[1]["cerrados"] - resumen_ciclos[0]["cerrados"]
    abiertos_c4 = stats_c4.get('ABIERTO', 0)
    print(f"Resultados Ciclo 4: Nuevos Cerrados: {cerrados_c4} | Total Cerrados: {stats_c4.get('CERRADO', 0)} | Abiertos: {abiertos_c4}")
    resumen_ciclos[4] = {"modelo": "DeepSeek R1", "costo": gasto_por_ciclo[4], "cerrados": cerrados_c4, "abiertos": abiertos_c4}

    # --- CICLO 5 (Intento 6 - DeepSeek R1) ---
    print("\n--- EJECUTANDO CICLO 5 (Intento 6 con DeepSeek R1) ---")
    lote_c5 = obtener_lote_especifico(test_codbarras, ciclo_esperado=5)
    print(f"Total registros a procesar en Ciclo 5 (siguen abiertos): {len(lote_c5)}")
    
    if len(lote_c5) > 0:
        chunk_size_r1 = 5
        chunks = [lote_c5[i:i+chunk_size_r1] for i in range(0, len(lote_c5), chunk_size_r1)]
        print(f"  Procesando {len(chunks)} chunks en paralelo con ThreadPoolExecutor (max_workers=5)...")
        
        def procesar_un_chunk(idx, chunk):
            print(f"    [Thread] Iniciando chunk {idx+1}/{len(chunks)} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), model="deepseek/deepseek-r1", ciclo_actual=5)
            if res:
                db_updated = generar_y_ejecutar_sql(res, catalog)
                print(f"    [Thread] Chunk {idx+1} finalizado. {db_updated} registros actualizados en BD.")
            else:
                print(f"    [Thread] Chunk {idx+1} falló o no retornó resultados.")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(procesar_un_chunk, idx, chunk) for idx, chunk in enumerate(chunks)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error procesando chunk en thread: {e}")
            
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE codbarras IN ({placeholders}) GROUP BY estado_ciclo")
    stats_c5 = {r[0]: r[1] for r in cursor.fetchall()}
    conn.close()
    
    cerrados_c5 = stats_c5.get('CERRADO', 0) - stats_c4.get('CERRADO', 0)
    agotados_c5 = stats_c5.get('AGOTADO', 0)
    print(f"Resultados Ciclo 5: Nuevos Cerrados: {cerrados_c5} | Total Cerrados: {stats_c5.get('CERRADO', 0)} | Agotados: {agotados_c5}")
    resumen_ciclos[5] = {"modelo": "DeepSeek R1", "costo": gasto_por_ciclo[5], "cerrados": cerrados_c5, "agotados": agotados_c5}

    # --- TABLA RESUMEN FINAL ---
    print("\n" + "="*70)
    print("         RESUMEN FINAL DEL EXPERIMENTO (6 CICLOS COMPLETOS)")
    print("="*70)
    print(f"{'Ciclo':<8}{'Modelo Usado':<16}{'Costo':<12}{'Resueltos':<12}{'Estado Restante':<15}")
    print("-"*70)
    
    total_gasto = 0.0
    total_resueltos = 0
    
    for c in range(6):
        rc = resumen_ciclos[c]
        total_gasto += rc["costo"]
        total_resueltos += rc["cerrados"]
        
        restante_str = ""
        if c < 5:
            restante_str = f"{rc.get('abiertos', 0)} Abiertos"
        else:
            restante_str = f"{rc.get('agotados', 0)} Agotados"
            
        print(f"Ciclo {c:<3} {rc['modelo']:<16} ${rc['costo']:.5f} {rc['cerrados']:<12} {restante_str:<15}")
        
    print("-"*70)
    print(f"{'TOTAL':<8} {'':<16} ${total_gasto:.4f} {total_resueltos:<12} (Eficacia del {total_resueltos}%)")
    print("="*70)

if __name__ == "__main__":
    main()
