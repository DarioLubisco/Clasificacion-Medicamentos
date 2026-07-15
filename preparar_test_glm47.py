#!/usr/bin/env python3
"""
Prueba del benchmark con solo GLM-4.7 (un producto) para verificar integración.
"""
import json

# Lote de prueba con 1 solo producto
lote_prueba = [
    {
        "registro": {
            "codigo": "7703030140702",
            "codbarras": "7703030140702",
            "descripcion_original": "ACETAMINOFEN TABLETA 500MG X 30",
            "ciclos_reproceso": 0
        },
        "atributos_ya_encontrados": {}
    }
]

print("Lote de prueba (1 producto):")
print(json.dumps(lote_prueba, indent=2, ensure_ascii=False))

# Guardar el lote
with open('lote_prueba_glm47.json', 'w', encoding='utf-8') as f:
    json.dump(lote_prueba, f, indent=2, ensure_ascii=False)

print("\n✅ Lote guardado en 'lote_prueba_glm47.json'")
print("\nPara ejecutar el benchmark solo con GLM-4.7:")
print("1. Modificar benchmark_modelos.py para usar solo el lote de prueba")
print("2. Ejecutar: python3 benchmark_modelos.py")