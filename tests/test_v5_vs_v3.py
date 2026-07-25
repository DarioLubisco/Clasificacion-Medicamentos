"""
Test: prompt v5 (reescrito por K3) vs prompt v3 (producción).

Aísla el efecto del PROMPT: mismos 5 productos, misma visión, mismo modo
1-producto-por-llamada. Solo cambia el prompt (v3 vs v5). Compara:
- parse OK / FALLO por producto
- llaves críticas presentes
- coincidencia de atributos clave (divergencias v3 vs v5)
- costo/tokens

Objetivo: confirmar que v5 mantiene o mejora la calidad de v3 antes de
considerarlo para producción o para el modo batch.

NO toca la DB. Visión ON.

Uso:
    python3 tests/test_v5_vs_v3.py
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
LLAVES_COMPARAR = ["dominio","principio_activo","concentracion","forma_farmaceutica",
                   "cantidad_presentacion","contenido_neto","fabricante","marca","codigo_atc"]
LLAVES_CRITICAS = {"dominio","principio_activo","concentracion","forma_farmaceutica",
                   "cantidad_presentacion","registro_sanitario","volumen_unidad_medida"}


def _atr(parsed):
    if not parsed: return {}
    items = parsed if isinstance(parsed, list) else [parsed]
    for p in items:
        if isinstance(p, dict):
            return p.get("atributos_nuevos_consolidados", {}) or {}
    return {}


def correr_con_prompt(scrapeados, taxonomias, prompt_archivo, etiqueta):
    """Procesa los 5 productos 1-por-llamada usando el prompt indicado."""
    print(f"\n{'='*70}\n{etiqueta} (prompt: {prompt_archivo})\n{'='*70}")
    os.environ["PROMPT_ARCHIVO"] = prompt_archivo
    atr = {}
    agg = {"costo":0.0,"tiempo":0.0,"tin":0,"tout":0,"ok":0,"fallo":0,
           "llaves_faltan_total":0,"llaves_check":0}
    for d in scrapeados:
        cb = [{"registro":{"codigo":d["codbarras"],"codbarras":d["codbarras"],
                           "descripcion_original":d["descripcion"],"ciclos_reproceso":0},
               "atributos_ya_encontrados":None,"fuentes_web":d["fuentes"]}]
        t0=time.time()
        parsed, m, raw, fotos = ev.procesar_producto_batch1(
            json.dumps(cb, ensure_ascii=False), taxonomias, d["imagenes"], d["descripcion"])
        dt=time.time()-t0
        a = _atr(parsed)
        atr[d["codbarras"]] = a
        costo = (m.get("costo_glm",0) or 0)+(m.get("costo_gemini",0) or 0)
        agg["costo"]+=costo; agg["tiempo"]+=dt
        agg["tin"]+=m.get("prompt_tokens",0) or 0
        agg["tout"]+=m.get("completion_tokens",0) or 0
        if parsed and a: agg["ok"]+=1
        else: agg["fallo"]+=1
        faltan = LLAVES_CRITICAS - set(a.keys())
        agg["llaves_faltan_total"]+=len(faltan)
        agg["llaves_check"]+=len(LLAVES_CRITICAS)
        print(f"  {d['codbarras']}: {'OK' if a else 'FALLO'} ${costo:.5f} {dt:.1f}s llaves_faltan={len(faltan)}")
    return atr, agg


def comparar(a_v3, a_v5):
    print(f"\n{'='*70}\nCOMPARACIÓN v3 vs v5\n{'='*70}")
    div=0; cmp=0; v5_mejor=0; v5_peor=0
    for cod in a_v3:
        a3, a5 = a_v3.get(cod,{}), a_v5.get(cod,{})
        print(f"\n  {cod}:")
        for k in LLAVES_COMPARAR:
            v3, v5 = a3.get(k), a5.get(k)
            if str(v3 or "").strip().lower() == str(v5 or "").strip().lower():
                continue
            cmp+=1
            # si v3 es None/vacío y v5 tiene valor → v5 mejor
            if (v3 is None or str(v3).strip()=="") and (v5 is not None and str(v5).strip()!=""):
                v5_mejor+=1; tag="v5 mejor (v3=None)"
            elif (v5 is None or str(v5).strip()=="") and (v3 is not None and str(v3).strip()!=""):
                v5_peor+=1; tag="v5 peor (v5=None)"
            else:
                div+=1; tag="valor distinto"
            print(f"    {k}: v3={v3!r} | v5={v5!r} → {tag}")
        if all(str(a3.get(k) or "").strip().lower()==str(a5.get(k) or "").strip().lower() for k in LLAVES_COMPARAR):
            print(f"    ✅ idénticos en llaves comparables")
    print(f"\n  Divergencias valor distinto: {div}")
    print(f"  v5 mejor (v3=None, v5 llenó): {v5_mejor}")
    print(f"  v5 peor (v5=None, v3 llenó): {v5_peor}")
    return div, v5_mejor, v5_peor, cmp


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="1", help="identificador de corrida (1,2,3) para distinguir logs")
    args = ap.parse_args()
    run = args.run
    print(f"{'='*70}\nTEST v5 vs v3 [run {run}] — proveedor {os.getenv('IA_PROVEEDOR','glm')}\nVisión ON. 5 productos. NO toca DB.\n{'='*70}")
    print("\n[1/3] Scrapeando 5 productos...")
    scrapeados=[]
    for cod,desc in PRODUCTOS_TEST:
        print(f"  [scrape] {cod} — {desc[:45]}")
        fuentes,imagenes,urls = op.scrape_producto(cod,desc)
        scrapeados.append({"codbarras":cod,"descripcion":desc,"fuentes":fuentes,"imagenes":imagenes,"urls":urls})
    print(f"  fuentes: {sum(len(d['fuentes']) for d in scrapeados)}, imgs: {sum(len(d['imagenes']) for d in scrapeados)}")
    print("\n[2/3] Taxonomías...")
    tax = ev.obtener_taxonomias_estrictas()

    atr_v3, agg_v3 = correr_con_prompt(scrapeados, tax, "prompt_agente_v3_solidificado_final.txt", "MODO v3 (producción actual)")
    atr_v5, agg_v5 = correr_con_prompt(scrapeados, tax, "prompt_agente_v5_reescrito_k3.txt", "MODO v5 (reescrito por K3)")

    div, v5m, v5p, cmp = comparar(atr_v3, atr_v5)

    print(f"\n{'='*70}\nRESUMEN v3 vs v5\n{'='*70}")
    print(f"{'Métrica':<28}{'v3':>16}{'v5':>16}")
    print("-"*60)
    print(f"{'Productos OK (de 5)':<28}{agg_v3['ok']:>16}{agg_v5['ok']:>16}")
    print(f"{'Productos FALLO':<28}{agg_v3['fallo']:>16}{agg_v5['fallo']:>16}")
    lk_v3 = f"{agg_v3['llaves_faltan_total']}/{agg_v3['llaves_check']}"
    lk_v5 = f"{agg_v5['llaves_faltan_total']}/{agg_v5['llaves_check']}"
    print(f"{'Llaves críticas faltantes':<28}{lk_v3:>16}{lk_v5:>16}")
    print(f"{'Costo USD':<28}{agg_v3['costo']:>16.5f}{agg_v5['costo']:>16.5f}")
    print(f"{'Tokens in':<28}{agg_v3['tin']:>16,}{agg_v5['tin']:>16,}")
    print(f"{'Tokens out':<28}{agg_v3['tout']:>16,}{agg_v5['tout']:>16,}")
    print(f"{'Tiempo (s)':<28}{agg_v3['tiempo']:>16.1f}{agg_v5['tiempo']:>16.1f}")
    print(f"\n  Divergencias v3↔v5: {div} (valor distinto)")
    print(f"  v5 llenó campos que v3 dejó null: {v5m}")
    print(f"  v5 dejó null campos que v3 llenó: {v5p}")
    print("\n"+"-"*60)
    if agg_v5["ok"]>=agg_v3["ok"] and v5p<=2:
        print("VEREDICTO: ✅ v5 mantiene o mejora calidad de v3. Candidato a producción.")
    elif v5p>3:
        print(f"VEREDICTO: ⚠️ v5 pierde {v5p} campos vs v3. Revisar antes de usar.")
    else:
        print("VEREDICTO: ⚠️ revisar divergencias arriba antes de decidir.")
    print("-"*60)
    out = REPO/"scratch"/f"test_v5_vs_v3_run{run}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"run":run,"v3":{"agg":agg_v3,"atr":atr_v3},"v5":{"agg":agg_v5,"atr":atr_v5},
                               "div":div,"v5_mejor":v5m,"v5_peor":v5p}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultado [run {run}]: {out}")


if __name__ == "__main__":
    main()
