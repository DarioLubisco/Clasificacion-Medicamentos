import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import os
import sys
import re
import pandas as pd
from dotenv import load_dotenv
import requests
import base64
import mimetypes
from PIL import Image
import io

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def obtener_taxonomias_estrictas():
    cache_path = "scratch/taxonomias_local.txt"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    try:
        conn = pyodbc.connect(CONN_STR, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
        conn.close()
        tax_str = "\n".join(tax)
        os.makedirs("scratch", exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(tax_str)
        return tax_str
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
    for prefix in ["```json", "```"]:
        if prefix in content:
            parts = content.split(prefix)
            for part in parts[1:]:
                subpart = part.split("```")[0].strip()
                try:
                    return json.loads(subpart)
                except Exception:
                    pass
    start_idx_dict = content.find('{')
    if start_idx_dict != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(content[start_idx_dict:])
            return obj
        except Exception:
            pass
    start_idx = content.find('[')
    if start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(content[start_idx:])
            return obj
        except Exception:
            pass
    try:
        return json.loads(content)
    except Exception:
        pass
    raise ValueError("No valid JSON found in response content")

def filtrar_imagenes_legibles(imagenes_b64, descripcion_producto, modelo_texto_actual=""):
    if not imagenes_b64:
        return [], [], 0.0
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Se te dará la descripción de un producto comercial ('{descripcion_producto}') y una imagen. ¿La imagen parece corresponder al producto de la descripción (ya sea medicamento, jeringa, equipo médico, misceláneo, etc.)? Si la imagen NO tiene relación alguna o es puro ruido/error, responde únicamente con el número 0. Si SÍ corresponde o parece coherente, califica la legibilidad de la información impresa (empaque, marca, especificaciones) del 1 al 5. Responde ÚNICAMENTE con el número entero (0, 1, 2, 3, 4 o 5), sin ningún texto adicional."
    
    # Aislamiento de Pipeline visual
    vision_model = "google/gemini-2.5-flash"
    precio_in = 0.075
    precio_out = 0.30

    costo_total = 0.0
    fotos_aprobadas = []
    fotos_a_guardar = []
    imagenes_unicas = list(dict.fromkeys(imagenes_b64))

    for url_img in imagenes_unicas[:10]:
        if len(fotos_aprobadas) >= 3:
            break
            
        try:
            if url_img.startswith("data:image"):
                b64_uri = url_img
            else:
                # Descargar imagen localmente para el pre-filtro (evitando 400 Bad Request por proxy de Gemini)
                headers_img = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                img_res = requests.get(url_img, headers=headers_img, timeout=10)
                if img_res.status_code != 200:
                    print(f"    [Pre-Filtro] Error HTTP {img_res.status_code} descargando URL {url_img}. Omitiendo.")
                    continue
                
                b64_data = base64.b64encode(img_res.content).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(url_img)
                if not mime_type:
                    mime_type = "image/jpeg"
                b64_uri = f"data:{mime_type};base64,{b64_data}"
        except Exception as e:
            print(f"    [Pre-Filtro] Error local conectando a URL {url_img}: {e}")
            continue

        data = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": b64_uri}}
                    ]
                }
            ],
            "temperature": 0.0
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tok = usage.get('prompt_tokens', 0)
                c_tok = usage.get('completion_tokens', 0)
                # Cálculo de costo de visión del modelo que pre-filtra
                costo_total += (p_tok * precio_in / 1e6) + (c_tok * precio_out / 1e6)
                
                content = result['choices'][0]['message']['content'].strip()
                match = re.search(r'\d+', content)
                if match:
                    calificacion = int(match.group())
                    if calificacion > 0:
                        # Guardamos en la tabla satélite con su score original (Solo URL como pidió el usuario)
                        fotos_a_guardar.append({"url_imagen": url_img, "score": calificacion, "b64_uri": b64_uri})
                        if calificacion >= 3:
                            fotos_aprobadas.append(b64_uri)
                            print(f"    [Pre-Filtro] Foto Aprobada (Puntaje: {calificacion}) - URL guardada.")
                        else:
                            print(f"    [Pre-Filtro] Foto Salvada/Reserva (Puntaje: {calificacion})")
                    else:
                        print(f"    [Pre-Filtro] Foto Descartada, no coincide (Puntaje: 0)")
                else:
                    print(f"    [Pre-Filtro] Respuesta inesperada: {content}")
        except Exception as e:
            print(f"    [Pre-Filtro] Error evaluando imagen: {e}")
            continue
            
    return fotos_aprobadas, fotos_a_guardar, costo_total

