"""
Promedia las N corridas del test v5 vs v3 y calcula la calidad media de v5
respecto a v3.

Lee scratch/test_v5_vs_v3_run{1,2,3}.json (o los que existan) y calcula:
- Por cada corrida: divergencias, v5_mejor, v5_peor, productos OK v3/v5.
- Calidad v5 vs v3 = 1 - (v5_peor / total_atributos_comparables).
- Promedio de las N corridas.

Criterio del usuario: v5 ≥ 98% de calidad respecto al v3 (básico).

Uso:
    python3 tests/promediar_v5_vs_v3.py
"""
import json, glob
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LLAVES_COMPARAR = ["dominio","principio_activo","concentracion","forma_farmaceutica",
                   "cantidad_presentacion","contenido_neto","fabricante","marca","codigo_atc"]

def calidad_corrida(d):
    """% de atributos donde v5 coincide con v3 (v5 acertó) o lo mejoró (v3=None, v5 llenó).
    Solo cuenta como 'pérdida' los v5_peor (v5=None o distinto y v3 tenía valor)."""
    v5_peor = d.get("v5_peor", 0)
    v5_mejor = d.get("v5_mejor", 0)
    div = d.get("div", 0)
    total = v5_peor + v5_mejor + div
    # base de comparables: 5 productos × 9 llaves = 45
    base = 5 * len(LLAVES_COMPARAR)
    perdida_real = v5_peor  # divergencias donde v5 objetivamente perdió
    # las 'div' (valor distinto) y 'v5_mejor' no son pérdida (v5 respondió algo válido)
    calidad = 1 - (perdida_real / base) if base else 0
    return calidad * 100, perdida_real, v5_mejor, div, base

def main():
    archivos = sorted(glob.glob(str(REPO / "scratch" / "test_v5_vs_v3_run*.json")))
    # también el original sin sufijo (run1 si se llamó sin --run)
    orig = REPO / "scratch" / "test_v5_vs_v3_resultado.json"
    if orig.exists():
        archivos.insert(0, str(orig))
    if not archivos:
        print("No hay archivos de resultado todavía.")
        return
    print(f"=== PROMEDIO DE {len(archivos)} CORRIDA(S) v5 vs v3 ===\n")
    calidades = []
    print(f"{'Corrida':<12}{'calidad%':>10}{'v5_peor':>9}{'v5_mejor':>9}{'div_val':>9}{'base':>6}{'OK v3/v5':>12}")
    print("-"*67)
    for f in archivos:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"  {f}: error leyendo {e}")
            continue
        cal, peor, mejor, div, base = calidad_corrida(d)
        ok_v3 = d.get("v3",{}).get("agg",{}).get("ok","?")
        ok_v5 = d.get("v5",{}).get("agg",{}).get("ok","?")
        nombre = Path(f).stem
        print(f"{nombre:<12}{cal:>10.1f}{peor:>9}{mejor:>9}{div:>9}{base:>6}{f'{ok_v3}/{ok_v5}':>12}")
        calidades.append(cal)
    if calidades:
        prom = sum(calidades)/len(calidades)
        print(f"\n{'PROMEDIO':<12}{prom:>10.1f}")
        print(f"\nCriterio del usuario: v5 ≥ 98% de calidad respecto a v3.")
        if prom >= 98:
            print(f"VEREDICTO: ✅ v5 cumple ({prom:.1f}% ≥ 98%). Candidato a producción.")
        elif prom >= 95:
            print(f"VEREDICTO: ⚠️ v5 cerca ({prom:.1f}% < 98%). Casi, revisar divergencias.")
        else:
            print(f"VEREDICTO: ❌ v5 NO cumple ({prom:.1f}% < 98%). No reemplazar v3.")
    else:
        print("\nNo hay corridas con datos válidos.")

if __name__ == "__main__":
    main()
