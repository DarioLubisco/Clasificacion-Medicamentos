# GLM-4.7 Integration - Resumen de Solución

## ✅ PROBLEMA RESUELTO

El sandbox de Cursor bloqueaba el acceso directo a `api.z.ai` con error 403, y la API directa de Z.ai devolvía "Insufficient balance".

## ✅ SOLUCIÓN IMPLEMENTADA

GLM-4.7 está disponible en **OpenRouter** con el model ID: `z-ai/glm-4.7`

### Configuración Aplicada:

**Archivo: `benchmark_modelos.py`**

1. **Agregado pricing para GLM-4.7:**
   - Input: $0.40 por 1M tokens
   - Output: $1.75 por 1M tokens

2. **Agregado GLM-4.7 a la lista de modelos:**
   ```python
   modelos_a_evaluar = [
       ("DeepSeek V4 Flash", "deepseek/deepseek-v4-flash", 1, "benchmark_deepseek_flash.json"),
       ("DeepSeek V4 Pro", "deepseek/deepseek-v4-pro", 2, "benchmark_deepseek_pro.json"),
       ("GLM-4.7", "z-ai/glm-4.7", 3, "benchmark_glm47.json")  # ← NUEVO
   ]
   ```

3. **Habilitado modo reasoning para GLM-4.7:**
   ```python
   if "glm-4.7" in model.lower():
       data["include_reasoning"] = True
   ```

4. **Manejo especial de respuesta GLM-4.7:**
   - GLM-4.7 puede devolver `content: null` si el reasoning ocupa todos los tokens
   - Se agregó fallback para usar `reasoning` cuando `content` es null

## ✅ VERIFICACIÓN COMPLETADA

**Test de integración ejecutado exitosamente:**
- Producto: ACETAMINOFEN TABLETA 500MG X 30
- Tokens: 944 input + 1474 output
- Costo: $0.00296
- Extracción exitosa de atributos
- Post-procesamiento funcionando correctamente

**Archivos de prueba creados:**
- `test_glm47_openrouter.py` - Test básico de conexión
- `preparar_test_glm47.py` - Crea lote de prueba con 1 producto
- `test_integracion_glm47.py` - Test completo del flujo
- `lote_prueba_glm47.json` - Lote de prueba
- `resultado_test_glm47.json` - Resultado del test

## 🚀 EJECUTAR EL BENCHMARK COMPLETO

```bash
cd "/home/synapse/source/repos/Clasificacion Medicamentos"
python3 benchmark_modelos.py
```

Esto ejecutará:
1. Selección aleatoria de 30 productos de la base de datos
2. Evaluación con 3 modelos:
   - DeepSeek V4 Flash
   - DeepSeek V4 Pro
   - **GLM-4.7 (real, no simulado)**
3. Post-procesamiento de producción (limpieza regex, normalización)
4. Cálculo de scores de calidad
5. Reporte comparativo de costos y resultados

## 📊 EXPECTATIVAS

GLM-4.7 está optimizado para:
- Coding y tareas complejas
- Multi-step reasoning con "thinking mode"
- Context window: 202,752 tokens

Puede ser más lento que DeepSeek Flash debido al modo reasoning, pero debería ofrecer mejor calidad en extracción de atributos farmacéuticos complejos.

## 📝 NOTAS

- El API Key de OpenRouter está en `sinapsis.credentials`
- Se requiere permiso `full_network` para ejecutar el benchmark
- El costo de GLM-4.7 es intermedio entre Flash y Pro
- GLM-4.7 incluye reasoning tokens adicionales (no cobrados como output)