def transcribir_imagenes_gemini(fotos_aprobadas, desc_producto):
    """Envía las imágenes aprobadas a Gemini Flash 2.5 para OCR farmacéutico.
    Retorna una lista de transcripciones de texto y el costo acumulado."""
    if not fotos_aprobadas:
        return [], 0.0

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    ocr_prompt = (
        f"Eres un extractor OCR farmacéutico. Se te muestra la imagen de un producto: '{desc_producto}'.\n"
        "Extrae TODO el texto visible en la imagen: nombre del producto, laboratorio/fabricante, "
        "principio activo, concentración, forma farmacéutica, contenido neto, presentación, "
        "país de origen, registro sanitario, lote, fecha de vencimiento, y cualquier otro dato "
        "farmacéutico legible.\n\n"
        "Si la imagen es ilegible o no tiene texto útil, responde EXACTAMENTE: IMAGEN SIN TEXTO ÚTIL\n\n"
        "Responde SOLO con el texto extraído, sin comentarios adicionales."
    )
    precio_in = 0.075 / 1e6
    precio_out = 0.30 / 1e6
    costo_ocr = 0.0
    transcripciones = []

    for idx, b64_uri in enumerate(fotos_aprobadas[:3], 1):
        data = {
            "model": "google/gemini-2.5-flash",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": ocr_prompt},
                    {"type": "image_url", "image_url": {"url": b64_uri}}
                ]
            }],
            "temperature": 0.0
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tok = usage.get('prompt_tokens', 0)
                c_tok = usage.get('completion_tokens', 0)
                costo_ocr += (p_tok * precio_in) + (c_tok * precio_out)
                text_out = result['choices'][0]['message']['content'].strip()
                if text_out and "IMAGEN SIN TEXTO ÚTIL" not in text_out:
                    transcripciones.append(f"[Imagen {idx}]: {text_out}")
                    print(f"    [OCR Gemini] Imagen {idx}: {len(text_out)} chars extraídos")
                else:
                    print(f"    [OCR Gemini] Imagen {idx}: Sin texto útil")
        except Exception as e:
            print(f"    [OCR Gemini] Error en imagen {idx}: {e}")

    return transcripciones, costo_ocr

