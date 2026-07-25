"""
Experimento A/B: 1 producto por llamada vs 5 productos en una sola llamada.

OBJETIVO: decidir si conviene cambiar la arquitectura de batch=1 (1 producto
por llamada LLM) a batch=5 (5 productos en un solo prompt). Con contexto de 1M
(D/GLM), meter 5 productos (~38K tokens) no degrada por tamaño; el riesgo es
'atención dividida' que afecta la calidad del JSON por producto. Este test lo
resuelve con evidencia.

METODOLOGÍA (controlada, sin tocar la DB):
  1. Scrapea los 5 productos UNA sola vez → mismos datos para ambos modos.
  2. Modo A: 5 llamadas, cada una con context_block de 1 producto.
  3. Modo B: 1 llamada con context_block de 5 productos.
  4. Compara: parse OK, llaves presentes, costo, tiempo, tokens, score, y diff
     de atributos clave entre A y B.

NO persiste, NO UPDATE, NO claim EN_PROCESO. Solo lectura + llamadas LLM.

Uso:
    python3 tests/test_ab_5_por_llamada.py
    python3 tests/test_ab_5_por_llamada.py --productos 3   # versión más corta
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Orden de carga del runtime: synapse_cred primero (resuelve API keys), luego .env.
try:
    from synapse_cred import load_synapse_credentials
    load_synapse_credentials()
except Exception as _e:
    print(f"[WARN] synapse_cred: {_e}")
from dotenv import load_dotenv
load_dotenv(REPO / ".env")

# Visión OFF: aisla la variable que medimos (calidad del LLM de texto). El OCR
# agregaría ruido y costo sin aportar a la comparación A/B.
os.environ["VISION_ACTIVA"] = "0"

import evaluate_local as ev
import orquestador_produccion as op

# --- Los 5 productos reales (de la DB, ABIERTO, EAN-13, descripción clara) ---
PRODUCTOS_TEST = [
    ("7591243815757", "ERILON 0.05% Crema 15g (Desonida)"),
    ("7591243815801", "ERILON 0.1% crema 15g"),
    ("7591243817607", "FEM Ducha Vaginal 135 ml con cánula Biotech"),
    ("7591243817782", "FLENOX Ambroxol 15 mg/5 ml jarabe pediátrico 120 ml"),
    ("7591243817805", "Flenox 15 mg/5 ml jarabe pediátrico con ambroxol, 60 ml."),
]

# Llaves que DEBEN estar presentes en cada JSON de salida (anti key-dropping).
LLAVES_CRITICAS = {
    "dominio", "principio_activo", "concentracion", "forma_farmaceutica",
    "cantidad_presentacion", "contenido_neto", "fabricante", "marca",
    "codigo_atc", "registro_sanitario", "generico", "origen",
}
# Llaves cuyo VALOR comparamos entre A y B (si divergen, la atención dividida
# afectó la extracción).
LLAVES_COMPARAR = {
    "dominio", "principio_activo", "concentracion", "forma_farmaceutica",
    "cantidad_presentacion", "contenido_neto", "fabricante", "marca",
}


def _scrape_todos(productos):
    """Scrapea cada producto una vez. Devuelve lista de dict con datos crudos."""
    out = []
    for cod, desc in productos:
        print(f"  [scrape] {cod} — {desc[:50]}")
        fuentes, imagenes, urls = op.scrape_producto(cod, desc)
        out.append({
            "codbarras": cod,
            "descripcion": desc,
            "fuentes": fuentes,
            "imagenes": imagenes,
            "urls": urls,
        })
    return out


def _extraer_atributos(parsed):
    """Normaliza la salida del LLM a una lista de (codbarras, dict_atributos).

    El JSON de salida incluye 'registro.codbarras' en cada item (ver few-shot
    del prompt), así que mapeamos por codbarras cuando está disponible (robusto
    al desorden). Si no, devolvemos codbarras=None para fallback por orden.
    """
    if parsed is None:
        return []
    items = parsed if isinstance(parsed, list) else [parsed]
    out = []
    for p in items:
        if not isinstance(p, dict):
            continue
        cod = (p.get("registro") or {}).get("codbarras")
        out.append((cod, p.get("atributos_nuevos_consolidados", {})))
    return out


def modo_a_uno_por_llamada(scrapeados, taxonomias):
    """5 llamadas, 1 producto cada una. Devuelve (atributos_por_producto, metricas_agg)."""
    print("\n" + "=" * 70)
    print("MODO A: 1 producto por llamada (5 llamadas)")
    print("=" * 70)
    atributos_por_producto = {}  # codbarras -> dict atributos
    agg = {"costo": 0.0, "tiempo": 0.0, "tokens_in": 0, "tokens_out": 0,
           "cache_hit": 0, "errores_api": 0, "errores_json": 0}
    for d in scrapeados:
        context_block = [{
            "registro": {"codigo": d["codbarras"], "codbarras": d["codbarras"],
                         "descripcion_original": d["descripcion"], "ciclos_reproceso": 0},
            "atributos_ya_encontrados": None,
            "fuentes_web": d["fuentes"],
        }]
        t0 = time.time()
        parsed, metricas, _raw, _fotos = ev.procesar_producto_batch1(
            json.dumps(context_block, ensure_ascii=False), taxonomias,
            imagenes_b64=[], desc_producto=d["descripcion"],
        )
        dt = time.time() - t0
        atrs = _extraer_atributos(parsed)
        # mapear por codbarras (robusto); fallback al primero si no viene
        atr_dict = {}
        for cod, a in atrs:
            if cod == d["codbarras"]:
                atr_dict = a
                break
        if not atr_dict and atrs:
            atr_dict = atrs[0][1]
        atributos_por_producto[d["codbarras"]] = atr_dict
        agg["costo"] += metricas.get("costo_glm", 0) or 0
        agg["tiempo"] += dt
        agg["tokens_in"] += metricas.get("prompt_tokens", 0) or 0
        agg["tokens_out"] += metricas.get("completion_tokens", 0) or 0
        agg["cache_hit"] += metricas.get("prompt_cache_hit_tokens", 0) or 0
        agg["errores_api"] += len(metricas.get("errores_api", []))
        agg["errores_json"] += metricas.get("errores_json", 0) or 0
        print(f"  {d['codbarras']}: parse={'OK' if atrs else 'FALLO'} "
              f"costo=${metricas.get('costo_glm', 0):.5f} {dt:.1f}s "
              f"in={metricas.get('prompt_tokens', 0)} out={metricas.get('completion_tokens', 0)}")
    return atributos_por_producto, agg


def _llamar_llm_texto_directo(prompt_text, system_prompt, max_tokens):
    """Llama al LLM de texto sin pasar por procesar_producto_batch1 (que asume 1)."""
    return ev.llamar_llm_texto(prompt_text, system_prompt=system_prompt, max_tokens=max_tokens)


def modo_b_cinco_en_una(scrapeados, taxonomias):
    """1 llamada con los 5 productos en el context_block."""
    print("\n" + "=" * 70)
    print("MODO B: 5 productos en 1 sola llamada")
    print("=" * 70)
    context_block = []
    for d in scrapeados:
        context_block.append({
            "registro": {"codigo": d["codbarras"], "codbarras": d["codbarras"],
                         "descripcion_original": d["descripcion"], "ciclos_reproceso": 0},
            "atributos_ya_encontrados": None,
            "fuentes_web": d["fuentes"],
        })

    # Armar el prompt igual que procesar_producto_batch1 pero con N registros.
    tpl_path = os.getenv("PROMPT_ARCHIVO", "prompt_agente_v3_solidificado_final.txt")
    tpl = open(tpl_path, encoding="utf-8").read()
    split = "**LOTE A PROCESAR:**"
    idx = tpl.find(split)
    system_prompt = tpl[:idx].replace("{taxonomias_existentes}", taxonomias)
    user_content = (tpl[idx:].replace("{context_json_str}", json.dumps(context_block, ensure_ascii=False))
                                .replace("{nota_vision}", "[Nota: sin imágenes en este test]"))
    provider = os.getenv("IA_PROVEEDOR", "glm").lower()
    mt = None if provider == "deepseek" else int(os.getenv("GLM_MAX_TOKENS", "16384"))

    t0 = time.time()
    result, err, label = _llamar_llm_texto_directo(user_content, system_prompt=system_prompt, max_tokens=mt)
    dt = time.time() - t0
    if err:
        print(f"  ERROR API: {err}")
        return {}, {"costo": 0, "tiempo": dt, "tokens_in": 0, "tokens_out": 0,
                    "cache_hit": 0, "errores_api": 1, "errores_json": 0,
                    "n_productos_devueltos": 0}

    provider2 = os.getenv("IA_PROVEEDOR", "glm").lower()
    if provider2 == "deepseek":
        content, _reasoning = ev.deepseek_extract_content(result)
        costo = ev.deepseek_estimate_cost(result)
    else:
        content, _reasoning = ev.extract_content(result)
        costo = ev.estimate_cost(result)
    usage = (result.get("usage") or {}) if isinstance(result, dict) else {}
    parsed = None
    try:
        parsed = ev.extract_json_from_content(content or "")
    except Exception:
        pass
    atrs = _extraer_atributos(parsed)  # lista de (codbarras, dict_atributos)

    # Mapear por codbarras real (robusto al desorden). El JSON de salida incluye
    # registro.codbarras en cada item (ver few-shot del prompt).
    cods = [d["codbarras"] for d in scrapeados]
    atributos_por_producto = {}
    for cod, a in atrs:
        if cod in cods:
            atributos_por_producto[cod] = a
    # fallback por orden para los que no trajeron codbarras
    mapeados_por_orden = 0
    for i, cod in enumerate(cods):
        if cod not in atributos_por_producto and i < len(atrs):
            atributos_por_producto[cod] = atrs[i][1]
            mapeados_por_orden += 1
    for cod in cods:
        atributos_por_producto.setdefault(cod, {})

    agg = {"costo": costo or 0, "tiempo": dt,
           "tokens_in": usage.get("prompt_tokens", 0) or 0,
           "tokens_out": usage.get("completion_tokens", 0) or 0,
           "cache_hit": usage.get("prompt_cache_hit_tokens") or 0,
           "errores_api": 0, "errores_json": 0 if atrs else 1,
           "n_productos_devueltos": len(atrs)}
    print(f"  1 llamada: {len(atrs)}/5 productos devueltos  costo=${costo:.5f} {dt:.1f}s "
          f"in={agg['tokens_in']} out={agg['tokens_out']} cache_hit={agg['cache_hit']}"
          + (f"  ({mapeados_por_orden} mapeados por orden)" if mapeados_por_orden else ""))
    return atributos_por_producto, agg


def comparar(atr_a, atr_b):
    """Compara atributos entre modo A y B. Devuelve resumen de divergencias."""
    print("\n" + "=" * 70)
    print("COMPARACIÓN A vs B (atributos por producto)")
    print("=" * 70)
    divergencias = 0
    comparaciones = 0
    for cod in atr_a:
        a, b = atr_a.get(cod, {}), atr_b.get(cod, {})
        # llaves presentes
        faltan_a = LLAVES_CRITICAS - set(a.keys())
        faltan_b = LLAVES_CRITICAS - set(b.keys())
        # divergencias de valor en llaves comparables
        diffs = []
        for k in LLAVES_COMPARAR:
            if k in a or k in b:
                comparaciones += 1
                va, vb = a.get(k), b.get(k)
                if str(va or "").strip().lower() != str(vb or "").strip().lower():
                    divergencias += 1
                    diffs.append(f"{k}: A={va!r} B={vb!r}")
        print(f"\n  {cod}:")
        print(f"    llaves faltantes A: {sorted(faltan_a) or 'ninguna ✅'}")
        print(f"    llaves faltantes B: {sorted(faltan_b) or 'ninguna ✅'}")
        if diffs:
            print(f"    ⚠ divergencias valor ({len(diffs)}):")
            for d in diffs:
                print(f"       - {d}")
        else:
            print(f"    ✅ sin divergencias en llaves comparables")
    return divergencias, comparaciones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--productos", type=int, default=5, help="cuántos productos (2-5)")
    args = ap.parse_args()
    n = max(2, min(5, args.productos))
    productos = PRODUCTOS_TEST[:n]

    print("=" * 70)
    print(f"TEST A/B — batch=1 vs batch={n}  (proveedor: {os.getenv('IA_PROVEEDOR','glm')})")
    print(f"Visión OFF. NO toca la DB. {n} productos.")
    print("=" * 70)

    print(f"\n[1/3] Scrapeando {n} productos (una sola vez)...")
    scrapeados = _scrape_todos(productos)
    total_fuentes = sum(len(d["fuentes"]) for d in scrapeados)
    print(f"  Total fuentes extraídas: {total_fuentes} (promedio {total_fuentes/n:.1f}/producto)")

    print("\n[2/3] Cargando taxonomías...")
    taxonomias = ev.obtener_taxonomias_estrictas()

    atr_a, agg_a = modo_a_uno_por_llamada(scrapeados, taxonomias)
    atr_b, agg_b = modo_b_cinco_en_una(scrapeados, taxonomias)

    divergencias, comparaciones = comparar(atr_a, atr_b)

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN A/B")
    print("=" * 70)
    print(f"{'Métrica':<28} {'Modo A (1/llam)':>16} {'Modo B (5/llam)':>16}")
    print("-" * 62)
    print(f"{'Llamadas API':<28} {n:>16} {1:>16}")
    print(f"{'Costo USD total':<28} {agg_a['costo']:>16.5f} {agg_b['costo']:>16.5f}")
    print(f"{'Tiempo total (s)':<28} {agg_a['tiempo']:>16.1f} {agg_b['tiempo']:>16.1f}")
    print(f"{'Tokens input':<28} {agg_a['tokens_in']:>16,} {agg_b['tokens_in']:>16,}")
    print(f"{'Tokens output':<28} {agg_a['tokens_out']:>16,} {agg_b['tokens_out']:>16,}")
    print(f"{'Cache hit tokens':<28} {agg_a['cache_hit']:>16,} {agg_b['cache_hit']:>16,}")
    print(f"{'Errores API':<28} {agg_a['errores_api']:>16} {agg_b['errores_api']:>16}")
    print(f"{'Errores JSON':<28} {agg_a['errores_json']:>16} {agg_b['errores_json']:>16}")
    print(f"{'Productos devueltos':<28} {n:>16} {agg_b.get('n_productos_devueltos','?'):>16}")
    print(f"{'Divergencias valor A vs B':<28} {f'{divergencias}/{comparaciones}':>16}")
    ahorro_in = agg_a['tokens_in'] - agg_b['tokens_in']
    print(f"\n  Ahorro input B vs A: {ahorro_in:,} tokens ({ahorro_in*100/max(agg_a['tokens_in'],1):.1f}%)")
    print(f"  Divergencias de valor: {divergencias}/{comparaciones} "
          f"({divergencias*100/max(comparaciones,1):.1f}% de los atributos difieren)")

    # Veredicto automático
    print("\n" + "-" * 62)
    if divergencias == 0 and agg_b.get("n_productos_devueltos", 0) == n and agg_b["errores_json"] == 0:
        print("VEREDICTO: ✅ B (5/llamada) da el MISMO resultado que A, con ahorro de input.")
        print("   → El cambio sería seguro. Revisar también costo/tiempo arriba.")
    elif divergencias > 0:
        print(f"VEREDICTO: ⚠️ B diverge en {divergencias} atributo(s). La atención dividida afectó.")
        print("   → Revisar las divergencias arriba: ¿son críticas o menores?")
    elif agg_b.get("n_productos_devueltos", 0) != n:
        print(f"VEREDICTO: ❌ B devolvió {agg_b.get('n_productos_devueltos')} de {n} productos.")
        print("   → El modelo se cayó productos en el lote. batch=1 más confiable.")
    print("-" * 62)

    # Guardar resultado
    out = REPO / "scratch" / "test_ab_resultado.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "n": n, "productos": [c for c, _ in productos],
        "modo_a": {"agg": agg_a, "atributos": atr_a},
        "modo_b": {"agg": agg_b, "atributos": atr_b},
        "divergencias": divergencias, "comparaciones": comparaciones,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado guardado en: {out}")


if __name__ == "__main__":
    main()
