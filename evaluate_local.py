"""
Pipeline local canónico: scraper web + visión (MiMo/Gemini) + consolidación LLM.

Único orquestador de extracción de atributos del proyecto.
  python3 run_experimento.py
  python3 evaluate_local.py   # o main(input_path=..., output_path=...)
"""
import os
from dotenv import load_dotenv
import json
import urllib.request
import sys
import re
import pandas as pd
import requests
import base64
import mimetypes
import time
from pathlib import Path

from synapse_cred import load_synapse_credentials
load_synapse_credentials()

from pathlib import Path as _Path
load_dotenv(_Path(__file__).resolve().parent / ".env")

from pipeline_logger import log, log_producto, log_resumen, log_evento

# Cliente Z.ai directo (GLM Coding Plan)
from cliente_glm import call_glm, extract_content, estimate_cost, GLM_MODEL as ZAI_MODEL
from cliente_vision_mimo import call_mimo_chat, extract_content as mimo_extract_content
from cliente_vision_mimo import estimate_cost as mimo_estimate_cost, reasoning_tokens as mimo_reasoning_tokens

# Cliente DeepSeek nativo (api.deepseek.com) — opcional, activado vía IA_PROVEEDOR=deepseek
try:
    from cliente_deepseek import call_deepseek, extract_content as deepseek_extract_content
    from cliente_deepseek import estimate_cost as deepseek_estimate_cost, DEEPSEEK_MODEL
except Exception:
    call_deepseek = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GLM_MODEL = ZAI_MODEL  # alias; el modelo viene de N8N/synapse.credentials (glm-4.7)

# Precios OpenRouter Gemini Flash (USD / 1M tokens)
GEMINI_PRICE_IN_PER_1M = 0.30
GEMINI_PRICE_OUT_PER_1M = 2.50


def _vision_config():
    """Config de visión desde .env vía variables de entorno."""
    proveedor = os.getenv("VISION_PROVEEDOR", "mimo").lower()
    modelo = os.getenv("VISION_MODELO", "mimo-v2.5")
    thinking = os.getenv("VISION_THINKING", "disabled").lower()
    max_prefiltro = int(os.getenv("VISION_MAX_PREFILTRO", "10"))
    max_ocr = int(os.getenv("VISION_MAX_OCR", "3"))
    umbral = int(os.getenv("VISION_UMBRAL", "3"))
    return {
        "proveedor": proveedor,
        "modelo": modelo,
        "thinking": thinking,
        "max_prefiltro": max_prefiltro,
        "max_ocr": max_ocr,
        "umbral": umbral,
    }


def _vision_label(cfg: dict) -> str:
    if cfg["proveedor"] == "mimo":
        return f"MiMo {cfg['modelo']} (Token Plan, thinking={cfg['thinking']})"
    return f"{cfg['modelo']} (OpenRouter)"


def _calcular_costo_openrouter(usage: dict) -> float:
    p_tok = usage.get("prompt_tokens", 0)
    c_tok = usage.get("completion_tokens", 0)
    return (p_tok * GEMINI_PRICE_IN_PER_1M / 1e6) + (c_tok * GEMINI_PRICE_OUT_PER_1M / 1e6)


def _llamar_vision_api(messages, temperature=0.0, max_tokens=1024):
    """
    Llama al proveedor de visión configurado.
    Returns: (content_str, costo_usd, error_str|None, meta_dict)
    """
    cfg = _vision_config()

    if cfg["proveedor"] == "mimo":
        timeout_vision = int(os.getenv("TIMEOUT_VISION", "120"))
        result, err = call_mimo_chat(
            messages,
            model=cfg["modelo"],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            thinking=cfg["thinking"],
            timeout=timeout_vision,
        )
        if err:
            return "", 0.0, err, {}
        content, _ = mimo_extract_content(result)
        r_tok = mimo_reasoning_tokens(result)
        if r_tok:
            print(f"    [MiMo] ADVERTENCIA: reasoning_tokens={r_tok} con thinking={cfg['thinking']}")
        usage = result.get("usage", {})
        meta = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": r_tok,
        }
        return content, mimo_estimate_cost(result), None, meta

    if not OPENROUTER_API_KEY:
        return "", 0.0, "OPENROUTER_API_KEY no configurada", {}

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": cfg["modelo"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        timeout_vision = int(os.getenv("TIMEOUT_VISION", "120"))
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_vision) as response:
            result = json.loads(response.read().decode())
            usage = result.get("usage", {})
            content = result["choices"][0]["message"]["content"].strip()
            meta = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": 0,
            }
            return content, _calcular_costo_openrouter(usage), None, meta
    except Exception as e:
        return "", 0.0, str(e), {}

