"""
Cliente Z.ai para el modelo GLM-4.7 (GLM Coding Plan).

Endpoint oficial (GLM Coding Plan, protocolo OpenAI-compatible):
    https://api.z.ai/api/coding/paas/v4/chat/completions

Documentacion:
    - https://docs.z.ai/devpack/tool/others
    - https://docs.z.ai/guides/develop/http/introduction

Notas importantes:
    * El plan GLM Coding Plan SI tiene saldo disponible. El error anterior
      "Insufficient balance or no resource package" se producia porque los
      scripts llamaban a la URL base sin el path `/chat/completions`, lo que
      hacia que la peticion llegara al endpoint generico (no al plan Coding).
    * La API Key de Z.ai tiene formato `<id>.<secret>` y se usa tal cual
      con Bearer authentication. NO hace falta generar JWT salvo que se
      quiera mayor seguridad (no es el caso del Coding Plan).
    * GLM-4.7 activa el modo razonamiento por defecto. La respuesta trae
      `content` (salida final) y `reasoning_content` (cadena de pensamiento,
      no cobrada como output pero cuenta como reasoning_tokens).
"""
import json
import os
import urllib.error
import urllib.request
from typing import Optional, Tuple, Dict, Any

try:
    from synapse_cred import load_synapse_credentials
    load_synapse_credentials()
except Exception:
    pass

GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_BASE_URL = os.getenv("GLM_API_URL", "https://api.z.ai/api/coding/paas/v4")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4.7")

# Precios publicos aprox de GLM-4.7 (USD por 1M tokens).
# El Coding Plan es flat-rate mensual, pero dejamos el calculo para
# reportar el "costo equivalente" por comparacion con otros modelos.
GLM_PRICE_IN_PER_1M = 0.50
GLM_PRICE_OUT_PER_1M = 2.00
# Context Caching de Z.ai: los tokens cacheados se cobran a ~50% del input.
# Se reportan en usage.prompt_tokens_details.cached_tokens.
# https://docs.z.ai/guides/capabilities/cache
GLM_PRICE_CACHE_HIT_PER_1M = 0.25


def get_chat_endpoint(base_url: str = GLM_BASE_URL) -> str:
    """Devuelve la URL completa del recurso chat/completions."""
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    return endpoint


def call_glm(
    prompt: str,
    *,
    model: str = GLM_MODEL,
    system_prompt: Optional[str] = None,
    messages: Optional[list] = None,
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_tokens: int = 4000,
    timeout: int = 120,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Llama a GLM (Z.ai Coding Plan) con protocolo OpenAI-compatible.

    Args:
        prompt: Texto del usuario (se ignora si `messages` esta dado).
        system_prompt: Mensaje system opcional (se ignora si `messages` esta dado).
        messages: Lista de mensajes completa. Si se da, tiene prioridad.
        model: ID del modelo (por defecto glm-4.7).
        temperature, top_p, max_tokens: Parametros de sampling.
        timeout: Timeout HTTP en segundos.
        api_key, base_url: Sobrescribir valores de entorno.

    Returns:
        (result_dict, error_str). Si todo va bien, error_str es None.
    """
    key = api_key or GLM_API_KEY
    if not key:
        return None, "GLM_API_KEY no esta definido en el entorno."

    endpoint = get_chat_endpoint(base_url or GLM_BASE_URL)

    if messages is None:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Language": "en-US,en",
    }

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload), None
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return None, f"HTTP {e.code} {e.reason}: {err_body}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def extract_content(result: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae (content, reasoning_content) de la respuesta de Z.ai.
    GLM-4.7 puede devolver content=None si agota tokens en el razonamiento;
    en ese caso devolvemos reasoning_content como fallback.
    """
    if not result or "choices" not in result:
        return None, None
    try:
        msg = result["choices"][0]["message"]
    except Exception:
        return None, None
    content = msg.get("content")
    reasoning = msg.get("reasoning_content") or msg.get("reasoning")
    return content, reasoning


def estimate_cost(result: Dict[str, Any],
                  price_in: float = GLM_PRICE_IN_PER_1M,
                  price_out: float = GLM_PRICE_OUT_PER_1M,
                  price_cache_hit: float = GLM_PRICE_CACHE_HIT_PER_1M) -> float:
    """Costo USD aproximado a partir de usage. Coding Plan es flat-rate;
    este numero es solo un 'costo equivalente' para comparar modelos.

    Refleja el descuento del Context Caching de Z.ai: los tokens en
    `usage.prompt_tokens_details.cached_tokens` se cobran a ~50% del input; el
    resto del input a precio pleno. Si la API no reporta cached_tokens, cae al
    cálculo legacy con prompt_tokens entero a precio pleno.
    """
    if not result:
        return 0.0
    usage = result.get("usage", {}) or {}
    c_tok = usage.get("completion_tokens", 0) or 0
    p_tok = usage.get("prompt_tokens", 0) or 0

    details = usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens") or 0
    if cached:
        fresh = max(p_tok - cached, 0)
        return (cached * price_cache_hit / 1e6
                + fresh * price_in / 1e6
                + c_tok * price_out / 1e6)

    # Fallback legacy: sin desglose de caché, todo el input a precio pleno.
    # completion_tokens YA incluye reasoning_tokens segun el API de Z.ai.
    return (p_tok * price_in / 1e6) + (c_tok * price_out / 1e6)


if __name__ == "__main__":
    print("Endpoint:", get_chat_endpoint())
    print("Modelo  :", GLM_MODEL)
    result, err = call_glm("Responde solo con: OK", max_tokens=50)
    if err:
        print("[FAIL]", err)
        raise SystemExit(1)
    content, reasoning = extract_content(result)
    print("content :", repr(content))
    print("usage   :", result.get("usage"))
    print("costo $ :", estimate_cost(result))
