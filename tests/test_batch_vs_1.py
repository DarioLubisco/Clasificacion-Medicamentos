"""
Test DEFINITIVO: batch=5 (v4) vs 1-por-llamada (v3). 3 corridas en paralelo.

Decide si activar el flag ORQUESTADOR_BATCH_LLM=1 en producción.
Ambos prompts (v3 y v4) tienen los mismos fixes de integridad aplicados.
Bug de tokens arreglado (24000 Modo A, N×8192 Modo B).

Criterio: batch=5 debe mantener ≥97% de la calidad del 1-por-llamada.

NO toca la DB. Visión ON. Mismos 5 productos en cada corrida.

Uso (3 corridas en paralelo):
    python3 tests/test_batch_vs_1.py --run 1 &
    python3 tests/test_batch_vs_1.py --run 2 &
    python3 tests/test_batch_vs_1.py --run 3 &
Luego: python3 tests/promediar_batch_vs_1.py
"""
from __future__ import annotations
import json, os, sys, time, argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
try:
    from synapse_cred import load_synapse_credentials; load_synapse_credentials()
except Exception as _e:
    print(f"[WARN] synapse_cred: {_e}")
from dotenv import load_dotenv; load_dotenv(REPO / ".env")
os.environ["VISION_ACTIVA"] = "1"
os.environ["ORQUESTADOR_BATCH_LLM"] = "0"  # Modo 1-por-llamada explícito

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
    """5 llamadas de 1 producto (v3, modo producción actual)."""
    print(f"\n{'='*70}\nMODO 1-por-llamada (v3, 5 llamadas)\n{'='*70}")
    os.environ["PROMPT_ARCHIVO"] = "prompt_agente_v3_solidificado_final.txt"
    atr = {}; agg = {"costo":0.0,"tiempo":0.0,"tin":0,"tout":0,"ok":0,"fallo":0}
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
        agg["ok" if a else "fallo"]+=1
        print(f"  {d['codbarras']}: {'OK' if a else 'FALLO'} ${c:.5f} {dt:.1f}s")
    return atr, agg


def modo_batch5(scrapeados, tax):
    """1 llamada de 5 productos (v4, OCR por producto)."""
    print(f"\n{'='*70}\nMODO batch=5 (v4, 1 llamada)\n{'='*70}")
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
           "ok":sum(1 for v in atr.values() if v),"fallo":sum(1 for v in atr.values() if not v),
           "n_dev":n_dev}
    print(f"  1 llamada: {n_dev}/5 devueltos ${agg['costo']:.5f} {dt:.1f}s in={agg['tin']} out={agg['tout']}")
    return atr, agg


def comparar(a1, ab):
    print(f"\n{'='*70}\nCOMPARACIÓN 1-llamada vs batch=5\n{'='*70}")
    b_peor=0; b_mejor=0; div=0; cmp=0; base=5*len(LLAVES)
    for cod in a1:
        a,b = a1.get(cod,{}), ab.get(cod,{})
        print(f"\n  {cod}:")
        for k in LLAVES:
            va,vb = a.get(k), b.get(k)
            if str(va or "").strip().lower()==str(vb or "").strip().lower():
                cmp+=1; continue
            cmp+=1
            if (va is None or str(va).strip()=="") and (vb is not None and str(vb).strip()!=""):
                b_mejor+=1; tag="batch mejor (1llam=None)"
            elif (vb is None or str(vb).strip()=="") and (va is not None and str(va).strip()!=""):
                b_peor+=1; tag="batch peor (batch=None)"
            else:
                div+=1; tag="valor distinto"
            print(f"    {k}: 1llam={va!r} | batch={vb!r} → {tag}")
        if all(str(a.get(k) or "").strip().lower()==str(b.get(k) or "").strip().lower() for k in LLAVES):
            print(f"    ✅ idénticos")
    calidad = (1 - b_peor/base)*100
    print(f"\n  batch peor: {b_peor} | batch mejor: {b_mejor} | div valor: {div} | base: {base}")
    print(f"  CALIDAD batch vs 1-llamada: {calidad:.1f}%")
    return {"calidad":calidad,"b_peor":b_peor,"b_mejor":b_mejor,"div":div,"base":base}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run",default="1")
    args=ap.parse_args(); run=args.run
    print(f"{'='*70}\nTEST batch=5 vs 1-llamada [run {run}] — {os.getenv('IA_PROVEEDOR','glm')}\nVisión ON. 5 productos. NO toca DB.\n{'='*70}")
    print(f"\n[1/3] Scrapeando 5 productos...")
    scrapeados=[]
    for cod,desc in PRODUCTOS_TEST:
        print(f"  [scrape] {cod} — {desc[:45]}")
        f,im,u = op.scrape_producto(cod,desc)
        scrapeados.append({"codbarras":cod,"descripcion":desc,"fuentes":f,"imagenes":im,"urls":u})
    print(f"  fuentes: {sum(len(d['fuentes']) for d in scrapeados)} imgs: {sum(len(d['imagenes']) for d in scrapeados)}")
    print("\n[2/3] Taxonomías...")
    tax=ev.obtener_taxonomias_estrictas()
    atr1,agg1 = modo_1llamada(scrapeados, tax)
    atrb,aggb = modo_batch5(scrapeados, tax)
    comp = comparar(atr1, atrb)
    print(f"\n{'='*70}\nRESUMEN [run {run}]\n{'='*70}")
    print(f"{'Métrica':<24}{'1-llamada':>14}{'batch=5':>14}")
    print("-"*54)
    print(f"{'Llamadas API':<24}{5:>14}{1:>14}")
    print(f"{'Costo USD':<24}{agg1['costo']:>14.5f}{aggb['costo']:>14.5f}")
    print(f"{'Tiempo (s)':<24}{agg1['tiempo']:>14.1f}{aggb['tiempo']:>14.1f}")
    print(f"{'Tokens in':<24}{agg1['tin']:>14,}{aggb['tin']:>14,}")
    print(f"{'Tokens out':<24}{agg1['tout']:>14,}{aggb['tout']:>14,}")
    print(f"{'Productos OK':<24}{agg1['ok']:>14}{aggb['ok']:>14}")
    print(f"{'CALIDAD batch':<24}{'—':>14}{comp['calidad']:>13.1f}%")
    print("\n"+"-"*54)
    if comp['calidad']>=97 and aggb['ok']>=4:
        print(f"VEREDICTO: ✅ batch=5 cumple ≥97% ({comp['calidad']:.1f}%). Listo para activar.")
    elif comp['calidad']>=93:
        print(f"VEREDICTO: ⚠️ batch=5 cerca ({comp['calidad']:.1f}% < 97%). Revisar divergencias.")
    else:
        print(f"VEREDICTO: ❌ batch=5 NO cumple ({comp['calidad']:.1f}% < 97%). Mantener 1-llamada.")
    print("-"*54)
    out=REPO/"scratch"/f"test_batch_vs_1_run{run}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"run":run,"agg1":agg1,"aggb":aggb,"comp":comp,
        "atr1":atr1,"atrb":atrb}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado [run {run}]: {out}")


if __name__=="__main__":
    main()
