import os
import json
import sys

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import orquestador_scraper_v11_local as scrap
import scratch.evaluate_optimized_local as ev

def main():
    # Load the 20 hard products
    with open('reporte_dificiles_actualizado.json', 'r', encoding='utf-8') as f:
        dificiles = json.load(f)

    resultados_scraping = []
    for i, item in enumerate(dificiles):
        ean = f"9000000000{i:02d}"
        desc = item['descripcion']
        print(f"\n[{i+1}/20] Scrapeando {ean} - {desc}...")
        
        fuentes_extraidas = []
        todas_imagenes = []
        
        # Búsqueda web usando la descripción del producto
        urls_web = scrap.buscar_en_internet(desc, max_fuentes=5)  # limit to 5 sources to be faster
        for idx, url in enumerate(urls_web):
            fuente_data = scrap.extraer_fuente_web(url, idx+1, desc_maestra=desc)
            if fuente_data:
                fuentes_extraidas.append(fuente_data)
                todas_imagenes.extend(fuente_data['imagenes_encontradas'])
                if len(set(todas_imagenes)) >= 5: # limit to 5 images to be faster
                    break
                    
        resultados_scraping.append({
            "ean": ean,
            "descripcion": desc,
            "fuentes_web": fuentes_extraidas,
            "imagenes_b64": list(set(todas_imagenes))[:5]
        })

    # Save to input file for evaluation
    input_path = "scratch/eval_20_vision.json"
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(resultados_scraping, f, ensure_ascii=False, indent=2)

    print("\nScraping completado. Ejecutando evaluate_optimized...")

    # Run evaluation with the new file
    # We clear results first to force re-evaluation
    comp_path = "scratch/resultados_20_vision.json"
    if os.path.exists(comp_path):
        try:
            os.remove(comp_path)
        except Exception:
            pass

    ev.main(
        input_path=input_path,
        comp_path=comp_path,
        excel_path="scratch/comparativa_20_vision.xlsx"
    )

if __name__ == "__main__":
    main()
