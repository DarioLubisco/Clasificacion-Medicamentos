import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        return ""

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO') if atrib else 'MEDICAMENTO_ALOPATICO'
    es_med = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    if not atrib:
        return 0
        
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

def extract_json_from_content(content):
    content = content.strip()
    
    # Try finding markdown code block: ```json ... ``` or ``` ... ```
    for prefix in ["```json", "```"]:
        if prefix in content:
            parts = content.split(prefix)
            for part in parts[1:]:
                subpart = part.split("```")[0].strip()
                try:
                    return json.loads(subpart)
                except Exception:
                    pass
                    
    # Try finding the first '[' and matching using raw_decode
    start_idx = content.find('[')
    if start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(content[start_idx:])
            return obj
        except Exception:
            pass
            
    # Try direct parse
    try:
        return json.loads(content)
    except Exception:
        pass
        
    raise ValueError("No valid JSON found in response content")

def llamar_openrouter_multimodal(context_json_str, taxonomias_existentes, model, imagenes_b64):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos y sus descripciones, contextos web y TAMBIÉN IMÁGENES de referencia que debes analizar junto con el texto.
    Tu único objetivo es la PRECISIÓN ABSOLUTA (Zero-Tolerance). Extraer un dato que no está explícitamente en la descripción, en el contexto web adjunto o en las imágenes de referencia es un ERROR CRÍTICO. Ante la menor duda, debes devolver null.

    Analiza TODOS los elementos proporcionados (texto y visuales) para extraer los siguientes atributos:
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
    4. Marca / Fabricante / Origen: Si no hay información explícita, usa null. NO asumas 'Genérico' como marca. Si ves el laboratorio en la caja de la imagen, utilízalo.
    5. Segmento Etario: NO lo deduzcas sin evidencia (infantil, niños, pediátrico, adulto). Ante la duda, null.

    REGLA DE TAXONOMIA (INQUEBRANTABLE):
    {taxonomias_existentes}
    
    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web o imagen.
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

    LOTE A PROCESAR (Contexto Web Incluido):
    {context_json_str}
    """
    
    content_payload = [{"type": "text", "text": prompt}]
    for b64 in imagenes_b64:
        content_payload.append({"type": "image_url", "image_url": {"url": b64}})
        
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            usage = result.get('usage', {})
            content = result['choices'][0]['message']['content']
            if not content:
                refusal = result['choices'][0]['message'].get('refusal')
                reasoning = result['choices'][0]['message'].get('reasoning')
                print(f"    [Aviso] Modelo {model} no retornó content. Refusal: {refusal} | Reasoning: {reasoning}")
                return None, usage
                
            try:
                parsed_json = extract_json_from_content(content)
                return parsed_json, usage
            except Exception as e:
                print(f"    [Error Parseo] Fallo al extraer JSON de {model}: {e}")
                print(f"    [Contenido Crudo]:\n{content}\n")
                return None, usage
    except Exception as e:
        print(f"    Error {model}: {e}")
        return None, {}

def main():
    print("INICIANDO EVALUACIÓN MULTIMODAL DE GEMMA 4 31B Y 26B-A4B")
    
    input_path = "scratch/scraping_multimodal_results.json"
    comp_path = "scratch/resultados_comparativa_multimodal.json"
    excel_path = "scratch/comparativa_modelos_multimodal.xlsx"
    
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra {input_path}")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        lote_scraping = json.load(f)
        
    resultados_multimodal = {}
    if os.path.exists(comp_path):
        try:
            with open(comp_path, "r", encoding="utf-8") as f:
                resultados_multimodal = json.load(f)
        except Exception:
            pass
            
    taxonomias_str = obtener_taxonomias_estrictas()
    
    modelos = {
        "gemma_4_31b": "google/gemma-4-31b-it",
        "gemma_4_26b": "google/gemma-4-26b-a4b-it"
    }
    
    precios = {
        "gemma_4_31b": {"in": 0.12 / 1e6, "out": 0.35 / 1e6},
        "gemma_4_26b": {"in": 0.06 / 1e6, "out": 0.33 / 1e6}
    }
    
    for item in lote_scraping:
        ean = item["ean"]
        desc = item["descripcion"]
        fuentes_web = item["fuentes_web"]
        imagenes_b64 = item["imagenes_b64"]
        
        print(f"\nProcesando EAN {ean} - {desc} (Fuentes: {len(fuentes_web)}, Imágenes: {len(imagenes_b64)})")
        
        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]
        
        if ean not in resultados_multimodal:
            resultados_multimodal[ean] = {"descripcion": desc}
            
        res_ean = resultados_multimodal[ean]
        res_ean["descripcion"] = desc
        
        updated_any = False
        for key, model_id in modelos.items():
            if key in res_ean and not res_ean[key].get("error", False) and res_ean[key].get("atrib") is not None:
                print(f"  {key} ya evaluado con éxito (Score: {res_ean[key]['score']}). Omitiendo.")
                continue
                
            print(f"  Evaluando con {model_id}...")
            res_txt, usage = llamar_openrouter_multimodal(json.dumps(context_block, indent=2), taxonomias_str, model_id, imagenes_b64)
            
            p_tokens = usage.get('prompt_tokens', 0)
            c_tokens = usage.get('completion_tokens', 0)
            costo = (p_tokens * precios[key]["in"]) + (c_tokens * precios[key]["out"])
            
            if res_txt and len(res_txt) > 0:
                atrib = res_txt[0].get('atributos_nuevos_consolidados', {})
                score = calcular_score_calidad(atrib)
                atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
                res_ean[key] = {
                    "atrib": atrib,
                    "score": score,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo": costo
                }
                print(f"    [{key} Éxito] Score: {score} | Confianza: {atrib.get('confianza_nivel')} | Costo: ${costo:.6f}")
            else:
                res_ean[key] = {
                    "atrib": None,
                    "score": 0,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo": costo,
                    "error": True
                }
                print(f"    [{key} Fallo/Rechazo] Costo: ${costo:.6f}")
            
            updated_any = True
                
        resultados_multimodal[ean] = res_ean
        
        # Guardar reporte consolidado JSON
        if updated_any:
            with open(comp_path, "w", encoding="utf-8") as f:
                json.dump(resultados_multimodal, f, indent=2, ensure_ascii=False)
        
    # Guardar reporte consolidado JSON
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(resultados_multimodal, f, indent=2, ensure_ascii=False)
        
    # Recrear el archivo Excel
    rows = []
    model_mapping = {
        "gemini_2_5_flash": "Gemini 2.5 Flash",
        "gemini_2_5_pro": "Gemini 2.5 Pro",
        "gemini_3_1_pro": "Gemini 3.1 Pro",
        "gemma_4_31b": "Gemma 4 31B",
        "gemma_4_26b": "Gemma 4 26B-A4B"
    }
    
    for ean, item in resultados_multimodal.items():
        desc = item["descripcion"]
        for model_key, model_name in model_mapping.items():
            model_res = item.get(model_key)
            if not model_res or model_res.get("atrib") is None:
                rows.append({
                    "EAN": ean,
                    "Descripción": desc,
                    "Modelo": model_name,
                    "Score": 0,
                    "Confianza Nivel": "Rechazado/Error",
                    "Confianza Razonamiento": "El modelo se rehusó a clasificar o falló en responder",
                    "Dominio": None,
                    "Principio Activo": None,
                    "Concentración": None,
                    "Forma Farmacéutica": None,
                    "Cantidad Presentación": None,
                    "Contenido Neto": None,
                    "Unidad Neto": None,
                    "Marca": None,
                    "Fabricante": None,
                    "ATC": None,
                    "Genérico": None,
                    "Costo USD": model_res.get("costo", 0.0) if model_res else 0.0,
                    "Razonamiento": None
                })
                continue
                
            at = model_res["atrib"]
            rows.append({
                "EAN": ean,
                "Descripción": desc,
                "Modelo": model_name,
                "Score": model_res.get("score", 0),
                "Confianza Nivel": at.get("confianza_nivel"),
                "Confianza Razonamiento": at.get("confianza_razonamiento"),
                "Dominio": at.get("dominio"),
                "Principio Activo": at.get("principio_activo"),
                "Concentración": at.get("concentracion"),
                "Forma Farmacéutica": at.get("forma_farmaceutica"),
                "Cantidad Presentación": at.get("cantidad_presentacion"),
                "Contenido Neto": at.get("contenido_neto"),
                "Unidad Neto": at.get("contenido_neto_unidad_Des"),
                "Marca": at.get("marca"),
                "Fabricante": at.get("fabricante"),
                "ATC": at.get("codigo_atc"),
                "Genérico": at.get("generico"),
                "Costo USD": model_res.get("costo", 0.0),
                "Razonamiento": at.get("razonamiento")
            })
            
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparativa Multimodal")
        
    print(f"Archivo de Excel regenerado en: {os.path.abspath(excel_path)}")

if __name__ == "__main__":
    main()