def llamar_openrouter_multimodal(context_json_str, taxonomias_existentes, model, imagenes_b64, desc_producto):
    fotos_aprobadas, fotos_a_guardar, costo_vision = filtrar_imagenes_legibles(imagenes_b64, desc_producto, model)

    # ═══════════════════════════════════════════════════════════════════
    # OCR: Para modelos texto-only, transcribir las imágenes con Gemini
    # Para modelos multimodales, también transcribir como respaldo de texto
    # ═══════════════════════════════════════════════════════════════════
    es_modelo_texto_only = "deepseek" in model.lower()
    transcripciones = []
    costo_ocr = 0.0

    if fotos_aprobadas:
        transcripciones, costo_ocr = transcribir_imagenes_gemini(fotos_aprobadas, desc_producto)
        costo_vision += costo_ocr

    if not fotos_aprobadas:
        nota_vision = "[Nota: No se logró conseguir ninguna imagen de calidad suficiente (legibilidad < 3). Procede usando únicamente los datos de texto web.]"
    elif es_modelo_texto_only:
        if transcripciones:
            texto_ocr = "\n".join(transcripciones)
            nota_vision = (
                f"[Nota: Se procesaron {len(fotos_aprobadas)} imagen(es) pre-aprobadas mediante OCR (Gemini Flash). "
                f"A continuación el texto extraído de las imágenes del producto:]\n\n"
                f"--- INICIO TRANSCRIPCIÓN OCR ---\n{texto_ocr}\n--- FIN TRANSCRIPCIÓN OCR ---"
            )
        else:
            nota_vision = "[Nota: Se encontraron imágenes pero ninguna contenía texto farmacéutico legible. Procede usando únicamente los datos de texto web.]"
    else:
        nota_vision_parts = [f"[Nota: Se adjuntan {len(fotos_aprobadas)} imagen(es) pre-aprobadas con alta legibilidad para análisis visual directo.]"]
        if transcripciones:
            texto_ocr = "\n".join(transcripciones)
            nota_vision_parts.append(
                f"[Respaldo OCR del texto visible en las imágenes:]\n"
                f"--- INICIO TRANSCRIPCIÓN OCR ---\n{texto_ocr}\n--- FIN TRANSCRIPCIÓN OCR ---"
            )
        nota_vision = "\n".join(nota_vision_parts)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    

    # ═══════════════════════════════════════════════════════════════════
    # CARGA DEL PROMPT DESDE ARCHIVO EXTERNO (ver CONTEXT.md seccion 2)
    # Separado del .py para evitar que ediciones al prompt rompan logica
    # ═══════════════════════════════════════════════════════════════════
    prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_agente_v3_solidificado_final.txt")
    with open(prompt_template_path, "r", encoding="utf-8") as f_prompt:
        prompt_template = f_prompt.read()

    prompt = prompt_template.replace(
        "{taxonomias_existentes}", taxonomias_existentes
    ).replace(
        "{context_json_str}", context_json_str
    ).replace(
        "{nota_vision}", nota_vision
    )

    content_payload = [{"type": "text", "text": prompt}]

    # ═══════════════════════════════════════════════════════════════════
    # RESTRICCION R1 (CONTEXT.md): DeepSeek NO soporta vision.
    # Solo los modelos que NO sean DeepSeek reciben imagenes en el payload.
    # DeepSeek recibe la informacion visual como texto transcrito (nota_vision).
    # ═══════════════════════════════════════════════════════════════════
    es_modelo_texto_only = "deepseek" in model.lower()

    if not es_modelo_texto_only:
        for b64 in fotos_aprobadas:
            content_payload.append({
                "type": "image_url",
                "image_url": {"url": b64}
            })

    # ASERCION DEFENSIVA R1: Verificar que NUNCA se envien imagenes a DeepSeek
    if es_modelo_texto_only:
        for item in content_payload:
            assert item.get("type") != "image_url", \
                "ERROR CRITICO (CONTEXT.md R1): imagen enviada a modelo texto-only: " + model

    es_deepseek = "deepseek" in model.lower()
    temp_value = 0.6 if es_deepseek else 0.2

    data = {
        "model": model,
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": temp_value,
        "top_p": 0.9
    }
    if es_deepseek:
        data["reasoning"] = {"effort": "xhigh"}

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode())
            usage = result.get('usage', {})
            finish_reason = result['choices'][0].get('finish_reason', '')
            
            if finish_reason == 'length':
                print(f"\n    [⚠️ ALERTA STRESS TEST] El modelo {model} se quedó SIN TOKENS (finish_reason: length). ¡Razonamiento cortado!\n")
                usage['finish_reason'] = 'length'
                
            content = result['choices'][0]['message']['content']
            if not content:
                refusal = result['choices'][0]['message'].get('refusal')
                reasoning = result['choices'][0]['message'].get('reasoning')
                print(f"    [Aviso] Modelo {model} no retornó content. Refusal: {refusal} | Reasoning: {reasoning}")
                return None, usage, None, costo_vision, fotos_a_guardar
                
            try:
                parsed_json = extract_json_from_content(content)
                return parsed_json, usage, content, costo_vision, fotos_a_guardar
            except Exception as e:
                print(f"    [Error Parseo] Fallo al extraer JSON de {model}: {e}")
                print(f"    [Contenido Crudo]:\n{content}\n")
                return None, usage, content, costo_vision, fotos_a_guardar
    except Exception as e:
        print(f"    Error {model}: {e}")
        return None, {}, None, costo_vision, fotos_a_guardar


