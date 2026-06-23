import json
import os

comp_path = "scratch/resultados_comparativa_multimodal.json"
with open(comp_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("| EAN | Producto | Gemini 2.5 Flash | Gemini 2.5 Pro | Gemini 3.1 Pro | Gemma 4 31B | Gemma 4 26B-A4B |")
print("|---|---|---|---|---|---|---|")

for ean, item in data.items():
    desc = item.get("descripcion", "")
    # truncate description to keep table tidy
    if len(desc) > 30:
        desc = desc[:27] + "..."
        
    def fmt_model(res):
        if not res:
            return "*Rechazado (NULL)*"
        if res.get("error"):
            return "*Error*"
        at = res.get("atrib")
        if not at:
            return "*Rechazado (NULL)*"
        score = res.get("score", 0)
        conf = at.get("confianza_nivel", 0)
        return f"{score} (Nivel {conf})"
        
    flash = fmt_model(item.get("gemini_2_5_flash"))
    pro25 = fmt_model(item.get("gemini_2_5_pro"))
    pro31 = fmt_model(item.get("gemini_3_1_pro"))
    gemma31 = fmt_model(item.get("gemma_4_31b"))
    gemma26 = fmt_model(item.get("gemma_4_26b"))
    
    print(f"| {ean} | {desc} | {flash} | {pro25} | {pro31} | {gemma31} | {gemma26} |")

print("\n--- Costos Totales ---")
costs = {
    "gemini_2_5_flash": 0.0,
    "gemini_2_5_pro": 0.0,
    "gemini_3_1_pro": 0.0,
    "gemma_4_31b": 0.0,
    "gemma_4_26b": 0.0
}
for ean, item in data.items():
    for k in costs.keys():
        res = item.get(k)
        if res:
            costs[k] += res.get("costo", 0.0)

for k, val in costs.items():
    print(f"- {k}: ${val:.6f}")
