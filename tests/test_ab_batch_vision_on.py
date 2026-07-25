"""
Test A/B con VISIÓN ON: batch=5-con-OCR vs 5×batch=1-con-OCR.

Validación final antes de activar ORQUESTADOR_BATCH_LLM=1 en producción.
El A/B original ganó con visión OFF; este confirma que batch=5 mantiene calidad
CUANDO hay imágenes reales y OCR por producto.

METODOLOGÍA:
  1. Scrapea 5 productos nuevos UNA sola vez.
  2. Modo A (5×batch=1, visión ON): usa procesar_producto_batch1 (como producción).
  3. Modo B (1×batch=5, visión ON): OCR por producto + procesar_lote_batch.
  4. Compara divergencias de atributos + costo + tokens + tiempo.

NO toca la DB. Visión ON (VISION_ACTIVA=1).

Uso:
    python3 tests/test_ab_batch_vision_on.py
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
# Visión ON explícito (este test SÍ usa imágenes)
os.environ["VISION_ACTIVA"] = "1"

import evaluate_local as ev
import orquestador_produccion as op

PRODUCTOS_TEST = [
    ("7591196006912", "Acetaminofén 650 mg x 10 tabletas Medigen"),
    ("7591196007155", "Apiret (Acetaminofén) 180 mg/5 ml solución oral 60 ml"),
    ("7591196007162", "BUDECORT SUSP P/INH 1MG/ML X 10ML"),
    ("7591196006530", "Mucoxol 30mg/5ml Jarabe 120ml (Ambroxol)"),
    ("7591196004604", "CORTYNASE 0.05% (Mometasona) suspensión nasal, 140 dosis."),
]
LLAVES_COMPARAR = {"dominio","principio_activo","concentracion","forma_farmaceutica",
                   "cantidad_presentacion","contenido_neto","fabricante","marca","codigo_atc"}


def _atr_de_parsed(parsed, codbarras=None):
    """Extrae dict de atributos de la salida del LLM. Si codbarras, busca por él."""
    if not parsed:
        return {}
    items = parsed if isinstance(parsed, list) else [parsed]
    for p in items:
        if not isinstance(p, dict):
            continue
        if codbarras is not None:
            cod = (p.get("registro") or {}).get("codbarras")
            if str(cod) == str(codbarras):
                return p.get("atributos_nuevos_consolidados", {}) or {}
    # fallback al primero
    for p in items:
        if isinstance(p, dict):
            return p.get("atributos_nuevos_consolidados", {}) or {}
    return {}


def modo_a(scrapeados, taxonomias):
    print("\n" + "="*70 + "\nMODO A: 5×batch=1 CON VISIÓN (como producción)\n" + "="*70)
    atr = {}
    agg = {"costo":0.0,"tiempo":0.0,"tin":0,"tout":0,"cache_hit":0,"err_api":0,"err_json":0,
           "ocr_chars":0}
    for d in scrapeados:
        cb = [{"registro":{"codigo":d["codbarras"],"codbarras":d["codbarras"],
                           "descripcion_original":d["descripcion"],"ciclos_reproceso":0},
               "atributos_ya_encontrados":None,"fuentes_web":d["fuentes"]}]
        t0=time.time()
        parsed, m, raw, fotos = ev.procesar_producto_batch1(
            json.dumps(cb, ensure_ascii=False), taxonomias, d["imagenes"], d["descripcion"])
        dt=time.time()-t0
        atr[d["codbarras"]] = _atr_de_parsed(parsed, d["codbarras"])
        agg["costo"]+=(m.get("costo_glm",0) or 0)+(m.get("costo_gemini",0) or 0)
        agg["tiempo"]+=dt
        agg["tin"]+=m.get("prompt_tokens",0) or 0
        agg["tout"]+=m.get("completion_tokens",0) or 0
        agg["cache_hit"]+=m.get("prompt_cache_hit_tokens",0) or 0
        agg["err_api"]+=len(m.get("errores_api",[]))
        agg["err_json"]+=m.get("errores_json",0) or 0
        print(f"  {d['codbarras']}: {'OK' if parsed else 'FALLO'} ${ (m.get('costo_glm',0) or 0)+(m.get('costo_gemini',0) or 0):.5f} {dt:.1f}s imgs={len(fotos)}")
    return atr, agg


def modo_b(scrapeados, taxonomias):
    print("\n" + "="*70 + "\nMODO B: 1×batch=5 CON VISIÓN (OCR por producto)\n" + "="*70)
    # OCR por producto (nota_vision_ocr propio)
    productos_datos = []
    for d in scrapeados:
        nota_ocr, fotos, mv = op._ocr_producto(d["imagenes"], d["descripcion"])
        productos_datos.append({"codbarras":d["codbarras"],"descripcion":d["descripcion"],
            "fuentes_web":d["fuentes"],"nota_vision_ocr":nota_ocr,
            "atributos_ya_encontrados":None,"ciclos_reproceso":0})
    t0=time.time()
    parsed_list, m, raw = ev.procesar_lote_batch(productos_datos, taxonomias)
    dt=time.time()-t0
    atr = {}
    for d in scrapeados:
        atr[d["codbarras"]] = _atr_de_parsed(parsed_list, d["codbarras"])
    agg = {"costo":(m.get("costo_glm",0) or 0)+(m.get("costo_gemini",0) or 0),"tiempo":dt,
           "tin":m.get("prompt_tokens",0) or 0,"tout":m.get("completion_tokens",0) or 0,
           "cache_hit":m.get("prompt_cache_hit_tokens",0) or 0,
           "err_api":len(m.get("errores_api",[])),"err_json":m.get("errores_json",0) or 0,
           "n_devueltos":len(parsed_list) if isinstance(parsed_list,list) else (1 if parsed_list else 0)}
    print(f"  1 llamada: {agg['n_devueltos']}/5 productos ${agg['costo']:.5f} {dt:.1f}s in={agg['tin']} out={agg['tout']}")
    return atr, agg


def comparar(a, b):
    print("\n" + "="*70 + "\nCOMPARACIÓN A vs B (con visión)\n" + "="*70)
    div=0; cmp=0
    for cod in a:
        aa,bb = a.get(cod,{}), b.get(cod,{})
        diffs=[]
        for k in LLAVES_COMPARAR:
            if k in aa or k in bb:
                cmp+=1
                if str(aa.get(k) or "").strip().lower()!=str(bb.get(k) or "").strip().lower():
                    div+=1; diffs.append(f"{k}: A={aa.get(k)!r} B={bb.get(k)!r}")
        print(f"\n  {cod}:")
        print(f"    {'⚠ '+str(len(diffs))+' divergencias' if diffs else '✅ sin divergencias'}")
        for d in diffs: print(f"       - {d}")
    return div, cmp


def main():
    print("="*70 + f"\nTEST A/B VISIÓN ON — proveedor {os.getenv('IA_PROVEEDOR','glm')}\nVisión ON. NO toca DB. 5 productos NUEVOS.\n" + "="*70)
    print("\n[1/3] Scrapeando 5 productos...")
    scrapeados=[]
    for cod,desc in PRODUCTOS_TEST:
        print(f"  [scrape] {cod} — {desc[:45]}")
        fuentes,imagenes,urls = op.scrape_producto(cod,desc)
        scrapeados.append({"codbarras":cod,"descripcion":desc,"fuentes":fuentes,"imagenes":imagenes,"urls":urls})
    print(f"  Total fuentes: {sum(len(d['fuentes']) for d in scrapeados)}, total imgs: {sum(len(d['imagenes']) for d in scrapeados)}")
    print("\n[2/3] Taxonomías...")
    tax = ev.obtener_taxonomias_estrictas()
    atr_a, agg_a = modo_a(scrapeados, tax)
    atr_b, agg_b = modo_b(scrapeados, tax)
    div, cmp = comparar(atr_a, atr_b)
    print("\n"+"="*70+"\nRESUMEN A/B VISIÓN ON\n"+"="*70)
    print(f"{'Métrica':<24}{'Modo A (5×1)':>16}{'Modo B (1×5)':>16}")
    print("-"*58)
    print(f"{'Llamadas LLM':<24}{5:>16}{1:>16}")
    print(f"{'Costo USD':<24}{agg_a['costo']:>16.5f}{agg_b['costo']:>16.5f}")
    print(f"{'Tiempo (s)':<24}{agg_a['tiempo']:>16.1f}{agg_b['tiempo']:>16.1f}")
    print(f"{'Tokens in':<24}{agg_a['tin']:>16,}{agg_b['tin']:>16,}")
    print(f"{'Tokens out':<24}{agg_a['tout']:>16,}{agg_b['tout']:>16,}")
    print(f"{'Cache hit':<24}{agg_a['cache_hit']:>16,}{agg_b['cache_hit']:>16,}")
    print(f"{'Divergencias':<24}{f'—':>16}{f'{div}/{cmp}':>16}")
    print(f"\n  Ahorro costo B vs A: ${agg_a['costo']-agg_b['costo']:.5f} ({(agg_a['costo']-agg_b['costo'])*100/max(agg_a['costo'],1e-9):.0f}%)")
    print(f"  Divergencias: {div}/{cmp} ({div*100/max(cmp,1):.1f}%)")
    print("\n"+"-"*58)
    if div==0 and agg_b.get("n_devueltos",0)==5:
        print("VEREDICTO: ✅ batch=5 con visión = MISMA calidad que batch=1. Seguro activar flag.")
    elif div<=2 and agg_b.get("n_devueltos",0)>=4:
        print(f"VEREDICTO: ⚠️ pocas divergencias ({div}). Revisar arriba: ¿críticas o menores?")
    elif agg_b.get("n_devueltos",0)<5:
        print(f"VEREDICTO: ❌ batch=5 devolvió {agg_b.get('n_devueltos')}/5 con visión. NO activar.")
    else:
        print(f"VEREDICTO: ⚠️ {div} divergencias. Revisar criticidad antes de activar.")
    print("-"*58)
    out = REPO/"scratch"/"test_ab_vision_resultado.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"modo_a":{"agg":agg_a,"atr":atr_a},"modo_b":{"agg":agg_b,"atr":atr_b},
                               "div":div,"cmp":cmp}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado: {out}")


if __name__ == "__main__":
    main()
