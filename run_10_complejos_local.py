import os
import json
import sys

# 1. Lista de EANs
eans_test = [
    {"ean": "000000000130", "desc": "Ondansetrón 4 mg/2 ml solución inyectable, 10 ampollas"},
    {"ean": "0000000107839", "desc": "Vancomicina 1 g polvo para solución inyectable I.V. x 10 ampollas"},
    {"ean": "0000000201629", "desc": "Metotrexato 50 mg/2 ml solución inyectable (IV/IM) en ampolla."},
    {"ean": "0000001100181", "desc": "Jarabe de Passiflora Plus de 180 ml de Farmagenik."},
    {"ean": "0000001100198", "desc": "Senolax Jarabe 120 ml Farmagenik"},
    {"ean": "0000025525748", "desc": "Jarabe de berro Farmagenik 120 ml"},
    {"ean": "0000025525755", "desc": "Jarabe de achicoria Farmagenik 120 ml"},
    {"ean": "0000042419860", "desc": "NIVEA Crema de Manos 3 en 1 Antibacterial Cuidado y Protección 75 ml"}, # NO MEDICINA
    {"ean": "5600360014096", "desc": "Clavoxilin 600 mg/42,9 mg/5 mL suspensión oral con amoxicilina y ácido clavulánico, 100 mL."},
    {"ean": "7269144920428", "desc": "OTOLYS (Ciprofloxacina + Hidrocortisona) 5ml Suspensión Ótica"}
]

# Modificar evaluate_optimized temporalmente para leer de este json en vez de la BD.
# Generar el JSON dummy como si hubiera venido del scraper.
import orquestador_scraper_v11_local as scrap

resultados_scraping = []
for item in eans_test:
    print(f"Scrapeando {item['ean']}...")
    # El procesar_lote_db normal extrae del BD, no toma EANs por parámetro en v11.
    # Usaremos directamente la función scrap.buscar_en_internet y procesar
    
    fuentes_extraidas = []
    todas_imagenes = []
    
    # Búsqueda web
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

with open("scratch/10_complejos_raw_local.json", "w", encoding="utf-8") as f:
    json.dump(resultados_scraping, f, ensure_ascii=False, indent=2)

print("Scraping completado. Ejecutando evaluate_optimized...")

# Inyectar el json_path a evaluate_optimized
import scratch.evaluate_optimized_local as ev

ev.main(input_path="scratch/10_complejos_raw_local.json", comp_path="scratch/10_complejos_resultados_local.json", excel_path="scratch/10_complejos_excel_local.xlsx")