def obtener_taxonomias_estrictas():
    """Versión que solo usa cache local - NO intenta conectar a SQL"""
    cache_path = os.getenv("TAXONOMIAS_CACHE", "scratch/taxonomias_local.txt")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                tax_str = f.read()
                print(f"[✓] Taxonomías cargadas desde cache local ({len(tax_str)} chars)")
                return tax_str
        except Exception as e:
            print(f"[⚠] Error leyendo cache de taxonomías: {e}")
            return ""

    print(f"[⚠] ADVERTENCIA: No hay cache de taxonomías en {cache_path}")
    return ""

def calcular_score_calidad(atrib):
    """Calcula score de calidad basado en atributos completados.
    Distribución sobre 100 puntos (sin segmento_etario, que se asigna en Python)."""
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

    if atrib.get('principio_activo'): score += 17
    if atrib.get('concentracion'): score += 17
    if atrib.get('forma_farmaceutica'): score += 18
    if tiene_cant: score += 12
    if atrib.get('contenido_neto'): score += 6
    if atrib.get('origen'): score += 12
    if atrib.get('fabricante'): score += 6
    if atrib.get('marca'): score += 6
    if atrib.get('codigo_atc'): score += 6

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

# ---------------------------------------------------------------------------
# Mapeo ATC profundo → segmento etario (tabla exhaustiva)
# Prefijos de nivel 3 (4 chars) que son inherentemente pediátricos/neonatales.
# Todo lo demás se asigna como ADULTO por defecto.
# ---------------------------------------------------------------------------
_ATC_PEDIATRICO = {
    # Vacunas (J07) — mayoría pediátricas
    'J07A', 'J07B', 'J07C', 'J07X',
    # Antiparasitarios (P01) — uso frecuente pediátrico
    'P01A', 'P01B', 'P01C',
    # Antidiarreicos (A07) — rehidratación pediátrica
    'A07A', 'A07B', 'A07C', 'A07D', 'A07E', 'A07F', 'A07X',
    # Fórmulas infantiles y alimentos (A09/A12 pediátricos)
    'A09A',
    # Vitaminas pediátricas
    'A11A', 'A11C',
    # Suplementos minerales pediátricos
    'A12A', 'A12B', 'A12C',
    # Antihelmínticos (P02) — uso frecuente pediátrico
    'P02B', 'P02C', 'P02D',
    # Antifúngicos sistémicos (J02) — algunos pediátricos
    'J02A',
}

_ATC_NEONATAL = {
    # Sustancias generales neonatales
    'V03A', 'V03B',
    # Surfactantes pulmonares (R07) — neonatal
    'R07A',
    # Soluciones de perfusión neonatales
    'B05A', 'B05B', 'B05C', 'B05D', 'B05X', 'B05Z',
}

def deducir_segmento_etario(codigo_atc_profundo):
    """Deduce segmento etario a partir del código ATC profundo (nivel 4/5).
    Si el prefijo de nivel 3 está en las tablas pediátricas/neonatales,
    devuelve el segmento correspondiente. Si no, devuelve 'ADULTO'.
    Si no hay código ATC, devuelve None."""
    if not codigo_atc_profundo:
        return None
    prefijo3 = codigo_atc_profundo[:4].upper()
    if prefijo3 in _ATC_NEONATAL:
        return "NEONATAL"
    if prefijo3 in _ATC_PEDIATRICO:
        return "PEDIATRICO"
    return "ADULTO"

