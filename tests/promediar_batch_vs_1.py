"""Promedia las 3 corridas de batch=5 vs 1-llamada."""
import json, glob
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent

def main():
    archivos = sorted(glob.glob(str(REPO/"scratch"/"test_batch_vs_1_run*.json")))
    if not archivos:
        print("No hay resultados todavía.")
        return
    print(f"=== PROMEDIO DE {len(archivos)} CORRIDA(S) batch=5 vs 1-llamada ===\n")
    cals=[]; ahorros=[]
    print(f"{'Corrida':<26}{'calidad%':>9}{'ahorro$':>9}{'batch_ok':>9}")
    print("-"*53)
    for f in archivos:
        try: d=json.load(open(f,encoding="utf-8"))
        except Exception as e: print(f"  {f}: {e}"); continue
        cal=d.get("comp",{}).get("calidad",0)
        agg1=d.get("agg1",{}); aggb=d.get("aggb",{})
        ahorro=(agg1.get("costo",0)-aggb.get("costo",0))
        cals.append(cal); ahorros.append(ahorro)
        print(f"{Path(f).stem:<26}{cal:>9.1f}{ahorro:>9.5f}{aggb.get('ok','?'):>9}")
    if cals:
        prom=sum(cals)/len(cals); prom_ahorro=sum(ahorros)/len(ahorros)
        print(f"\n{'PROMEDIO':<26}{prom:>9.1f}{prom_ahorro:>9.5f}")
        print(f"\nCriterio: batch=5 ≥ 97% de calidad del 1-por-llamada.")
        if prom>=97: print(f"VEREDICTO: ✅ batch=5 cumple ({prom:.1f}% ≥ 97%). Activar flag.")
        elif prom>=93: print(f"VEREDICTO: ⚠️ batch=5 cerca ({prom:.1f}% < 97%). Revisar.")
        else: print(f"VEREDICTO: ❌ batch=5 NO cumple ({prom:.1f}% < 97%). Mantener 1-llamada.")

if __name__=="__main__":
    main()
