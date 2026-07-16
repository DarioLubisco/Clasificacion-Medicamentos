"""
Cliente DeepSeek nativo (api.deepseek.com, protocolo OpenAI-compatible).

Modelos disponibles: deepseek-v4-flash, deepseek-v4-pro.
DeepSeek V4 razona por defecto: la respuesta trae `content` (salida final) y
`reasoning_content` (cadena de pensamiento, cuenta como reasoning_tokens).
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

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# Precios públicos de DeepSeek V4 Flash (USD por 1M tokens).
DEEPSEEK_PRICE_IN_PER_1M = 0.27
DEEPSEEK_PRICE_OUT_PER_1M = 1.10


def get_chat_endpoint(base_url: str = DEEPSEEK_BASE_URL) -> str:
    """Devuelve la URL completa del recurso chat/completions."""
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    return endpoint


def call_deepseek(
    prompt: str,
    *,
    model: str = DEEPSEEK_MODEL,
    system_prompt: Optional[str] = None,
    messages: Optional[list] = None,
    max_tokens: int = 16384,
    reasoning_effort: str = "max",
    thinking_enabled: bool = True,
    timeout: int = 180,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Llama a DeepSeek (api.deepseek.com) con protocolo OpenAI-compatible.

    DeepSeek V4 razona por defecto. El control del razonamiento es:
      - reasoning_effort: "low" | "medium" | "high" | "max" (top-level, NO anidado).
        Mapeo de compatibilidad: low/medium → high; xhigh → max.
        El estándar del proyecto (CONTEXT.md "xhigh") se traduce a "max" aquí.
      - thinking: {"type": "enabled"} activa el thinking mode.

    IMPORTANTE: en thinking mode, `temperature` y `top_p` son NO-OP (la API los
    ignora sin error). NO se envían para evitar ruido de configuración heredada.
    `max_tokens` SÍ es el budget total (reasoning + completion).

    Returns:
        (result_dict, error_str). Si todo va bien, error_str es None.
    """
    key = api_key or DEEPSEEK_API_KEY
    if not key:
        return None, "DEEPSEEK_API_KEY no esta definido en el entorno."

    endpoint = get_chat_endpoint(base_url or DEEPSEEK_BASE_URL)

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
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
    }
    if thinking_enabled:
        body["thinking"] = {"type": "enabled"}

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
    Extrae (content, reasoning_content) de la respuesta de DeepSeek.
    DeepSeek V4 puede devolver content=None si agota tokens en el razonamiento;
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
                  price_in: float = DEEPSEEK_PRICE_IN_PER_1M,
                  price_out: float = DEEPSEEK_PRICE_OUT_PER_1M) -> float:
    """Costo USD a partir de usage."""
    if not result:
        return 0.0
    usage = result.get("usage", {}) or {}
    p_tok = usage.get("prompt_tokens", 0) or 0
    c_tok = usage.get("completion_tokens", 0) or 0
    # completion_tokens YA incluye reasoning_tokens.
    return (p_tok * price_in / 1e6) + (c_tok * price_out / 1e6)


if __name__ == "__main__":
    print("Endpoint:", get_chat_endpoint())
    print("Modelo  :", DEEPSEEK_MODEL)
    result, err = call_deepseek("Responde solo con: OK", max_tokens=50)
    if err:
        print("[FAIL]", err)
        raise SystemExit(1)
    content, reasoning = extract_content(result)
    print("content :", repr(content))
    print("usage   :", result.get("usage"))
    print("costo $ :", estimate_cost(result))