def extract_json_from_content(content):
    """
    Extrae JSON del contenido de respuesta del modelo.

    Modelos con razonamiento profundo (DeepSeek reasoning_effort=max, GLM-4.7
    thinking mode) pueden envolver el JSON en bloques <analisis_clinico>,
    markdown ```json, o dejarlo pelado tras texto de razonamiento. Esta función
    busca el array/objeto JSON real en orden de especificidad descendente.
    """
    if not content:
        raise ValueError("No valid JSON found in response content")
    content = content.strip()

    # 1) Bloque markdown explicito ```json ... ``` o ``` ... ```
    for prefix in ["```json", "```"]:
        if prefix in content:
            parts = content.split(prefix)
            for part in parts[1:]:
                subpart = part.split("```")[0].strip()
                try:
                    return json.loads(subpart)
                except Exception:
                    pass

    # 2) Intentar parseo directo (content es JSON puro)
    try:
        return json.loads(content)
    except Exception:
        pass

    # 3) Buscar el array JSON real: patron [ seguido de { (con whitespace).
    #    Esto evita confundirse con corchetes sueltos en texto de razonamiento.
    array_match = re.search(r'\[\s*\{', content)
    if array_match:
        start = array_match.start()
        # Tomar desde el [ hasta el ultimo ] del content (el array es lo ultimo)
        end = content.rfind(']')
        if end > start:
            candidate = content[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        # Fallback: raw_decode desde el [
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(content[start:])
            return obj
        except Exception:
            pass

    # 4) Buscar objeto JSON unico { ... } (ultimo { al inicio de un objeto)
    obj_match = re.search(r'\{[\s"]*', content)
    if obj_match:
        start = obj_match.start()
        end = content.rfind('}')
        if end > start:
            try:
                return json.loads(content[start:end + 1])
            except Exception:
                pass

    raise ValueError("No valid JSON found in response content")

def _normalizar_texto(s: str) -> str:
    """ASCII-fold + lower + colapsar espacios, para comparación semántica tolerante."""
    if not s:
        return ""
    import unicodedata
    nf = unicodedata.normalize("NFKD", s)
    return re.sub(r"\s+", " ", "".join(c for c in nf if not unicodedata.combining(c))).strip().lower()


def _extraer_dominio(url: str) -> str:
    """Extrae el dominio raíz de una URL para deduplicación por fuente independiente."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        # Quitar www. y subdominios CDN (cdn., static.) para agrupar por sitio.
        for pref in ("www.", "cdn.", "static.", "img.", "images."):
            if host.startswith(pref):
                host = host[len(pref):]
        return host
    except Exception:
        return ""


def filtrar_imagenes_legibles(imagenes_b64, descripcion_producto):
    """Pre-filtro de imágenes con el modelo de visión configurado."""
    if not imagenes_b64:
        return [], [], 0.0

    cfg = _vision_config()
    prompt = f"Se te dará la descripción de un producto comercial ('{descripcion_producto}') y una imagen. ¿La imagen parece corresponder al producto de la descripción? Si la imagen NO tiene relación alguna o es puro ruido/error, responde únicamente con el número 0. Si SÍ corresponde, califica la legibilidad del 1 al 5. Responde ÚNICAMENTE con el número entero (0, 1, 2, 3, 4 o 5), sin ningún texto adicional."

    costo_total = 0.0
    fotos_aprobadas = []
    fotos_a_guardar = []
    imagenes_unicas = list(dict.fromkeys(imagenes_b64))
    umbral = cfg["umbral"]
    max_aprobadas = cfg["max_ocr"]

    for url_img in imagenes_unicas[: cfg["max_prefiltro"]]:
        if len(fotos_aprobadas) >= max_aprobadas:
            break

        try:
            if url_img.startswith("data:image"):
                b64_uri = url_img
            else:
                headers_img = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                timeout_red = int(os.getenv("TIMEOUT_RED", "15"))
                img_res = requests.get(url_img, headers=headers_img, timeout=timeout_red)
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

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": b64_uri}},
            ],
        }]
        try:
            content, costo_llamada, err, _meta = _llamar_vision_api(messages, temperature=0.0, max_tokens=16)
            costo_total += costo_llamada
            if err:
                print(f"    [Pre-Filtro] Error evaluando imagen: {err}")
                continue

            match = re.search(r'\d+', content)
            if match:
                calificacion = int(match.group())
                if calificacion > 0:
                    fotos_a_guardar.append({"url_imagen": url_img, "score": calificacion, "b64_uri": b64_uri})
                    if calificacion >= umbral:
                        fotos_aprobadas.append(b64_uri)
                        print(f"    [Pre-Filtro] Foto Aprobada (Puntaje: {calificacion})")
                    else:
                        print(f"    [Pre-Filtro] Foto Salvada/Reserva (Puntaje: {calificacion})")
                else:
                    print(f"    [Pre-Filtro] Foto Descartada (Puntaje: 0)")
            else:
                print(f"    [Pre-Filtro] Respuesta inesperada: {content}")
        except Exception as e:
            print(f"    [Pre-Filtro] Error evaluando imagen: {e}")
            continue

    return fotos_aprobadas, fotos_a_guardar, costo_total

def transcribir_imagenes_vision(fotos_aprobadas, desc_producto):
    """OCR farmacéutico con el modelo de visión configurado."""
    if not fotos_aprobadas:
        return [], 0.0

    cfg = _vision_config()
    ocr_prompt = (
        f"Eres un extractor OCR farmacéutico. Se te muestra la imagen de un producto: '{desc_producto}'.\n"
        "Extrae TODO el texto visible: nombre, laboratorio, principio activo, concentración, forma farmacéutica, "
        "contenido neto, presentación, país de origen, registro sanitario, lote, vencimiento.\n\n"
        "Si la imagen es ilegible o no tiene texto útil, responde EXACTAMENTE: IMAGEN SIN TEXTO ÚTIL\n\n"
        "Responde SOLO con el texto extraído, sin comentarios adicionales."
    )
    costo_ocr = 0.0
    transcripciones = []
    tag = "MiMo" if cfg["proveedor"] == "mimo" else "Vision"

    for idx, b64_uri in enumerate(fotos_aprobadas[: cfg["max_ocr"]], 1):
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": ocr_prompt},
                {"type": "image_url", "image_url": {"url": b64_uri}},
            ],
        }]
        try:
            text_out, costo_llamada, err, _meta = _llamar_vision_api(messages, temperature=0.0, max_tokens=4096)
            costo_ocr += costo_llamada
            if err:
                print(f"    [OCR {tag}] Error en imagen {idx}: {err}")
                continue
            if text_out and "IMAGEN SIN TEXTO ÚTIL" not in text_out:
                transcripciones.append(f"[Imagen {idx}]: {text_out}")
                print(f"    [OCR {tag}] Imagen {idx}: {len(text_out)} chars extraídos")
            else:
                print(f"    [OCR {tag}] Imagen {idx}: Sin texto útil")
        except Exception as e:
            print(f"    [OCR {tag}] Error en imagen {idx}: {e}")

    return transcripciones, costo_ocr


# Alias legacy
transcribir_imagenes_gemini = transcribir_imagenes_vision

def llamar_glm_47_api(prompt_text, model_id, max_tokens=4000):
    """
    Llamada DIRECTA a GLM-4.7 via API de Z.ai (GLM Coding Plan).
    NO usa OpenRouter. Devuelve (result_dict, error_str).
    Temperature y top_p vienen del .env (GLM-4.7 recomienda 0.7 / 0.95).
    """
    max_tokens = int(os.getenv("GLM_MAX_TOKENS", str(max_tokens)))
    temperature = float(os.getenv("GLM_TEMPERATURE", "0.7"))
    top_p = float(os.getenv("GLM_TOP_P", "0.95"))
    timeout_texto = int(os.getenv("TIMEOUT_TEXTO", "300"))
    return call_glm(
        prompt=prompt_text,
        model=model_id,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        timeout=timeout_texto,
    )


def llamar_llm_texto(prompt_text, max_tokens=4000):
    """
    Despacha la consolidación al proveedor de texto configurado.

    IA_PROVEEDOR:
      - "glm"      (default): GLM-4.7 vía Z.ai Coding Plan.
      - "deepseek": DeepSeek V4 Flash vía api.deepseek.com (nativo, no OpenRouter).

    Devuelve (result_dict, error_str, label_modelo).
    """
    provider = os.getenv("IA_PROVEEDOR", "glm").lower()
    if provider == "deepseek":
        if call_deepseek is None:
            return None, "deepseek_client no disponible (import fallido)", None
        # DeepSeek V4 thinking mode: max_tokens amplio (reasoning + JSON).
        # temperature/top_p son NO-OP en thinking mode — no se pasan.
        mt = max_tokens or int(os.getenv("DEEPSEEK_MAX_TOKENS", "16384"))
        timeout_texto = int(os.getenv("TIMEOUT_TEXTO", "300"))
        result, err = call_deepseek(
            prompt=prompt_text,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            max_tokens=mt,
            reasoning_effort=os.getenv("DEEPSEEK_REASONING_EFFORT", "max"),
            timeout=timeout_texto,
        )
        return result, err, "DeepSeek V4 Flash"
    # default: GLM
    result, err = llamar_glm_47_api(prompt_text, GLM_MODEL, max_tokens=max_tokens)
    return result, err, "GLM-4.7"

def procesar_producto_batch1(context_json_str, taxonomias_existentes, imagenes_b64, desc_producto):
    """Procesa UN producto con GLM-4.7 (Batch=1)"""

    # Métricas
    metricas = {
        "llamadas_gemini_prefiltro": 0,
        "llamadas_gemini_ocr": 0,
        "llamadas_glm": 0,
        "costo_gemini": 0.0,
        "costo_glm": 0.0,
        "tiempo_inicio": time.time(),
        "errores_json": 0,
        "errores_api": []
    }

    vision_activa = os.getenv("VISION_ACTIVA", "1") == "1"
    if not vision_activa:
        imagenes_b64 = []

    vcfg = _vision_config()
    vlabel = _vision_label(vcfg)

    # Paso 1: Pre-filtro de imágenes
    log(f"  [1/3] Pre-filtro de imágenes ({vlabel})...")
    fotos_aprobadas, fotos_a_guardar, costo_vision = filtrar_imagenes_legibles(imagenes_b64, desc_producto)
    metricas["llamadas_gemini_prefiltro"] = len(imagenes_b64[: vcfg["max_prefiltro"]]) if imagenes_b64 else 0
    metricas["costo_gemini"] += costo_vision

    # Paso 2: OCR
    log(f"  [2/3] OCR de imágenes ({vlabel})...")
    transcripciones = []
    costo_ocr = 0.0
    if fotos_aprobadas:
        transcripciones, costo_ocr = transcribir_imagenes_vision(fotos_aprobadas, desc_producto)
        metricas["llamadas_gemini_ocr"] = len(fotos_aprobadas[: vcfg["max_ocr"]])
        metricas["costo_gemini"] += costo_ocr

    ocr_tag = "MiMo" if vcfg["proveedor"] == "mimo" else "Gemini Flash"

    # Construir nota_vision
    if not fotos_aprobadas:
        nota_vision = "[Nota: No se logró conseguir ninguna imagen de calidad suficiente (legibilidad < 3). Procede usando únicamente los datos de texto web.]"
    elif transcripciones:
        texto_ocr = "\n".join(transcripciones)
        nota_vision = (
            f"[Nota: Se procesaron {len(fotos_aprobadas)} imagen(es) pre-aprobadas mediante OCR ({ocr_tag}). "
            f"A continuación el texto extraído de las imágenes del producto:]\n\n"
            f"--- INICIO TRANSCRIPCIÓN OCR ---\n{texto_ocr}\n--- FIN TRANSCRIPCIÓN OCR ---"
        )
    else:
        nota_vision = "[Nota: Se encontraron imágenes pero ninguna contenía texto farmacéutico legible. Procede usando únicamente los datos de texto web.]"

    # Paso 3: Consolidación LLM
    _proveedor_txt = os.getenv("IA_PROVEEDOR", "glm").lower()
    _modelo_label = "DeepSeek V4 Flash" if _proveedor_txt == "deepseek" else "GLM-4.7"
    log(f"  [3/3] Consolidación con {_modelo_label}...")

    # Cargar prompt (ruta desde .env → PROMPT_ARCHIVO / PROMPT_ARCHIVO)
    prompt_template_path = os.getenv("PROMPT_ARCHIVO", "prompt_agente_v3_solidificado_final.txt")
    with open(prompt_template_path, "r", encoding="utf-8") as f_prompt:
        prompt_template = f_prompt.read()

    prompt = prompt_template.replace(
        "{taxonomias_existentes}", taxonomias_existentes
    ).replace(
        "{context_json_str}", context_json_str
    ).replace(
        "{nota_vision}", nota_vision
    )

    # Llamada al LLM de texto (GLM-4.7 o DeepSeek según IA_PROVEEDOR)
    metricas["llamadas_glm"] = 1
    # GLM usa 4000; DeepSeek con reasoning=max necesita budget amplio (lo decide el wrapper).
    provider_txt_cfg = os.getenv("IA_PROVEEDOR", "glm").lower()
    mt_call = None if provider_txt_cfg == "deepseek" else 4000
    result_glm, error_glm, lbl_modelo = llamar_llm_texto(prompt, max_tokens=mt_call)

    if error_glm:
        metricas["errores_api"].append(f"{lbl_modelo or 'LLM'} API Error: {error_glm}")
        metricas["tiempo_total"] = time.time() - metricas["tiempo_inicio"]
        return None, metricas, None, fotos_a_guardar

    # Procesar respuesta del LLM (protocolo OpenAI-compatible: content +
    # reasoning_content). Si content es None por agotamiento de tokens en el
    # razonamiento, usamos reasoning_content como fallback.
    provider_txt = os.getenv("IA_PROVEEDOR", "glm").lower()
    if provider_txt == "deepseek":
        content, reasoning = deepseek_extract_content(result_glm)
        costo_txt = deepseek_estimate_cost(result_glm)
    else:
        content, reasoning = extract_content(result_glm)
        costo_txt = estimate_cost(result_glm)
    if not content and reasoning:
        # fallback: el razonamiento puede contener el JSON al final
        content = reasoning
    content = content or ''

    # Costo equivalente
    metricas["costo_glm"] = costo_txt

    # Trazabilidad LLM (persistida por el orquestador a OrquestadorLLMLog).
    # Capturamos: prompt final, reasoning separado, tokens y metadata del modelo.
    usage = (result_glm.get("usage") or {}) if isinstance(result_glm, dict) else {}
    metricas["prompt_enviado"]      = prompt[:50000]                  # str (template final con contexto)
    metricas["reasoning_content"]   = (reasoning or "")[:50000]       # str (chain-of-thought)
    metricas["prompt_tokens"]       = usage.get("prompt_tokens", 0) or 0
    metricas["completion_tokens"]   = usage.get("completion_tokens", 0) or 0
    metricas["reasoning_tokens"]    = (
        (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0
    )
    metricas["modelo_texto"]        = lbl_modelo or os.getenv("IA_MODELO", "")
    metricas["prompt_archivo"]      = prompt_template_path
    metricas["temperatura"]         = float(os.getenv("IA_TEMPERATURE", "0"))
    metricas["num_fuentes"]         = len(fotos_a_guardar)  # placeholder; orquestador sobreescribe con len(fuentes)
    metricas["num_imagenes"]        = len(imagenes_b64) if isinstance(imagenes_b64, list) else 0
    metricas["num_imagenes_aprob"]  = len(fotos_a_guardar)

    # Parsear JSON
    try:
        parsed_json = extract_json_from_content(content)
        metricas["tiempo_total"] = time.time() - metricas["tiempo_inicio"]
        return parsed_json, metricas, content, fotos_a_guardar
    except Exception as e:
        metricas["errores_json"] = 1
        metricas["errores_api"].append(f"JSON Parse Error: {str(e)}")
        metricas["tiempo_total"] = time.time() - metricas["tiempo_inicio"]
        return None, metricas, content, fotos_a_guardar

def main(input_path="scratch/eval_comparativa_10.json", output_path="scratch/comparativa_batch1.json"):
    vcfg = _vision_config()
    vlabel = _vision_label(vcfg)
    print("="*80)
    print("PIPELINE LOCAL | visión + consolidación LLM")
    print("="*80)
    print(f"  Visión       : {vlabel}")
    if vcfg["proveedor"] == "mimo":
        print(f"  MiMo URL     : {os.getenv('MIMO_API_URL', 'https://token-plan-sgp.xiaomimimo.com/v1')}")
    print(f"  GLM endpoint : https://api.z.ai/api/coding/paas/v4/chat/completions")
    print(f"  GLM modelo   : {GLM_MODEL} (GLM Coding Plan)")
    print()

    if not os.path.exists(input_path):
        print(f"Error: No se encuentra {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        productos = json.load(f)

    print(f"Productos a procesar: {len(productos)}")
    print()

    # Cargar taxonomías
    taxonomias_str = obtener_taxonomias_estrictas()

    # Resultados
    resultados_batch1 = {
        "configuracion": {
            "batch_size": 1,
            "modelo_consolidacion": _modelo_label,
            "modelo_vision": vlabel,
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "metricas_globales": {
            "total_llamadas_gemini": 0,
            "total_llamadas_glm": 0,
            "costo_total_gemini": 0.0,
            "costo_total_glm": 0.0,
            "costo_total": 0.0,
            "tiempo_total": 0.0,
            "productos_exitosos": 0,
            "productos_fallidos": 0,
            "total_errores_json": 0
        },
        "resultados_por_producto": {}
    }

    tiempo_inicio_global = time.time()

    for idx, item in enumerate(productos, 1):
        ean = item["ean"]
        desc = item["descripcion"]
        fuentes_web = item["fuentes_web"]
        imagenes_b64 = item["imagenes_b64"]

        print(f"\n{'='*80}")
        print(f"[{idx}/{len(productos)}] EAN {ean} - {desc}")
        print(f"{'='*80}")
        log_evento("producto_inicio", idx=idx, total=len(productos), ean=ean, descripcion=desc[:80])

        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]

        # Procesar producto
        parsed_json, metricas, raw_content, fotos_guardadas = procesar_producto_batch1(
            json.dumps(context_block, indent=2),
            taxonomias_str,
            imagenes_b64,
            desc
        )

        # Guardar resultado
        resultado_producto = {
            "descripcion": desc,
            "metricas": metricas,
            "exito": parsed_json is not None
        }

        if parsed_json:
            if isinstance(parsed_json, list) and len(parsed_json) > 0:
                atrib = parsed_json[0].get('atributos_nuevos_consolidados', {})
            elif isinstance(parsed_json, dict):
                atrib = parsed_json.get('atributos_nuevos_consolidados', {})
            else:
                atrib = {}

            if atrib:
                score = calcular_score_calidad(atrib)
                atrib['segmento_etario'] = deducir_segmento_etario(atrib.get('codigo_atc_profundo'))
                # Capa 2 — post-validación determinista: si fabricante/marca están marcados
                # como baja confianza (conflicto imagen↔texto u otra razón), el nivel global
                # se capa a máximo 3. Backstop del fallo donde GLM documenta fabricante=3
                # en confianza_razonamiento pero emite confianza_nivel=5.
                baja = set(atrib.get('atributos_baja_confianza') or [])
                if baja & {'fabricante', 'marca'}:
                    nivel_prev = atrib.get('confianza_nivel')
                    try:
                        atrib['confianza_nivel'] = min(int(nivel_prev or 5), 3)
                    except (TypeError, ValueError):
                        atrib['confianza_nivel'] = 3
                    if not atrib.get('alertas_auditoria'):
                        atrib['alertas_auditoria'] = (
                            "fabricante/marca en atributos_baja_confianza: "
                            f"confianza_nivel capada de {nivel_prev} a {atrib['confianza_nivel']} por post-validación"
                        )
                resultado_producto["atributos"] = atrib
                resultado_producto["score"] = score
                resultados_batch1["metricas_globales"]["productos_exitosos"] += 1
            else:
                resultado_producto["atributos"] = None
                resultado_producto["score"] = 0
                resultados_batch1["metricas_globales"]["productos_fallidos"] += 1
        else:
            resultado_producto["atributos"] = None
            resultado_producto["score"] = 0
            resultado_producto["error"] = "Fallo en procesamiento"
            resultado_producto["raw_content"] = raw_content
            resultados_batch1["metricas_globales"]["productos_fallidos"] += 1

        resultado_producto["fotos_a_guardar"] = fotos_guardadas
        resultados_batch1["resultados_por_producto"][ean] = resultado_producto

        # Actualizar métricas globales
        resultados_batch1["metricas_globales"]["total_llamadas_gemini"] += metricas["llamadas_gemini_prefiltro"] + metricas["llamadas_gemini_ocr"]
        resultados_batch1["metricas_globales"]["total_llamadas_glm"] += metricas["llamadas_glm"]
        resultados_batch1["metricas_globales"]["costo_total_gemini"] += metricas["costo_gemini"]
        resultados_batch1["metricas_globales"]["costo_total_glm"] += metricas["costo_glm"]
        resultados_batch1["metricas_globales"]["total_errores_json"] += metricas["errores_json"]

        print(f"  ✓ Procesado en {metricas['tiempo_total']:.2f}s | Costo: ${metricas['costo_gemini'] + metricas['costo_glm']:.6f}")

        # Logging estructurado del producto
        costo_prod = metricas['costo_gemini'] + metricas['costo_glm']
        atrib_log = resultado_producto.get("atributos") or {}
        log_producto(
            ean=ean,
            descripcion=desc,
            score=resultado_producto.get("score"),
            costo=costo_prod,
            tiempo=metricas['tiempo_total'],
            exito=resultado_producto.get("exito", False),
            atributos=atrib_log,
            error=resultado_producto.get("error"),
            modelo=os.getenv("GLM_MODEL", ""),
            fuentes_web=len(fuentes_web),
            imagenes=len(imagenes_b64),
            ocr_aprobadas=metricas.get("llamadas_gemini_ocr", 0),
        )

    # Calcular métricas globales finales
    resultados_batch1["metricas_globales"]["tiempo_total"] = time.time() - tiempo_inicio_global
    resultados_batch1["metricas_globales"]["costo_total"] = (
        resultados_batch1["metricas_globales"]["costo_total_gemini"] +
        resultados_batch1["metricas_globales"]["costo_total_glm"]
    )

    # Guardar resultados
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados_batch1, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✓ BATCH=1 COMPLETADO!")
    print(f"  - Resultados guardados: {output_path}")
    print(f"  - Productos exitosos: {resultados_batch1['metricas_globales']['productos_exitosos']}/{len(productos)}")

    # Resumen estructurado al logger
    mg = resultados_batch1["metricas_globales"]
    log_resumen({
        "productos_exitosos": mg["productos_exitosos"],
        "productos_fallidos": mg["productos_fallidos"],
        "tiempo_total": mg["tiempo_total"],
        "costo_total": mg["costo_total"],
        "total_llamadas_vision": mg["total_llamadas_gemini"],
        "total_llamadas_texto": mg["total_llamadas_glm"],
        "total_errores_json": mg["total_errores_json"],
        "resultados_archivo": output_path,
    })

if __name__ == "__main__":
    main()