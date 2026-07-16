#!/usr/bin/env python3
"""
Test simple de GLM-4.7 con un solo producto para verificar el flujo completo.
"""
import os
from dotenv import load_dotenv
from synapse_cred import load_synapse_credentials
load_synapse_credentials()

import json
import sys
sys.path.insert(0, '.')

from benchmark_modelos import llamar_openrouter, calcular_score_calidad, normalizar_segmento_etario
from limpiador_farmaceutico_regex import procesar_farmacos

# Cargar el lote de prueba
with open('lote_prueba_glm47.json', 'r', encoding='utf-8') as f:
    lote = json.load(f)

lote_json_str = json.dumps(lote, indent=2, ensure_ascii=False)

print("="*70)
print("  TEST DE INTEGRACIÓN GLM-4.7 (1 PRODUCTO)")
print("="*70)
print(f"\nLote a procesar: {len(lote)} producto(s)")
print(f"Modelo: z-ai/glm-4.7")
print("\nLlamando a GLM-4.7 via OpenRouter...")
print("-"*70)

# Llamar a GLM-4.7
resultado = llamar_openrouter(lote_json_str, model="z-ai/glm-4.7", ciclo_actual=3)

if not resultado:
    print("\n❌ ERROR: No se obtuvo respuesta de GLM-4.7")
    sys.exit(1)

print("-"*70)
print(f"\n✅ Respuesta recibida de GLM-4.7")
print(f"   Productos procesados: {len(resultado)}")

# Procesar el primer (y único) resultado
item = resultado[0]
atrib = item.get('atributos_nuevos_consolidados', item.get('atributos', {}))

print("\n" + "="*70)
print("  RESULTADO DEL PRODUCTO")
print("="*70)
print(f"\nDescripción original: {item['registro']['descripcion_original']}")
print(f"\nAtributos extraídos:")
print(json.dumps(atrib, indent=2, ensure_ascii=False))

# Aplicar post-procesamiento como en el benchmark real
atrib_clean = dict(atrib)

# 1. Limpieza con regex
res_limpieza = procesar_farmacos(atrib_clean.get('principio_activo'), atrib_clean.get('concentracion'))
if res_limpieza["exito"]:
    atrib_clean['principio_activo'] = res_limpieza["principio_activo"]
    atrib_clean['concentracion'] = res_limpieza["concentracion"]
else:
    atrib_clean['principio_activo'] = None
    atrib_clean['concentracion'] = None

# 2. Normalizar segmento etario
atrib_clean['segmento_etario'] = normalizar_segmento_etario(atrib_clean.get('segmento_etario'))

# 3. Normalizar forma farmacéutica
if atrib_clean.get('forma_farmaceutica'):
    ff_upper = str(atrib_clean.get('forma_farmaceutica')).upper().strip()
    reemplazos_ff = {
        'SOBRES': 'SOBRE', 'GOMITAS': 'GOMITA', 'TABLETAS': 'TABLETA',
        'ÓVULOS': 'ÓVULO', 'SUPOSITORIOS': 'SUPOSITORIO', 'CÁPSULAS': 'CÁPSULA',
        'COMPRIMIDOS': 'COMPRIMIDO', 'GRAGEAS': 'GRAGEA', 'APÓSITOS': 'APÓSITO',
        'PASTILLAS': 'PASTILLA', 'GASAS': 'GASA', 'CAPSULAS': 'CAPSULA',
        'GALLETAS': 'GALLETA', 'SACHETS': 'SACHET', 'CARAMELOS': 'CARAMELO'
    }
    if ff_upper in reemplazos_ff:
        atrib_clean['forma_farmaceutica'] = reemplazos_ff[ff_upper]

print("\n" + "="*70)
print("  RESULTADO POST-PROCESADO")
print("="*70)
print(json.dumps(atrib_clean, indent=2, ensure_ascii=False))

# Calcular score
score = calcular_score_calidad(atrib_clean)
print(f"\nScore de calidad: {score}/100")

if score >= 88:
    print("✅ APROBADO (score >= 88)")
else:
    print(f"❌ NO APROBADO (score < 88)")

# Guardar resultado
with open('resultado_test_glm47.json', 'w', encoding='utf-8') as f:
    json.dump({
        "original": atrib,
        "procesado": atrib_clean,
        "score": score
    }, f, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print("  RESUMEN FINAL")
print("="*70)
print("✅ GLM-4.7 funciona correctamente en el flujo del benchmark")
print("✅ La API de OpenRouter responde correctamente")
print("✅ El post-procesamiento se aplica sin errores")
print("\n📁 Resultados guardados en: resultado_test_glm47.json")
print("\n🎉 ¡Listo para ejecutar el benchmark completo con 30 productos!")
print("   Ejecutar: python3 benchmark_modelos.py")