def main(input_path="scratch/eval_5_combined.json", comp_path="scratch/resultados_comparativa_combinados.json", excel_path="scratch/comparativa_modelos_combinados.xlsx"):
    print("INICIANDO EVALUACIÓN MULTIMODAL (PROMPT OPTIMIZADO DEL USUARIO)")
    
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
    
    try:
        with open("modelos_activos.json", "r") as fm:
            cfg = json.load(fm)
            modelos = cfg["texto"]
            precios = {k: {"in": v["in"]/1e6, "out": v["out"]/1e6} for k, v in cfg["precios"].items()}
    except Exception as e:
        print(f"Error cargando modelos_activos.json: {e}")
        return
    
    lote_aleatorio = lote_scraping

    for item in lote_aleatorio:
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
        
        keys_to_evaluate = list(modelos.keys())
        
        i = 0
        while i < len(keys_to_evaluate):
            key = keys_to_evaluate[i]
            
            # Espacio dejado libre, el insert se movió abajo
            
            # Evaluar con cada modelo activo
            model_id = modelos[key]
            i += 1
            
            if key in res_ean and not res_ean[key].get("error", False) and res_ean[key].get("atrib") is not None:
                print(f"  {key} ya evaluado con éxito (Score: {res_ean[key]['score']}). Omitiendo.")
                continue
                
            print(f"  Evaluando con {model_id}...")
            res_txt, usage, content, costo_vision, fotos_guardadas = llamar_openrouter_multimodal(json.dumps(context_block, indent=2), taxonomias_str, model_id, imagenes_b64, desc)
            
            # INSERTAR LAS IMÁGENES SALVADAS A LA CARPETA FISICA LOCAL
            if fotos_guardadas:
                folder_path = os.path.join("scratch", "imagenes_productos")
                os.makedirs(folder_path, exist_ok=True)
                for idx, pic_data in enumerate(fotos_guardadas, 1):
                    try:
                        b64_str = pic_data.get("b64_uri", "").split("base64,")[-1]
                        if b64_str:
                            file_name = f"{ean}.webp" if idx == 1 else f"{ean}_{idx}.webp"
                            file_dest = os.path.join(folder_path, file_name)
                            
                            img_data = base64.b64decode(b64_str)
                            image = Image.open(io.BytesIO(img_data))
                            if image.mode in ("RGBA", "P"):
                                image = image.convert("RGB")
                            image.save(file_dest, "WEBP", quality=80)
                            
                            # Actualizamos url_imagen para que sea la ruta relativa del servidor web
                            pic_data["url_imagen"] = f"/imagenes/{file_name}"
                            
                            print(f"    [Local] Imagen convertida y guardada en: {file_dest}")
                    except Exception as e_local:
                        print(f"    [Local Error] No se pudo procesar imagen para webp: {e_local}")
            res_ean["fotos_a_guardar"] = fotos_guardadas
            
            p_tokens = usage.get('prompt_tokens', 0)
            c_tokens = usage.get('completion_tokens', 0)
            costo_texto = (p_tokens * precios[key]["in"]) + (c_tokens * precios[key]["out"])
            costo_total = costo_texto + costo_vision
            
            if res_txt:
                if isinstance(res_txt, list) and len(res_txt) > 0 and isinstance(res_txt[0], dict):
                    item_json = res_txt[0]
                elif isinstance(res_txt, dict):
                    item_json = res_txt
                else:
                    item_json = {}
                    
                atrib = item_json.get('atributos_nuevos_consolidados', {})
                score = calcular_score_calidad(atrib)
                atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
                res_ean[key] = {
                    "atrib": atrib,
                    "score": score,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo_vision": costo_vision,
                    "costo_texto": costo_texto,
                    "costo_total": costo_total,
                    "costo": costo_total
                }
                print(f"    [{key} Éxito] Score: {score} | Confianza: {atrib.get('confianza_nivel')} | Costo Total: ${costo_total:.6f} (Visión: ${costo_vision:.6f}, Texto: ${costo_texto:.6f})")
            else:
                res_ean[key] = {
                    "atrib": None,
                    "score": 0,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo_vision": costo_vision,
                    "costo_texto": costo_texto,
                    "costo_total": costo_total,
                    "costo": costo_total,
                    "error": True
                }
                print(f"    [{key} Fallo/Rechazo] Costo Total: ${costo_total:.6f} (Visión: ${costo_vision:.6f}, Texto: ${costo_texto:.6f})")
                
                with open("scratch/ia_errors.log", "a", encoding="utf-8") as f_err:
                    f_err.write(f"--- ERROR EAN {ean} ({model_id}) ---\n{content}\n\n")
                    
                pass
            
            updated_any = True
                
        resultados_multimodal[ean] = res_ean
        
        # Guardar reporte consolidado JSON incrementalmente
        if updated_any:
            with open(comp_path, "w", encoding="utf-8") as f:
                json.dump(resultados_multimodal, f, indent=2, ensure_ascii=False)
        
    # Recrear el archivo Excel
    rows = []
    model_mapping = {
        "deepseek_v4_flash": "DeepSeek V4 Flash",
        "deepseek_v4_pro": "DeepSeek V4 Pro"
    }
    
    for ean, item in resultados_multimodal.items():
        desc = item["descripcion"]
        for model_key, model_name in model_mapping.items():
            model_res = item.get(model_key)
            if not model_res or model_res.get("atrib") is None:
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
                "Costo Visión Gemini USD": model_res.get("costo_vision", 0.0),
                "Costo Consolidación USD": model_res.get("costo_texto", 0.0),
                "Costo Total USD": model_res.get("costo_total", 0.0),
                "Razonamiento": at.get("razonamiento")
            })
            
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparativa Optimizada")
        
    print(f"Archivo de Excel regenerado en: {os.path.abspath(excel_path)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stress":
        main(
            input_path="scratch/eval_stress.json",
            comp_path="scratch/resultados_stress.json",
            excel_path="scratch/comparativa_stress.xlsx"
        )
    else:
        main(input_path="scratch/eval_test_5_hard.json", comp_path="scratch/resultados_triple.json", excel_path="scratch/comparativa_triple.xlsx")
