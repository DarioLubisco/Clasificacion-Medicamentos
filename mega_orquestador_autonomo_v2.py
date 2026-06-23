import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import os
import re
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
socket.setdefaulttimeout(180)
from datetime import datetime
from MDM_Unified_Mapper import MasterCatalog
from limpiador_farmaceutico_regex import procesar_farmacos

gasto_lock = threading.Lock()

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GASTO_ACUMULADO_USD = 0.0
MAX_BUDGET_USD = 2.00

def obtener_taxonomias_existentes():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        taxonomias = []
        for r in cursor.fetchall():
            d = r[0]
            c = r[1] if r[1] else "SINEVAL"
            s = r[2] if r[2] else "SINEVAL"
            taxonomias.append(f"- Dominio: {d} | Categoria: {c} | Subcategoria: {s}")
        conn.close()
        if not taxonomias:
            return "No hay taxonomías existentes registradas."
        return "\n".join(taxonomias)
    except Exception as e:
        print(f"Error obteniendo taxonomias: {e}")
        return "No hay taxonomías existentes registradas."

def obtener_lote(limite=100, fase=1):
    print(f"Obteniendo {limite} registros pendientes para Fase {fase}...")
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    query = f"""
    SELECT TOP {limite} codbarras, descrip1art, ISNULL(ciclos_reproceso, 0) as ciclos_reproceso,
        principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, fabricante_Des, marca_Des,
        codigo_atc_Des, clasificacion_insumo_Des, requiere_recipe, blister, generico, 
        cantidad_presentacion, contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
    FROM Procurement.por_aprobacion_equivalencias 
    WHERE (estado_ciclo IS NULL OR estado_ciclo = 'ABIERTO')
    AND (origen_dato IS NULL OR origen_dato NOT LIKE 'IA_INVESTIGATED_V10_AUTO')
    """
    if fase == 1:
        query += " AND ISNULL(ciclos_reproceso, 0) = 0"
    elif fase == 2:
        query += " AND ISNULL(ciclos_reproceso, 0) = 1"
    elif fase == 3:
        query += " AND ISNULL(ciclos_reproceso, 0) = 2"
    elif fase == 4:
        query += " AND ISNULL(ciclos_reproceso, 0) = 3"
        
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
            "registro": {"codbarras": r[0], "descripcion_original": r[1], "ciclos_reproceso": r[2]},
            "atributos_ya_encontrados": ya_encontrados
        })
        
    conn.close()
    return lote

