"""
Cliente Xiaomi MiMo Token Plan (protocolo OpenAI-compatible).

Documentación:
  - https://mimo.mi.com/docs/en-US/tokenplan/Token%20Plan/quick-access
  - https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/deep-thinking

Token Plan (API Key tp-xxxxx):
  - Base URL SGP: https://token-plan-sgp.xiaomimimo.com/v1
  - Auth header: api-key (NO Bearer)
  - Thinking OFF: {"thinking": {"type": "disabled"}}
  - Modelo multimodal visión: mimo-v2.5
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

try:
    from synapse_cred import load_synapse_credentials

    load_synapse_credentials()
except Exception:
    pass

MIMO_API_KEY = os.getenv("MIMO_API_KEY")
MIMO_API_URL = os.getenv("MIMO_API_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")
MIMO_THINKING = os.getenv("MIMO_THINKING", "disabled")


def get_chat_endpoint(base_url: Optional[str] = None) -> str:
    endpoint = (base_url or MIMO_API_URL).rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    return endpoint


def call_mimo_chat(
    messages: list,
    *,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_completion_tokens: int = 4096,
    thinking: Optional[str] = None,
    timeout: int = 120,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Llama a MiMo Token Plan vía /chat/completions.

    Returns:
        (result_dict, error_str)
    """
    key = api_key or MIMO_API_KEY
    if not key:
        return None, "MIMO_API_KEY no configurada"

    thinking_type = (thinking or MIMO_THINKING or "disabled").lower()
    if thinking_type not in ("disabled", "enabled"):
        thinking_type = "disabled"

    payload: Dict[str, Any] = {
        "model": model or MIMO_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "thinking": {"type": thinking_type},
    }

    headers = {
        "api-key": key,
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        get_chat_endpoint(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return None, f"HTTP {e.code}: {body[:500]}"
    except Exception as e:
        return None, str(e)


def extract_content(result: Dict[str, Any]) -> Tuple[str, str]:
    """Devuelve (content, reasoning_content) del primer choice."""
    if not result.get("choices"):
        return "", ""
    message = result["choices"][0].get("message") or {}
    return (message.get("content") or "").strip(), (message.get("reasoning_content") or "").strip()


def estimate_cost(result: Dict[str, Any]) -> float:
    """
    Token Plan es suscripción flat-rate; devolvemos 0.0.
    Conserva tokens en usage para métricas.
    """
    return 0.0


def reasoning_tokens(result: Dict[str, Any]) -> int:
    usage = result.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return int(details.get("reasoning_tokens") or 0)
