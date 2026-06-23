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

socket.setdefaulttimeout(180)

# Add parent directory to path to import MDM_Unified_Mapper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MDM_Unified_Mapper import MasterCatalog

gasto_lock = threading.Lock()
GASTO_ACUMULADO_USD = 0.0
MAX_BUDGET_USD = 5.00
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
                costo = (p_tokens * 1.25 + c_tokens * 5.00) / 1000000.0
                
                with gasto_lock:
                    GASTO_ACUMULADO_USD += costo
                print(f"  [IA-Text] {model} | Costo req: ${costo:.5f} | Acumulado: ${GASTO_ACUMULADO_USD:.5f}")
                
                content = result['choices'][0]['message']['content']
                if content.startswith("```json"): content = content[7:]
                if content.endswith("```"): content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            print(f"  Error llamando a OpenRouter ({model}): {e}")
            time.sleep(5)
    return None

def llamar_vision_multimodal(codbarras, desc, url_imagenes, model="google/gemini-2.5-flash"):
    import base64
    
    valid_urls = [u for u in url_imagenes if u and u.strip().startswith(('http://', 'https://'))]
    if not valid_urls:
        print(f"  [Vision] Sin URLs de imagen válidas para EAN {codbarras}")
        return None
        
    base64_imgs = []
    for img_url in valid_urls[:5]:
        try:
            req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=8) as response:
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                if 'image' not in content_type and 'octet-stream' not in content_type:
                    continue
                img_data = response.read()
                if 'image' not in content_type:
                    content_type = 'image/jpeg'
                encoded = base64.b64encode(img_data).decode('utf-8')
                base64_imgs.append(f"data:{content_type};base64,{encoded}")
                if len(base64_imgs) >= 3:
                    break
        except Exception as e:
            continue

    if not base64_imgs:
        print(f"  [Vision] No se pudo descargar imagen para EAN {codbarras}")
        return None

    print(f"  [Vision] Analizando {len(base64_imgs)} imagenes en Base64 para EAN {codbarras} usando {model}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    content_payload = [
        {"type": "text", "text": f"Observa esta caja de medicamento/producto (EAN: {codbarras}, Desc: {desc}) en sus distintos ángulos.\nExtrae los siguientes datos impresos explícitamente en el empaque:\n- Nombre comercial (Marca)\n- Laboratorio (Fabricante)\n- País o región de manufactura (Origen)\n- Principio Activo\n- Concentración\n- Forma Farmacéutica\n- Cantidad Presentación\n- Contenido Neto\n\nNIVELES DE CONFIANZA VISUAL:\nDebes autoevaluar tu clasificación usando un 'confianza_nivel' (entero del 1 al 5) y explicarlo en 'confianza_razonamiento'.\n5 - TOTAL: Todo se lee claramente en la foto.\n4 - ALTA: Casi todo es legible con alta certeza.\n3 - MEDIA: Se lee parcialmente, hay reflejos o zonas borrosas.\n2 - BAJA: Muy borroso, apenas inferible.\n1 - NULA: Caja ilegible o no aporta información.\n\nDevuelve JSON: {{\"marca\": \"...\", \"fabricante\": \"...\", \"origen\": \"...\", \"principio_activo\": \"...\", \"concentracion\": \"...\", \"forma_farmaceutica\": \"...\", \"cantidad_presentacion\": \"...\", \"contenido_neto\": \"...\", \"confianza_nivel\": 5, \"confianza_razonamiento\": \"...\"}}"}
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
            
            usage = result.get('usage', {})
            p_tokens = usage.get('prompt_tokens', 0)
            c_tokens = usage.get('completion_tokens', 0)
            costo = (p_tokens * 0.075 + c_tokens * 0.3) / 1000000.0 # Aproximado Flash
            global GASTO_ACUMULADO_USD
            with gasto_lock:
                GASTO_ACUMULADO_USD += costo
            print(f"  [IA-Vision] {model} | Costo req: ${costo:.5f} | Acumulado: ${GASTO_ACUMULADO_USD:.5f}")

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
    
    # Para valores numéricos
    try:
        # Reemplazar comas por puntos para soporte decimal
        num_clean = val_str.replace(',', '.')
        float(num_clean)
        return num_clean
    except ValueError:
        # Intentar extraer el primer número de la cadena
        import re
        nums = re.findall(r'\d+(?:\.\d+)?', val_str)
        if nums:
            return nums[0]
        return "NULL"

def main():
    taxonomias_str = obtener_taxonomias_estrictas()
    if not taxonomias_str:
        print("ERROR CRITICO: Taxonomia vacía.")
        return

    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT TOP 5 s.codbarras, p.descrip1art
        FROM Procurement.scraping_farmacias_raw s
        JOIN Procurement.por_aprobacion_equivalencias p ON s.codbarras = p.codbarras
        WHERE s.procesado_fase3 = 0
    """)
    pendientes = cursor.fetchall()
    
    if not pendientes:
        print("No hay datos de scraping pendientes por evaluar (Fase 3).")
        return

    print(f"Iniciando Motor IA (Fase 3) Desacoplado para {len(pendientes)} EANs...")
    
    catalog = MasterCatalog(CONN_STR)

    for p in pendientes:
        codbarras = p.codbarras.strip()
        desc = p.descrip1art.strip()
        
        cursor.execute("""
            SELECT id_scrap, url_origen, texto_extraido, url_imagen 
            FROM Procurement.scraping_farmacias_raw 
            WHERE codbarras = ? AND procesado_fase3 = 0
        """, (codbarras,))
        bloques = cursor.fetchall()
        
        ids_scrap = []
        fuentes_web = []
        todas_imagenes = []
        
        for b in bloques:
            ids_scrap.append(b.id_scrap)
            if b.url_imagen:
                todas_imagenes.append(b.url_imagen)
            fuentes_web.append({
                "url": b.url_origen,
                "texto": b.texto_extraido
            })

        print(f"\nEvaluando {codbarras} con {len(fuentes_web)} bloques de texto y {len(todas_imagenes)} imágenes.")

        context_block = [{
            "registro": {
                "codbarras": codbarras, 
                "descripcion_original": desc
            },
            "fuentes_web": fuentes_web
        }]
        
        res_textual = llamar_openrouter_strict(json.dumps(context_block, indent=2), taxonomias_str)
        if not res_textual: 
            print("  Fallo en la respuesta de Gemini.")
            continue
            
        item_txt = res_textual[0]
        atrib = item_txt.get('atributos_nuevos_consolidados', {})
        score = calcular_score_calidad(atrib)
        
        # Validar si intentamos Vision
        # Intentamos visión si score es bajo O si falta algún dato fundamental
        necesita_vision = False
        if score < 100:
            if not atrib.get('marca') or not atrib.get('fabricante') or not atrib.get('origen') or not atrib.get('principio_activo'):
                necesita_vision = True
                
        if necesita_vision and todas_imagenes:
            res_visual = llamar_vision_multimodal(codbarras, desc, todas_imagenes)
            if res_visual:
                if isinstance(res_visual, list) and len(res_visual) > 0:
                    res_visual = res_visual[0]
                if isinstance(res_visual, dict):
                    # Heredar campos faltantes desde Visión
                    campos_heredar = ['marca', 'fabricante', 'origen', 'principio_activo', 'concentracion', 'forma_farmaceutica', 'cantidad_presentacion', 'contenido_neto']
                    for campo in campos_heredar:
                        if res_visual.get(campo) and not atrib.get(campo):
                            atrib[campo] = res_visual[campo]
                            
                    # Combinar razonamiento y actualizar nivel de confianza si la visión tuvo alta confianza
                    vision_conf = res_visual.get('confianza_nivel', 1)
                    texto_conf = atrib.get('confianza_nivel', 1)
                    if vision_conf > texto_conf:
                        atrib['confianza_nivel'] = vision_conf
                        
                    atrib['razonamiento'] = str(atrib.get('razonamiento','')) + " | VISUAL: " + str(res_visual.get('confianza_razonamiento', res_visual.get('razonamiento_visual', '')))
                    score = calcular_score_calidad(atrib)

        atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
        
        dominio = atrib.get('dominio', 'SINEVAL')
        categoria = atrib.get('categoria', 'SINEVAL')
        subcategoria = atrib.get('subcategoria', 'SINEVAL')
        es_med = (dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO'])
        
        confianza = atrib.get('confianza_nivel', 1)
        
        # LOGICA ESTRICTA DE ESTADO: Requiere score alto Y confianza alta
        if (score >= 85 and confianza >= 4) or (not es_med and score >= 60 and confianza >= 3):
            estado_ciclo = 'CERRADO'
        else:
            estado_ciclo = 'REVISION_MANUAL'
            
        obs = fmt(str(atrib.get('razonamiento'))[:95]) if atrib.get('razonamiento') else "NULL"
        img_json = fmt(json.dumps(todas_imagenes)) if todas_imagenes else "NULL"
        
        id_pa = catalog.find_id("principio_activo", atrib.get('principio_activo'))
        id_con = catalog.find_id("concentracion", atrib.get('concentracion'))
        id_ff = catalog.find_id("forma_farmaceutica", atrib.get('forma_farmaceutica'))
        
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
            f"origen_dato = 'IA_FASE3_DB_V2'",
            f"imagen_urls = {img_json}",
            f"principio_activo = {fmt(id_pa, False)}",
            f"concentracion = {fmt(id_con, False)}",
            f"forma_farmaceutica = {fmt(id_ff, False)}"
        ]
        
        sql_update = f"""
        DECLARE @id_taxonomia INT;
        SELECT @id_taxonomia = id_taxonomia FROM Procurement.Taxonomia 
        WHERE dominio = {fmt(dominio)} AND ISNULL(categoria, 'SINEVAL') = {fmt(categoria)} AND ISNULL(subcategoria, 'SINEVAL') = {fmt(subcategoria)};
          
        UPDATE Procurement.por_aprobacion_equivalencias 
        SET {', '.join(set_clauses)}, id_taxonomia = @id_taxonomia
        WHERE codbarras = '{codbarras}';
        """
        
        try:
            cursor.execute(sql_update)
            placeholders = ','.join('?' for _ in ids_scrap)
            cursor.execute(f"UPDATE Procurement.scraping_farmacias_raw SET procesado_fase3 = 1 WHERE id_scrap IN ({placeholders})", ids_scrap)
            print(f"  -> Guardado exitosamente (Score: {score}, Confianza: {confianza}, Estado: {estado_ciclo}).")
        except Exception as e:
            print(f"  -> Error al guardar en BD: {e}")
            print(f"  -> SQL que falló:\n{sql_update}")

    conn.close()
    print("Motor IA (Fase 3) finalizado.")

if __name__ == "__main__":
    main()
