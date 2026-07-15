#!/usr/bin/env python3
"""
Test de GLM-4.7 via API DIRECTA de Z.ai (GLM Coding Plan).

Endpoint oficial (GLM Coding Plan, protocolo OpenAI-compatible):
    https://api.z.ai/api/coding/paas/v4/chat/completions

Documentacion:
    - https://docs.z.ai/devpack/tool/others  (GLM Coding Plan endpoints)
    - https://docs.z.ai/guides/develop/http/introduction

Formato de la API Key de Z.ai:
    Es una cadena de la forma  <id>.<secret>  (p.ej. xxxxx.yyyyy).
    Para uso estandar con Bearer NO hace falta generar JWT; se envia el API
    Key literal en el header `Authorization: Bearer <API_KEY>`.
    El formato JWT solo es necesario si se quiere autenticacion de mayor
    seguridad (ver docs). El Coding Plan funciona con Bearer plano.
"""
import json
import os
import urllib.request
from dotenv import load_dotenv

from synapse_cred import load_synapse_credentials
load_synapse_credentials()

GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_BASE_URL = os.getenv("GLM_API_URL", "https://api.z.ai/api/coding/paas/v4")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4.7")

# IMPORTANTE: la URL base del Coding Plan es solo la raiz; hay que anadir
# el path del recurso. Si el usuario puso la base en GLM_API_URL, normalizamos.
GLM_CHAT_ENDPOINT = GLM_BASE_URL.rstrip("/")
if not GLM_CHAT_ENDPOINT.endswith("/chat/completions"):
    GLM_CHAT_ENDPOINT += "/chat/completions"


def llamar_glm47_direct(prompt, model=GLM_MODEL, temperature=0.2, max_tokens=4000,
                        system_prompt=None, timeout=90):
    """
    Llama a GLM-4.7 via API directa de Z.ai (Coding Plan, OpenAI-compatible).

    Devuelve: (result_dict, error_str)
        result_dict: respuesta JSON completa de la API (None si hay error)
        error_str: mensaje de error (None si todo OK)
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
        "Accept-Language": "en-US,en",
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        GLM_CHAT_ENDPOINT,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main():
    print("=" * 70)
    print("  TEST API DIRECTA Z.ai - GLM-4.7 (GLM Coding Plan)")
    print("=" * 70)
    print(f"Endpoint : {GLM_CHAT_ENDPOINT}")
    print(f"Modelo   : {GLM_MODEL}")
    print(f"API Key  : {GLM_API_KEY[:12]}...{GLM_API_KEY[-6:] if GLM_API_KEY else ''}")
    print()

    prompt = "Responde unicamente con la palabra: EXITO"
    print(f"Prompt: {prompt!r}")
    print("-" * 70)
    print("Llamando a Z.ai (modo razonamiento activado por defecto en GLM-4.7)...")
    print()

    result, error = llamar_glm47_direct(prompt, max_tokens=100)

    if error:
        print(f"[FAIL] Error de API: {error}")
        return 1

    print("[OK] Peticion exitosa (HTTP 200)")
    print()

    # Mostrar usage
    usage = result.get("usage", {})
    print("Usage:")
    print(f"  prompt_tokens          : {usage.get('prompt_tokens', 0)}")
    print(f"  completion_tokens      : {usage.get('completion_tokens', 0)}")
    comp_details = usage.get("completion_tokens_details", {}) or {}
    print(f"  reasoning_tokens       : {comp_details.get('reasoning_tokens', 0)}")
    print(f"  total_tokens           : {usage.get('total_tokens', 0)}")
    print()

    # Mostrar contenido + reasoning
    try:
        msg = result["choices"][0]["message"]
        content = msg.get("content")
        reasoning = msg.get("reasoning_content")
        print(f"content          : {content!r}")
        print(f"reasoning_content: {str(reasoning)[:200]!r}{'...' if reasoning and len(str(reasoning)) > 200 else ''}")
    except Exception as e:
        print(f"[WARN] No se pudo leer choices[0].message: {e}")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])

    print()
    if content and "EXITO" in content.upper():
        print("[PASS] GLM-4.7 responde correctamente via API directa de Z.ai.")
        return 0
    print("[FAIL] Respuesta inesperada.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
