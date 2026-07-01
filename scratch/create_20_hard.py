import json

with open('reporte_dificiles_actualizado.json', 'r', encoding='utf-8') as f:
    dificiles = json.load(f)

synthetic = []
for i, d in enumerate(dificiles):
    synthetic.append({
        "ean": f"9000000000{i:02d}",
        "descripcion": d["descripcion"],
        "fuentes_web": [],
        "imagenes_b64": []
    })

with open('scratch/eval_20_hard.json', 'w', encoding='utf-8') as f:
    json.dump(synthetic, f, indent=2, ensure_ascii=False)
