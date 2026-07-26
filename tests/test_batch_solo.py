"""
Test batch=5 SIN competencia (workers desactivados).

Objetivo: medir calidad REAL del batch cuando DeepSeek no está saturado
por 8 workers compitiendo. Timeout extendido a 600s.

Pre-requisito: los 8 workers de n8n deben estar desactivados y los
procesos orquestador matados.

NO toca la DB. Visión ON. 5 productos fijos.

Uso:
    python3 tests/test_batch_solo.py
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from synapse_cred import load_synapse_credentials; load_synapse_credentials()
except Exception as _e:
    print(f"[WARN] synapse_cred: {_e}")
from dotenv import load_dotenv; load_dotenv(REPO / ".env")
os.environ["VISION_ACTIVA"] = "1"
os.environ["ORQUESTADOR_BATCH_LLM"] = "1"  # BATCH MODE ON

# Override timeout para batch: 600s en vez de 300s
os.environ["DEEPSEEK_TIMEOUT_POR_PRODUCTO"] = "600"

import evaluate_local as ev
import orquestador_produccion as op

PRODUCTOS_TEST = [
    ("7591196006912", "Acetaminofén 650 mg x 10 tabletas Medigen"),
    ("7591196007155", "Apiret (Acetaminofén) 180 mg/5 ml solución oral 60 ml"),
    ("7591196007162", "BUDECORT SUSP P/INH 1MG/ML X 10ML"),
    ("7591196006530", "Mucoxol 30mg/5ml Jarabe 120ml (Ambroxol)"),
    ("7591196004604", "CORTYNASE 0.05% (Mometasona) suspensión nasal, 140 dosis."),
]
LLAVES = ["dominio","principio_activo","concentracion","forma_farmaceutica",
          "cantidad_presentacion","contenido_neto","fabricante","marca","codigo_atc"]


def _atr_de(parsed, codbarras=None):
    if not parsed: return {}
    items = parsed if isinstance(parsed, list) else [parsed]
    for p in items:
        if not isinstance(p, dict): continue
        if codbarras is not None and str((p.get("registro") or {}).get("codbarras"))==str(codbarras):
            return p.get("atributos_nuevos_consolidados", {}) or {}
    for p in items:
        if isinstance(p, dict):
            return p.get("atributos_nuevos_consolidados", {}) or {}
    return {}


def main():
    print(f"{'='*70}")
    print(f"TEST batch=5 SIN competencia — workers desactivados")
    print(f"Timeout extendido: 600s. Visión ON. NO toca DB.")
    print(f"{'='*70}")

    # Verificar que no hay workers corriendo
    import subprocess
    procs = subprocess.run(["pgrep", "-f", "orquestador_produccion"], capture_output=True, text=True)
    if procs.stdout.strip():
        print(f"⚠️  ADVERTENCIA: hay procesos orquestador corriendo:\n{procs.stdout}")
        print("Matalos antes con: pkill -f orquestador_produccion")
        sys.exit(1)
    print("\n✅ 0 procesos orquestador corriendo — test limpio")

    # Scrapear
    print(f"\n[1/3] Scrapeando 5 productos...")
    scrapeados = []
    for cod, desc in PRODUCTOS_TEST:
        print(f"  [scrape] {cod} — {desc[:45]}")
        f, im, u = op.scrape_producto(cod, desc)
        scrapeados.append({"codbarras":cod,"descripcion":desc,"fuentes":f,"imagenes":im,"urls":u})
    total_f = sum(len(d['fuentes']) for d in scrapeados)
    total_i = sum(len(d['imagenes']) for d in scrapeados)
    print(f"  fuentes: {total_f} imgs: {total_i}")

    # Taxonomías
    print("\n[2/3] Cargando taxonomías...")
    tax = ev.obtener_taxonomias_estrictas()

    # Batch=5
    print(f"\n[3/3] Ejecutando batch=5 (1 llamada LLM, timeout 600s)...")
    productos_datos = []
    for d in scrapeados:
        print(f"  [OCR] {d['codbarras']}")
        nota_ocr, fotos, mv = op._ocr_producto(d["imagenes"], d["descripcion"])
        productos_datos.append({
            "codbarras": d["codbarras"],
            "descripcion": d["descripcion"],
            "fuentes_web": d["fuentes"],
            "nota_vision_ocr": nota_ocr,
            "atributos_ya_encontrados": None,
            "ciclos_reproceso": 0,
        })

    t0 = time.time()
    parsed_list, m, raw = ev.procesar_lote_batch(productos_datos, tax)
    dt = time.time() - t0

    # Analizar resultados
    atr = {}
    for d in scrapeados:
        atr[d["codbarras"]] = _atr_de(parsed_list, d["codbarras"])

    n_dev = len(parsed_list) if isinstance(parsed_list, list) else (1 if parsed_list else 0)
    costo = (m.get("costo_glm", 0) or 0) + (m.get("costo_gemini", 0) or 0)
    tin = m.get("prompt_tokens", 0) or 0
    tout = m.get("completion_tokens", 0) or 0
    cache_hit = m.get("prompt_cache_hit_tokens", 0) or 0
    ok = sum(1 for v in atr.values() if v)
    fallo = sum(1 for v in atr.values() if not v)

    print(f"\n{'='*70}")
    print(f"RESULTADOS batch=5 (sin competencia)")
    print(f"{'='*70}")
    print(f"  Productos devueltos: {n_dev}/5")
    print(f"  Productos OK (con atributos): {ok}/5")
    print(f"  Productos FALLO (sin atributos): {fallo}/5")
    print(f"  Costo total: ${costo:.5f}")
    print(f"  Tiempo: {dt:.1f}s")
    print(f"  Tokens in: {tin:,}")
    print(f"  Tokens out: {tout:,}")
    print(f"  Cache hit tokens: {cache_hit:,}")

    # Detalle por producto
    print(f"\n{'='*70}")
    print(f"ATRIBUTOS POR PRODUCTO")
    print(f"{'='*70}")
    for cod, desc in PRODUCTOS_TEST:
        a = atr.get(cod, {})
        n_campos = sum(1 for k in LLAVES if a.get(k) is not None and str(a.get(k)).strip())
        print(f"\n  {cod} ({desc[:40]})")
        print(f"    Campos llenos: {n_campos}/{len(LLAVES)}")
        for k in LLAVES:
            v = a.get(k)
            status = "✅" if v is not None and str(v).strip() else "❌"
            print(f"    {status} {k}: {v!r}")

    # JSON output
    out = REPO / "scratch" / "test_batch_solo.json"
    out.parent.mkdir(exist_ok=True)
    result = {
        "n_devueltos": n_dev,
        "ok": ok,
        "fallo": fallo,
        "costo": costo,
        "tiempo": dt,
        "tin": tin,
        "tout": tout,
        "cache_hit": cache_hit,
        "atributos": atr,
        "raw_preview": (raw or "")[:2000],
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado guardado: {out}")

    # Veredicto
    print(f"\n{'='*70}")
    if n_dev == 5 and ok >= 4:
        print(f"VEREDICTO: ✅ batch=5 FUNCIONA sin competencia ({ok}/5 OK, {dt:.0f}s)")
    elif n_dev >= 3 and ok >= 3:
        print(f"VEREDICTO: ⚠️ batch=5 parcial ({ok}/5 OK, {n_dev}/5 devueltos)")
    elif n_dev == 0:
        print(f"VEREDICTO: ❌ batch=5 TIMEOUT incluso sin competencia ({dt:.0f}s)")
    else:
        print(f"VEREDICTO: ❌ batch=5 falló ({ok}/5 OK, {n_dev}/5 devueltos)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
