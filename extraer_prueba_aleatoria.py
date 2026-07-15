#!/usr/bin/env python3
"""
Extrae productos al azar de los archivos JSON existentes y los convierte
al formato esperado por evaluate_local.py
"""
import json
import random
from pathlib import Path

def procesar_producto_limpieza(item):
    """Convierte del formato investigacion_limpieza_v10.json al formato del pipeline"""
    registro = item.get("registro", {})
    return {
        "ean": registro.get("codbarras", ""),
        "descripcion": registro.get("descripcion_original", ""),
        "fuentes_web": [registro.get("fuente_web_consultada", "N/A")],
        "imagenes_b64": []
    }

def procesar_producto_lote2(item):
    """Convierte del formato investigacion_lote2_v10.json al formato del pipeline"""
    registro = item.get("registro", {})
    return {
        "ean": registro.get("codbarras", ""),
        "descripcion": registro.get("desc", ""),
        "fuentes_web": [registro.get("url", "N/A")],
        "imagenes_b64": []
    }

def main():
    print("Extrayendo productos al azar para prueba del pipeline...")

    # Cargar archivos fuente
    archivo1 = "investigacion_limpieza_v10.json"
    archivo2 = "investigacion_lote2_v10.json"

    productos = []

    # Procesar archivo 1
    if Path(archivo1).exists():
        with open(archivo1, "r", encoding="utf-8") as f:
            data1 = json.load(f)
            print(f"  Cargados {len(data1)} productos de {archivo1}")
            for item in data1:
                prod = procesar_producto_limpieza(item)
                if prod["ean"] and prod["descripcion"]:  # Solo productos válidos
                    productos.append(prod)

    # Procesar archivo 2
    if Path(archivo2).exists():
        with open(archivo2, "r", encoding="utf-8") as f:
            data2 = json.load(f)
            print(f"  Cargados {len(data2)} productos de {archivo2}")
            for item in data2:
                prod = procesar_producto_lote2(item)
                if prod["ean"] and prod["descripcion"]:  # Solo productos válidos
                    productos.append(prod)

    print(f"  Total productos válidos: {len(productos)}")

    # Seleccionar al azar
    num_seleccionados = 10
    seleccionados = random.sample(productos, min(num_seleccionados, len(productos)))

    # Guardar
    output_path = "scratch/eval_prueba_10_aleatorios.json"
    Path("scratch").mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(seleccionados, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(seleccionados)} productos seleccionados al azar:")
    for i, prod in enumerate(seleccionados, 1):
        print(f"  {i}. EAN: {prod['ean']} - {prod['descripcion']}")

    print(f"\n✓ Guardado en: {output_path}")

if __name__ == "__main__":
    main()