def llamar_openrouter(batch_json_str, taxonomias_existentes, model="qwen/qwen-2.5-72b-instruct"):
    global GASTO_ACUMULADO_USD
    if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD:
        print(f"ALERTA: Se alcanzó el límite de presupuesto de ${MAX_BUDGET_USD} USD. Abortando llamada a la IA.")
        return None
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Para cada producto, extrae los siguientes atributos basándote en la descripción:
    - dominio (string OBLIGATORIO: clasifica el producto en uno de estos dominios: "MEDICAMENTO_ALOPATICO", "PRODUCTO_NATURAL_HOMEOPATICO", "SUPLEMENTO_VITAMINICO", "COSMETICO_CUIDADO_PERSONAL", "MATERIAL_MEDICO_INSUMO", "MISCELANEO")
    - categoria (string o null, ej. "ANALGESICOS", "CUIDADO CAPILAR", "ALIMENTOS", "EQUIPOS MEDICOS")
    - subcategoria (string o null, ej. "ACETAMINOFEN", "CHAMPU", "SNACKS", "JERINGAS")
    - principio_activo (string o null si no aplica/es insumo)
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

    Para los productos donde no aplican datos médicos (ej. dominio MATERIAL_MEDICO_INSUMO, COSMETICO_CUIDADO_PERSONAL, MISCELANEO), debes poner en null: principio_activo, concentracion, forma_farmaceutica, requiere_recipe.
    
    Para los dominios médicos (ALOPATICO, NATURAL, SUPLEMENTO), extrae la información técnica estrictamente si está presente. NO ASUMAS, NO ADIVINES. Si un dato técnico falta, tu obligación es usar null. Para PRODUCTO_NATURAL_HOMEOPATICO, usa el nombre de la planta/compuesto natural como principio activo.
    NOTA: Si hay múltiples ingredientes, extráelos todos separados por un guion o coma. NO intentes ordenarlos alfabéticamente ni darles un formato estricto.

    IMPORTANTE SOBRE TAXONOMIA: 
    Aquí tienes las taxonomías (Dominio, Categoría, Subcategoría) que ya existen en nuestra base de datos:
    {taxonomias_existentes}
    
    Si el producto encaja perfectamente en una de estas combinaciones, USA esos mismos nombres exactamente (respetando mayúsculas/minúsculas de la lista).
    Si ninguna encaja, tienes permiso de CREAR una nueva Categoría o Subcategoría que tenga sentido, sea general y reutilizable. NUNCA crees categorías súper específicas como "CUIDADO CAPILAR DE MUJER MARCA X".

    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web.
    4 - ALTA: Se deduce lógicamente con total certeza científica, aunque haya diferencias menores en campos no críticos.
    3 - MEDIA: Información suficiente pero con discrepancias entre sitios o ambigüedad leve.
    2 - BAJA: Inferencias o aproximaciones por información escasa o contradictoria.
    1 - NULA: Falta de información crítica. Obligado a usar null en la mayoría de campos.

    IMPORTANTE SOBRE ATRIBUTOS PREVIOS: 
    - En la llave "atributos_ya_encontrados" te informaremos qué datos ya logramos extraer en intentos pasados. 
    - Por defecto, conserva esos valores. Sin embargo, si los 'atributos_ya_encontrados' contienen información que contradice el texto original o parece inventada, TIENES AUTORIZACIÓN PARA SOBREESCRIBIRLA Y CORREGIRLA.
    - Devuelve ÚNICAMENTE un array JSON válido con este formato, sin markdown, sin texto adicional:
    [
      {{
        "registro": {{"codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0}},
        "atributos_ya_encontrados": {{}},
        "atributos_nuevos_consolidados": {{"confianza_nivel": 5, "confianza_razonamiento": "...", "dominio": "...", "categoria": "...", "subcategoria": "...", "principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": "ADULTO", "origen": "IA", "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
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
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode())
                
                # Tracking Budget
                usage = result.get('usage', {})
                p_tokens = usage.get('prompt_tokens', 0)
                c_tokens = usage.get('completion_tokens', 0)
                model_lower = model.lower()
                if "gemini-2.5-flash" in model_lower:
                    costo = (p_tokens * 0.075 + c_tokens * 0.30) / 1000000.0
                elif "gemini-2.5-pro" in model_lower:
                    costo = (p_tokens * 1.25 + c_tokens * 5.00) / 1000000.0
                elif "deepseek-r1" in model_lower:
                    costo = (p_tokens * 0.55 + c_tokens * 2.19) / 1000000.0
                elif "minimax-m3" in model_lower:
                    costo = (p_tokens * 0.30 + c_tokens * 1.20) / 1000000.0
                elif "qwen-2.5-72b" in model_lower:
                    costo = (p_tokens * 0.36 + c_tokens * 0.40) / 1000000.0
                elif "mixtral" in model_lower:
                    costo = (p_tokens * 0.90 + c_tokens * 0.90) / 1000000.0
                else:
                    costo = (p_tokens * 1.00 + c_tokens * 1.00) / 1000000.0
                
                with gasto_lock:
                    GASTO_ACUMULADO_USD += costo
                print(f"  [IA] Modelo: {model} | Tokens: In={p_tokens}, Out={c_tokens} | Costo req: ${costo:.5f} | Acumulado: ${GASTO_ACUMULADO_USD:.5f}")
                
                if 'choices' not in result or not result['choices']:
                    print(f"ERROR: Respuesta inesperada de OpenRouter (sin choices): {json.dumps(result, indent=2)}")
                    return None
                
                message = result['choices'][0].get('message', {})
                content = message.get('content')
                if content is None:
                    print(f"ERROR: El content de la respuesta es None.")
                    return None
                    
                # Clean markdown if returned
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            print(f"  [Intento {attempt+1}/{max_retries}] Error llamando a OpenRouter ({model}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
    return None

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
    es_medicamento = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    if dominio == 'MEDICAMENTO_ALOPATICO':
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
    elif dominio in ['PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']:
        if not atrib.get('principio_activo') or not atrib.get('forma_farmaceutica'):
            return 0
            
    if es_medicamento: score += 5
    if atrib.get('clasificacion_insumo_Des'): score += 3
    if atrib.get('marca'): score += 3
    
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    tiene_cont = atrib.get('contenido_neto') is not None
    
    ff = str(atrib.get('forma_farmaceutica')).upper()
    solidos = ['TABLETA', 'PASTILLA', 'CAPSULA', 'GRAGEA', 'POLVO', 'SOBRE', 'PIZARRA', 'SUPOSITORIO', 'OVULO', 'COMPRIMIDO', 'GRANULADO']
    viales_inyectables = ['INYECTABLE', 'AMPOLLA', 'VIAL']
    
    es_solido = any(s in ff for s in solidos)
    
    if es_solido:
        if tiene_cant: score += 26
        score += 13 
    else:
        if tiene_cont:
            score += 39
        else:
            if tiene_cant: score += 26
            if any(v in ff for v in viales_inyectables): score += 13
        
    if atrib.get('fabricante'): score += 6
    if atrib.get('origen'): score += 19
    if atrib.get('generico') in [1, 0, True, False]: score += 6
    if atrib.get('codigo_atc'): score += 6
    if atrib.get('segmento_etario'): score += 13
    
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val: return "NO_DEFINIDO"
    val_upper = str(val).upper().strip()
    val_upper = val_upper.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    if "ADULTO" in val_upper: return "ADULTO"
    if "PEDIATRICO" in val_upper or "INFANTIL" in val_upper or "NIÑO" in val_upper or "HIJO" in val_upper or "KID" in val_upper: return "PEDIATRICO"
    if "NEONATAL" in val_upper or "NEONATO" in val_upper or "BEBE" in val_upper: return "NEONATAL"
    if "MIXTO" in val_upper: return "MIXTO"
    if "GENERAL" in val_upper or "TODO" in val_upper or "TODOS" in val_upper or "PUBLICO" in val_upper: return "GENERAL"
    if val_upper in ["ADULTO", "PEDIATRICO", "NEONATAL", "MIXTO", "GENERAL", "NO_DEFINIDO"]: return val_upper
    return "NO_DEFINIDO"

def generar_sql_updates(resultados_ia, catalog=None):
    sql_statements = []
    MAX_REINTENTOS = 4
    
    for item in resultados_ia:
        codbarras = item.get('registro', {}).get('codbarras')
        ciclos_reproceso = item.get('registro', {}).get('ciclos_reproceso', 0)
        ya_enc = item.get('atributos_ya_encontrados', {})
        atrib = item.get('atributos_nuevos_consolidados', item.get('atributos', {}))
        
        for k in ya_enc:
            v_nuevo = atrib.get(k)
            if v_nuevo is None or str(v_nuevo).strip() == '':
                atrib[k] = ya_enc[k]
        
        atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
        
        if not codbarras: continue
        
        def fmt(val, is_string=True):
            if val is None or val == 'None' or str(val).strip() == '': return "NULL"
            val_str = str(val).strip()
            if val_str.lower() == 'true': return "1"
            if val_str.lower() == 'false': return "0"
            if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
            return val_str

        res_limpieza = procesar_farmacos(atrib.get('principio_activo'), atrib.get('concentracion'))
        
        observaciones = ""
        if res_limpieza["exito"]:
            atrib['principio_activo'] = res_limpieza["principio_activo"]
            atrib['concentracion'] = res_limpieza["concentracion"]
            if res_limpieza["observaciones"]:
                observaciones = res_limpieza["observaciones"]
        else:
            atrib['principio_activo'] = None
            atrib['concentracion'] = None
            observaciones = res_limpieza["observaciones"]
        
        dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
        if not dominio or dominio == 'None':
            dominio = 'SINEVAL'
            
        categoria = atrib.get('categoria', 'SINEVAL')
        if not categoria or categoria == 'None': categoria = 'SINEVAL'
        
        subcategoria = atrib.get('subcategoria', 'SINEVAL')
        if not subcategoria or subcategoria == 'None': subcategoria = 'SINEVAL'
            
        if observaciones:
            observaciones = f"[{dominio}] {observaciones}"
        else:
            observaciones = f"[{dominio}]"
            
        score_calidad = calcular_score_calidad(atrib)
        es_med = (dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO'])
        
        if score_calidad >= 88 or (not es_med and score_calidad >= 70):
            estado_ciclo = 'CERRADO'
        else:
            if ciclos_reproceso >= MAX_REINTENTOS:
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
        
        if not es_med or not atrib.get('principio_activo'):
             set_clauses.append("es_medicamento = 0")
        else:
             set_clauses.append("es_medicamento = 1")
             
        # Construir bloque T-SQL autoportante
        sql_block = f"""
        BEGIN
            DECLARE @id_taxonomia INT;
            
            SELECT @id_taxonomia = id_taxonomia 
            FROM Procurement.Taxonomia 
            WHERE dominio = {fmt(dominio)} 
              AND ISNULL(categoria, 'SINEVAL') = {fmt(categoria)} 
              AND ISNULL(subcategoria, 'SINEVAL') = {fmt(subcategoria)};
              
            IF @id_taxonomia IS NULL
            BEGIN
                INSERT INTO Procurement.Taxonomia (dominio, categoria, subcategoria) 
                VALUES ({fmt(dominio)}, NULLIF({fmt(categoria)}, 'SINEVAL'), NULLIF({fmt(subcategoria)}, 'SINEVAL'));
                SET @id_taxonomia = SCOPE_IDENTITY();
            END
            
            UPDATE Procurement.por_aprobacion_equivalencias 
            SET {', '.join(set_clauses)},
                id_taxonomia = @id_taxonomia
            WHERE codbarras = '{codbarras}';
        END
        """
        sql_statements.append(sql_block)
    
    return sql_statements

def ejecutar_sql(sql_statements):
    print("Ejecutando sentencias SQL en la base de datos...")
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    count = 0
    for stmt in sql_statements:
        try:
            cursor.execute(stmt)
            count += 1
        except Exception as e:
            print(f"Error ejecutando: {stmt}\nDetalle: {e}")
    conn.commit()
    conn.close()
    print(f"Actualización completada. {count} registros actualizados en la BD.")

if __name__ == "__main__":
    import sys
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    chunk_size = 15
    resultados_totales = []
    
    taxonomias_str = obtener_taxonomias_existentes()
    
    # === FASE 1: Ciclo 0 -> Usamos Qwen 2.5 72B Instruct ===
    print("\n--- INICIANDO FASE 1: Ciclo 0 (Qwen 2.5 72B Instruct) ---")
    lote_f1 = obtener_lote(limite, fase=1)
    if lote_f1:
        for i in range(0, len(lote_f1), chunk_size):
            if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD: break
            chunk = lote_f1[i:i+chunk_size]
            print(f"Fase 1 - Chunk {i//chunk_size + 1} de {(len(lote_f1)-1)//chunk_size + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), taxonomias_str, model="qwen/qwen-2.5-72b-instruct")
            if res: resultados_totales.extend(res)
            time.sleep(2)
    else:
        print("No hay registros en Ciclo 0 para la Fase 1.")
        
    # === FASE 2: Ciclo 1 -> Usamos Mixtral 8x22B Instruct ===
    print("\n--- INICIANDO FASE 2: Ciclo 1 (Mixtral 8x22B) ---")
    lote_f2 = obtener_lote(limite, fase=2)
    if lote_f2:
        for i in range(0, len(lote_f2), chunk_size):
            if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD: break
            chunk = lote_f2[i:i+chunk_size]
            print(f"Fase 2 - Chunk {i//chunk_size + 1} de {(len(lote_f2)-1)//chunk_size + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), taxonomias_str, model="mistralai/mixtral-8x22b-instruct")
            if res: resultados_totales.extend(res)
            time.sleep(2)
    else:
        print("No hay registros en Ciclo 1 para la Fase 2.")
 
    # === FASE 3: Ciclo 2 -> Usamos MiniMax M3 ===
    print("\n--- INICIANDO FASE 3: Ciclo 2 (MiniMax M3) ---")
    lote_f3 = obtener_lote(limite, fase=3)
    if lote_f3:
        for i in range(0, len(lote_f3), chunk_size):
            if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD: break
            chunk = lote_f3[i:i+chunk_size]
            print(f"Fase 3 - Chunk {i//chunk_size + 1} de {(len(lote_f3)-1)//chunk_size + 1} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), taxonomias_str, model="minimax/minimax-m3")
            if res: resultados_totales.extend(res)
            time.sleep(2)
    else:
        print("No hay registros en Ciclo 2 para la Fase 3.")
 
    # === FASE 4: Ciclo 3 -> Usamos Gemini 2.5 Pro ===
    print("\n--- INICIANDO FASE 4: Ciclo 3 (Gemini 2.5 Pro - Ciclo Final) ---")
    lote_f4 = obtener_lote(limite, fase=4)
    if lote_f4:
        chunk_size_f4 = 5
        chunks = [lote_f4[i:i+chunk_size_f4] for i in range(0, len(lote_f4), chunk_size_f4)]
        print(f"  Procesando {len(chunks)} chunks en paralelo con ThreadPoolExecutor (max_workers=5)...")
        
        resultados_f4 = []
        def procesar_un_chunk(idx, chunk):
            if GASTO_ACUMULADO_USD >= MAX_BUDGET_USD: return
            print(f"    [Thread] Iniciando chunk {idx+1}/{len(chunks)} ({len(chunk)} items)...")
            res = llamar_openrouter(json.dumps(chunk, indent=2), taxonomias_str, model="google/gemini-2.5-pro")
            if res:
                resultados_f4.extend(res)
                
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(procesar_un_chunk, idx, chunk) for idx, chunk in enumerate(chunks)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error procesando chunk en thread: {e}")
                    
        if resultados_f4:
            resultados_totales.extend(resultados_f4)
    else:
        print("No hay registros en Ciclo 3 para la Fase 4.")
    
    # === EJECUCIÓN BD ===
    if resultados_totales:
        print(f"\nGenerando SQL para {len(resultados_totales)} registros procesados...")
        with open(f'debug_resultados_{limite}_v2.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_totales, f, indent=2)
            
        catalog = MasterCatalog(CONN_STR)
        sql_stmts = generar_sql_updates(resultados_totales, catalog)
        
        with open(f'actualizacion_investigacion_{limite}_v2.sql', 'w', encoding='utf-8') as f:
            f.write('\nGO\n'.join(sql_stmts))
            
        ejecutar_sql(sql_stmts)
        print(f"\nPROCESO COMPLETADO. Gasto Total: ${GASTO_ACUMULADO_USD:.4f} USD")
    else:
        print("Fallo la generacion de IA o no hubo registros procesables.")
