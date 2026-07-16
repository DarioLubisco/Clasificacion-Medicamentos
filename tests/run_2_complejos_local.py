import os
import json
import sys

# 1. Lista de EANs (Reducida a 2 productos a petición del usuario)
eans_test = [
    {"ean": "000000000130", "desc": "Ondansetrón 4 mg/2 ml solución inyectable, 10 ampollas"},
    {"ean": "0000042419860", "desc": "NIVEA Crema de Manos 3 en 1 Antibacterial Cuidado y Protección 75 ml"} # EAN real para probar el fix de SQL Server
]

# Modificar evaluate_optimized temporalmente para leer de este json en vez de la BD.
import orquestador_scraper as scrap

resultados_scraping = []
for item in eans_test:
    print(f"Scrapeando {item['ean']}...")
    
    fuentes_extraidas = []
    todas_imagenes = []
    
    # Búsqueda web con comillas inyectadas en v11
    urls_web = scrap.buscar_en_internet(f'"{item["ean"]}" {item["desc"]}', max_fuentes=10)
    for idx, url in enumerate(urls_web):
        fuente_data = scrap.extraer_fuente_web(url, idx+1)
        if fuente_data:
            fuentes_extraidas.append(fuente_data)
            todas_imagenes.extend(fuente_data['imagenes_encontradas'])
            if len(set(todas_imagenes)) >= 10:
                break
                
    resultados_scraping.append({
        "ean": item['ean'],
        "descripcion": item['desc'],
        "fuentes_web": fuentes_extraidas,
        "imagenes_b64": list(set(todas_imagenes))[:10]
    })

with open("scratch/2_complejos_raw_local.json", "w", encoding="utf-8") as f:
    json.dump(resultados_scraping, f, ensure_ascii=False, indent=2)

print("Scraping completado. Ejecutando evaluate_local...")

import evaluate_local as ev

ev.main(
    input_path="scratch/2_complejos_raw_local.json",
    output_path="scratch/2_complejos_resultados_local.json",
)
