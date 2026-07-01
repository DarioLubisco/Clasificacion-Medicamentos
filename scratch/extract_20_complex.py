import json

with open('reporte_dificiles_actualizado.json', 'r', encoding='utf-8') as f:
    dificiles = json.load(f)

dificiles_desc = [item['descripcion'] for item in dificiles]

with open('investigacion_limpieza_v10.json', 'r', encoding='utf-8') as f:
    completo = json.load(f)

extracted = []
for idx, res in enumerate(completo):
    desc_orig = res['registro']['descripcion_original']
    if desc_orig in dificiles_desc:
        ean = res['registro']['codbarras']
        fuentes_web = []
        if 'fuentes_web' in res:
            fuentes_web = res['fuentes_web']
        
        extracted.append({
            "ean": ean,
            "descripcion": desc_orig,
            "fuentes_web": fuentes_web,
            "imagenes_b64": []
        })

print(f"Found {len(extracted)} items out of {len(dificiles_desc)}")

# Just in case some weren't found, we can mock them or print warnings
with open('scratch/eval_20_complejos.json', 'w', encoding='utf-8') as f:
    json.dump(extracted, f, indent=2, ensure_ascii=False)
