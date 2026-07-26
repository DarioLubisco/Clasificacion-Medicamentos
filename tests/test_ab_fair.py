"""
Test A/B FAIR: batch=5 vs 1-por-llamada. Mismas condiciones.

- reasoning_effort=max para AMBOS modos (del .env)
- max_tokens=24000 por producto para AMBOS
- timeout dinámico para batch (300 + 120*(N-1))
- Mismos 5 productos, misma sesión
- Workers desactivados (test limpio)
- NO toca DB

Uso:
    python3 tests/test_ab_fair.py
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


def modo_1llamada(scrapeados, tax):
    """5 llamadas de 1 producto (v3). Mismos parámetros que batch."""
    print(f"\n{'='*70}\nMODO 1-por-llamada (v3, 5 llamadas)\n{'='*70}")
    os.environ["PROMPT_ARCHIVO"] = "prompt_agente_v3_solidificado_final.txt"
    atr = {}; agg = {"costo":0.0,"tiempo":0.0,"tin":0,"tout":0,"cache":0,"ok":0,"fallo":0}
    for d in scrapeados:
        cb = [{"registro":{"codigo":d["codbarras"],"codbarras":d["codbarras"],
                           "descripcion_original":d["descripcion"],"ciclos_reproceso":0},
               "atributos_ya_encontrados":None,"fuentes_web":d["fuentes"]}]
        t0=time.time()
        parsed,m,raw,fotos = ev.procesar_producto_batch1(
            json.dumps(cb,ensure_ascii=False), tax, d["imagenes"], d["descripcion"])
        dt=time.time()-t0
        a=_atr_de(parsed,d["codbarras"]); atr[d["codbarras"]]=a
        c=(m.get("costo_glm",0) or 0)+(m.get("costo_gemini",0) or 0)
        agg["costo"]+=c; agg["tiempo"]+=dt; agg["tin"]+=m.get("prompt_tokens",0) or 0
        agg["tout"]+=m.get("completion_tokens",0) or 0
        agg["cache"]+=m.get("prompt_cache_hit_tokens",0) or 0
        agg["ok" if a else "fallo"]+=1
        print(f"  {d['codbarras']}: {'OK' if a else 'FALLO'} ${c:.5f} {dt:.1f}s")
    return atr, agg


def modo_batch5(scrapeados, tax):
    """1 llamada de 5 productos (v4). reasoning_effort=max, timeout dinámico."""
    print(f"\n{'='*70}\nMODO batch=5 (v4, 1 llamada)\n{'='*70}")
    os.environ["ORQUESTADOR_BATCH_LLM"] = "1"
    productos_datos=[]
    for d in scrapeados:
        nota_ocr,fotos,mv = op._ocr_producto(d["imagenes"], d["descripcion"])
        productos_datos.append({"codbarras":d["codbarras"],"descripcion":d["descripcion"],
            "fuentes_web":d["fuentes"],"nota_vision_ocr":nota_ocr,
            "atributos_ya_encontrados":None,"ciclos_reproceso":0})
    t0=time.time()
    parsed_list,m,raw = ev.procesar_lote_batch(productos_datos, tax)
    dt=time.time()-t0
    atr={}
    for d in scrapeados:
        atr[d["codbarras"]]=_atr_de(parsed_list,d["codbarras"])
    n_dev = len(parsed_list) if isinstance(parsed_list,list) else (1 if parsed_list else 0)
    agg = {"costo":(m.get("costo_glm",0) or 0)+(m.get("costo_gemini",0) or 0),"tiempo":dt,
           "tin":m.get("prompt_tokens",0) or 0,"tout":m.get("completion_tokens",0) or 0,
           "cache":m.get("prompt_cache_hit_tokens",0) or 0,
           "ok":sum(1 for v in atr.values() if v),"fallo":sum(1 for v in atr.values() if not v),
           "n_dev":n_dev}
    print(f"  1 llamada: {n_dev}/5 devueltos ${agg['costo']:.5f} {dt:.1f}s in={agg['tin']} out={agg['tout']}")
    return atr, agg


def comparar(a1, ab):
    print(f"\n{'='*70}\nCOMPARACIÓN CAMPO POR CAMPO\n{'='*70}")
    b_peor=0; b_mejor=0; iguales=0; div=0; base=5*len(LLAVES)
    for cod in a1:
        a,b = a1.get(cod,{}), ab.get(cod,{})
        print(f"\n  {cod}:")
        for k in LLAVES:
            va,vb = a.get(k), b.get(k)
            sa,sb = str(va or "").strip().lower(), str(vb or "").strip().lower()
            if sa==sb:
                iguales+=1; continue
            if (va is None or sa=="") and (vb is not None and sb!=""):
                b_mejor+=1; tag="batch mejor"
            elif (vb is None or sb=="") and (va is not None and sa!=""):
                b_peor+=1; tag="batch PEOR"
            else:
                div+=1; tag="valor distinto"
            print(f"    {k}: 1llam={va!r} | batch={vb!r} → {tag}")
        if all(str(a.get(k) or "").strip().lower()==str(b.get(k) or "").strip().lower() for k in LLAVES):
            print(f"    ✅ idénticos")
    calidad = (1 - b_peor/base)*100
    print(f"\n  Resumen: iguales={iguales} | batch mejor={b_mejor} | batch peor={b_peor} | distintos={div}")
    print(f"  CALIDAD batch vs 1-llamada: {calidad:.1f}%")
    return {"calidad":calidad,"b_peor":b_peor,"b_mejor":b_mejor,"iguales":iguales,"div":div,"base":base}


def main():
    print(f"{'='*70}")
    print(f"A/B FAIR TEST: batch=5 vs 1-por-llamada")
    print(f"reasoning_effort=max (del .env), max_tokens=24K/producto")
    print(f"Workers desactivados. NO toca DB. Visión ON.")
    print(f"{'='*70}")

    # Scrapear una sola vez (mismos datos para ambos)
    print(f"\n[1/4] Scrapeando 5 productos...")
    scrapeados = []
    for cod, desc in PRODUCTOS_TEST:
        print(f"  [scrape] {cod} — {desc[:45]}")
        f, im, u = op.scrape_producto(cod, desc)
        scrapeados.append({"codbarras":cod,"descripcion":desc,"fuentes":f,"imagenes":im,"urls":u})
    print(f"  fuentes: {sum(len(d['fuentes']) for d in scrapeados)} imgs: {sum(len(d['imagenes']) for d in scrapeados)}")

    print("\n[2/4] Cargando taxonomías...")
    tax = ev.obtener_taxonomias_estrictas()

    # Modo A: 1-por-llamada
    print("\n[3/4] Ejecutando 1-por-llamada (5 llamadas)...")
    atr1, agg1 = modo_1llamada(scrapeados, tax)

    # Modo B: batch=5
    print("\n[4/4] Ejecutando batch=5 (1 llamada)...")
    atrb, aggb = modo_batch5(scrapeados, tax)

    # Comparación
    comp = comparar(atr1, atrb)

    # Resumen
    print(f"\n{'='*70}")
    print(f"RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"{'Métrica':<24}{'1-por-llamada':>14}{'batch=5':>14}")
    print("-"*54)
    print(f"{'Llamadas API':<24}{5:>14}{1:>14}")
    print(f"{'Costo USD':<24}{agg1['costo']:>14.5f}{aggb['costo']:>14.5f}")
    print(f"{'Tiempo (s)':<24}{agg1['tiempo']:>14.1f}{aggb['tiempo']:>14.1f}")
    print(f"{'Tokens in':<24}{agg1['tin']:>14,}{aggb['tin']:>14,}")
    print(f"{'Tokens out':<24}{agg1['tout']:>14,}{aggb['tout']:>14,}")
    print(f"{'Cache hit tokens':<24}{agg1['cache']:>14,}{aggb['cache']:>14,}")
    print(f"{'Productos OK':<24}{agg1['ok']:>14}{aggb['ok']:>14}")
    print(f"{'CALIDAD batch':<24}{'—':>14}{comp['calidad']:>13.1f}%")
    ahorro_costo = (1 - aggb['costo']/agg1['costo'])*100 if agg1['costo']>0 else 0
    ahorro_tiempo = (1 - aggb['tiempo']/agg1['tiempo'])*100 if agg1['tiempo']>0 else 0
    print(f"{'Ahorro costo':<24}{'—':>14}{ahorro_costo:>13.1f}%")
    print(f"{'Ahorro tiempo':<24}{'—':>14}{ahorro_tiempo:>13.1f}%")
    print("-"*54)
    if comp['calidad']>=97 and aggb['ok']>=4:
        print(f"VEREDICTO: ✅ batch=5 cumple ≥97% ({comp['calidad']:.1f}%). Listo para activar.")
    elif comp['calidad']>=93:
        print(f"VEREDICTO: ⚠️ batch=5 cerca ({comp['calidad']:.1f}% < 97%). Revisar divergencias.")
    else:
        print(f"VEREDICTO: ❌ batch=5 NO cumple ({comp['calidad']:.1f}% < 97%). Mantener 1-llamada.")
    print("-"*54)

    out = REPO / "scratch" / "test_ab_fair.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"agg1":agg1,"aggb":aggb,"comp":comp,
        "atr1":atr1,"atrb":atrb}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado: {out}")


if __name__=="__main__":
    main()
