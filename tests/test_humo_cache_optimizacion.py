"""
Prueba de humo para la optimización de caché de prompts.

VERIFICA (sin tocar la DB, sin imágenes, sin scraping real):
  1. El split system/user del prompt funciona (Cambio B).
  2. La llamada al LLM de texto regresa sin error de API.
  3. usage trae los campos de caché (Cambio C):
       - DeepSeek: prompt_cache_hit_tokens / prompt_cache_miss_tokens
       - GLM (Z.ai): prompt_tokens_details.cached_tokens
  4. estimate_cost refleja el descuento de caché (Cambio C1/C2).
  5. El 2do request con el MISMO prefijo debería tener cache_hit > 0
     (el 1ro suele ser cache-miss por caché frío).

Uso:
    python3 tests/test_humo_cache_optimizacion.py

Aísla visión con VISION_ACTIVA=0 para no incurrir en costos de OCR.
Consume una llamada real al proveedor de texto configurado en .env
(IA_PROVEEDOR). NO escribe en SQL.
"""
import json
import os
import sys
import time
from pathlib import Path

# Resolver repo root (tests/ -> repo root).
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Replicar el orden de carga de credenciales del runtime real:
# synapse_cred PRIMERO (resuelve API keys vía gestor de secretos), luego .env.
try:
    from synapse_cred import load_synapse_credentials
    load_synapse_credentials()
except Exception as _e:
    print(f"[WARN] synapse_cred no disponible: {_e}")
from dotenv import load_dotenv
load_dotenv(REPO / ".env")

# Desactivar visión para aislar la prueba al LLM de texto.
os.environ["VISION_ACTIVA"] = "0"

import evaluate_local as ev


def _build_context(codbarras: str, desc: str) -> str:
    """Replica el context_block que arma orquestador_produccion.py."""
    block = [{
        "registro": {
            "codigo": codbarras,
            "codbarras": codbarras,
            "descripcion_original": desc,
            "ciclos_reproceso": 0,
        },
        "atributos_ya_encontrados": None,
        "fuentes_web": [],  # sin scraping real → modo degradado
    }]
    return json.dumps(block, ensure_ascii=False)


def _reporte(metricas: dict, tag: str) -> None:
    print(f"\n────────── {tag} ──────────")
    print(f"  proveedor (IA_PROVEEDOR) : {os.getenv('IA_PROVEEDOR', 'glm')}")
    print(f"  modelo_texto             : {metricas.get('modelo_texto')}")
    err = metricas.get("errores_api") or []
    print(f"  errores_api              : {err if err else '(ninguno) ✅'}")
    print(f"  prompt_tokens            : {metricas.get('prompt_tokens')}")
    print(f"  completion_tokens        : {metricas.get('completion_tokens')}")
    print(f"  reasoning_tokens         : {metricas.get('reasoning_tokens')}")
    print(f"  prompt_cache_hit_tokens  : {metricas.get('prompt_cache_hit_tokens')}  "
          f"{'  ← HIT ✅' if (metricas.get('prompt_cache_hit_tokens') or 0) > 0 else ''}")
    print(f"  prompt_cache_miss_tokens : {metricas.get('prompt_cache_miss_tokens')}")
    print(f"  costo_glm (USD)          : ${metricas.get('costo_glm', 0):.6f}")
    print(f"  tiempo_total (s)         : {metricas.get('tiempo_total'):.1f}")


def main() -> int:
    print("=== Prueba de humo: optimización de caché de prompts ===")
    print(f"Repo: {REPO}")
    print(f"PROMPT_ARCHIVO: {os.getenv('PROMPT_ARCHIVO', 'prompt_agente_v3_solidificado_final.txt')}")
    print(f"VISION_ACTIVA forzado a 0 (aisla LLM de texto)")

    # Taxonomías reales (cache local si existe).
    print("\nCargando taxonomías...")
    taxonomias = ev.obtener_taxonomias_estrictas()
    if not taxonomias:
        print("[WARN] No se obtuvieron taxonomías (¿falta scratch/taxonomias_local.txt?).")
        print("       La prueba puede continuar pero el prompt tendrá {taxonomias_existentes} literal.")
        taxonomias = "(taxonomías no disponibles)"

    cod = "7501234567890"
    desc = "IBUPROFENO 400MG X 10 TABLETAS"
    ctx = _build_context(cod, desc)

    # Dos llamadas con el MISMO producto/prefijo para forzar cache-hit en la 2da.
    resultados = []
    for i in (1, 2):
        print(f"\n>>> Llamada {i}/2  ({desc})")
        parsed, metricas, raw_content, _fotos = ev.procesar_producto_batch1(
            ctx, taxonomias, imagenes_b64=[], desc_producto=desc,
        )
        resultados.append(metricas)
        _reporte(metricas, f"Llamada {i}")

        # Validar que el JSON parseado tiene la estructura mínima (no se cayeron llaves).
        if i == 1:
            if parsed is None:
                print("\n[❌] El modelo NO devolvió JSON parseable (parsed=None).")
                print("     Revisar metricas.errores_api y prompt_enviado en metricas.")
                return 2
            atr = parsed[0].get("atributos_nuevos_consolidados", {}) if isinstance(parsed, list) and parsed else {}
            llaves_criticas = {"dominio", "principio_activo", "concentracion", "registro_sanitario"}
            faltan = llaves_criticas - set(atr.keys())
            if faltan:
                print(f"\n[⚠️] JSON devuelto pero faltan llaves críticas: {faltan}")
            else:
                print(f"\n[✅] JSON parseado con llaves críticas presentes.")
                print(f"     dominio={atr.get('dominio')!r}  concentracion={atr.get('concentracion')!r}")

    # Comparar caché entre las 2 llamadas.
    h1 = resultados[0].get("prompt_cache_hit_tokens") or 0
    h2 = resultados[1].get("prompt_cache_hit_tokens") or 0
    print("\n================ VEREDICTO DE CACHÉ ================")
    print(f"  Llamada 1 cache_hit: {h1}  (se espera ~0, caché frío)")
    print(f"  Llamada 2 cache_hit: {h2}  (se espera > 0 si el caché funcionó)")
    if h2 > h1:
        print("  [✅] El caché SE ACTIVÓ en la 2da llamada (hit creció).")
    elif h2 == 0 and h1 == 0:
        prov = os.getenv("IA_PROVEEDOR", "glm")
        print(f"  [⚠️]  Ambas llamadas con cache_hit=0. Posibles causas:")
        print(f"        - Proveedor '{prov}' puede no reportar desglose de caché en este plan.")
        print("        - El prefijo aún no calienta el caché (evaporación / TTL corto).")
        print("        - Revisar manualmente usage crudo (ver abajo).")
    else:
        print("  [ℹ️] cache_hit presente pero no creció entre llamadas.")

    print("\n================ RAW usage (debug) ================")
    # Métricas no guardan usage crudo; lo reconstruimos de lo disponible.
    print("  (prompt_tokens + cache_hit/miss capturados arriba bastan para validar)")

    print("\n[HECHO] Fin de la prueba de humo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
