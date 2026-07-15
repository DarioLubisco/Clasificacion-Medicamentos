import os
import json
import sys
from urllib.parse import urlparse

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import orquestador_scraper as scrap
import evaluate_local as ev


def _dominio(url: str) -> str:
    """Dominio raíz para deduplicación de imágenes por fuente independiente."""
    try:
        host = urlparse(url).netloc.lower()
        for pref in ("www.", "cdn.", "static.", "img.", "images."):
            if host.startswith(pref):
                host = host[len(pref):]
        return host
    except Exception:
        return ""

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
        dominios_usados = set()

        # Búsqueda web usando la descripción del producto
        urls_web = scrap.buscar_en_internet(desc, max_fuentes=5)  # limit to 5 sources to be faster
        for idx, url in enumerate(urls_web):
            fuente_data = scrap.extraer_fuente_web(url, idx+1, desc_maestra=desc)
            if fuente_data:
                fuentes_extraidas.append(fuente_data)
                for img_url in fuente_data['imagenes_encontradas']:
                    dom = _dominio(img_url) or _dominio(url)
                    # Independencia: 1 imagen por dominio (evita 3 copias del mismo listing).
                    if dom and dom not in dominios_usados:
                        dominios_usados.add(dom)
                        todas_imagenes.append(img_url)
                    elif not dom:
                        todas_imagenes.append(img_url)
                    if len(set(todas_imagenes)) >= 5: # limit to 5 images to be faster
                        break
                if len(set(todas_imagenes)) >= 5:
                    break

        resultados_scraping.append({
            "ean": ean,
            "descripcion": desc,
            "fuentes_web": fuentes_extraidas,
            "imagenes_b64": list(dict.fromkeys(todas_imagenes))[:5]
        })

    # Save to input file for evaluation
    input_path = "scratch/eval_20_vision.json"
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(resultados_scraping, f, ensure_ascii=False, indent=2)

    print("\nScraping completado. Ejecutando evaluate_local...")

    output_path = "scratch/resultados_20_vision.json"
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass

    ev.main(input_path=input_path, output_path=output_path)

if __name__ == "__main__":
    main()
