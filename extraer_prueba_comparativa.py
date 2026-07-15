#!/usr/bin/env python3
"""
Extrae 10 productos de resultados_deepseek para el experimento comparativo
Batch=1 vs Batch=5 con GLM-4.7 + Gemini Vision
"""
import json
import random
from pathlib import Path

def main():
    print("="*80)
    print("EXTRAYENDO 10 PRODUCTOS PARA EXPERIMENTO COMPARATIVO")
    print("="*80)

    # Cargar resultados de DeepSeek
    input_path = "scratch/resultados_20_hard.json"
    if not Path(input_path).exists():
        print(f"Error: No se encuentra {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        resultados_deepseek = json.load(f)

    print(f"Productos disponibles: {len(resultados_deepseek)}")

    # Seleccionar 10 productos al azar
    productos_seleccionados = list(resultados_deepseek.keys())
    random.shuffle(productos_seleccionados)
    productos_seleccionados = productos_seleccionados[:10]

    # Reconstruir formato de entrada para el pipeline
    productos_para_pipeline = []

    for ean in productos_seleccionados:
        producto_resultado = resultados_deepseek[ean]
        descripcion = producto_resultado["descripcion"]

        # Reconstruir formato de entrada original
        producto_input = {
            "ean": ean,
            "descripcion": descripcion,
            "fuentes_web": [
                "N/A (sin fuentes web disponibles - prueba comparativa)",
                f"Referencia: {descripcion}"
            ],
            "imagenes_b64": []  # Sin imágenes para esta prueba inicial
        }

        productos_para_pipeline.append(producto_input)

    # Guardar en formato JSON
    output_path = "scratch/eval_comparativa_10.json"
    Path("scratch").mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(productos_para_pipeline, f, indent=2, ensure_ascii=False)

    print(f"\n✓ {len(productos_para_pipeline)} productos seleccionados:")
    for i, prod in enumerate(productos_para_pipeline, 1):
        print(f"  {i}. EAN: {prod['ean']} - {prod['descripcion']}")

    print(f"\n✓ Guardado en: {output_path}")
    print(f"✓ Resultados de referencia (DeepSeek): {input_path}")
    print("\n" + "="*80)
    print("LISTO PARA EXPERIMENTO COMPARATIVO")
    print("="*80)

if __name__ == "__main__":
    main()