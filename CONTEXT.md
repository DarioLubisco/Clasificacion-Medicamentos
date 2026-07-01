# CONTEXT.md — Reglas Inquebrantables del Proyecto
> **OBLIGATORIO**: Leer este archivo ANTES de hacer cualquier cambio en el proyecto.
> Última actualización: 2026-06-28

---

## 0. DIRECTIVA ESTRICTA DE AUTONOMÍA CERO
- **PROHIBICIÓN DE EJECUCIÓN**: El agente (incluyendo subagentes) tiene PROHIBIDO ejecutar CUALQUIER comando o script (ej. `python evaluate_optimized_local.py`, tests, etc.) en este entorno sin pedir permiso expreso y explícito al usuario primero.
- **PROHIBICIÓN DE REESTRUCTURACIÓN**: El agente no debe reestructurar, refactorizar, ni modificar la lógica de ejecución del pipeline o de los archivos del proyecto para hacer pruebas o saltar componentes (ej. excluir SQL) sin consultar y recibir aprobación explícita del usuario.
- **CERO ASUNCIONES**: Nunca asumas cómo se debe adaptar el flujo si el usuario menciona un cambio. Pide los requisitos exactos y espera aprobación antes de modificar o ejecutar.

---

## 1. Arquitectura del Pipeline de Evaluación

```
┌─────────────────────────────────────────────────────────────────┐
│                    evaluate_optimized_local.py                   │
│                                                                 │
│  Input: eval_5_combined.json (productos con fuentes web + URLs) │
│                                                                 │
│  │  Califica legibilidad 0-5. Aprobadas: score >= 3 (R3)   │   │
│  │  Salida: fotos_aprobadas (b64), fotos_a_guardar          │   │
└──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      PASO 2: OCR FARMACÉUTICO (Gemini Flash 2.5)         │   │
│  │                                                          │   │
│  │  Extrae TODO el texto visible de cada imagen aprobada:   │   │
│  │  nombre, laboratorio, principio activo, concentración,   │   │
│  │  forma farmacéutica, registro sanitario, lote, etc.      │   │
│  │                                                          │   │
│  │  Salida: transcripciones[] (texto plano por imagen)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      PASO 3: EVALUACIÓN LLM (por modelo activo)          │   │
│  │                                                          │   │
│  │  DeepSeek V4 Pro/Flash (TEXTO ONLY):                     │   │
│  │    ❌ NO recibe imágenes (causa HTTP 404)                 │   │
│  │    ✅ Recibe transcripciones OCR completas (nota_vision)  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      PASO 4: POST-PROCESAMIENTO                          │   │
│  │  - Guardar imágenes en disco (scratch/imagenes_test/)    │   │
│  │  - Calcular score de calidad                             │   │
│  │  - Normalizar segmento_etario                            │   │
│  │  - Guardar JSON incremental + Excel                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Restricciones Inquebrantables (NUNCA violar)

### R1: DeepSeek NO soporta visión
- DeepSeek V4 Pro es un modelo de TEXTO ONLY.
- Enviarle `image_url` en el content payload causa HTTP 404.
- Toda información visual llega a DeepSeek como TEXTO transcrito por Gemini Flash (OCR farmacéutico).
- La función `transcribir_imagenes_gemini()` extrae el texto de las imágenes aprobadas.
- Las transcripciones se inyectan en `nota_vision` entre delimitadores `--- INICIO/FIN TRANSCRIPCIÓN OCR ---`.
- **Aserción en código**: Existe un assert que previene enviar image_url a DeepSeek.

### R2: Fuentes Complementarias (NO prioridad visual)
- Las fuentes de texto web y las imágenes tienen IGUAL PESO.
- NO existe "prioridad visual". Esta regla fue eliminada explícitamente por el usuario.
- Las contradicciones se resuelven por preponderancia de evidencia documentada.

### R5: codigo_atc vs codigo_atc_profundo
- `codigo_atc`: SOLO del catálogo (extraer de corchetes []). Prohibido inferir.
- `codigo_atc_profundo`: SÍ permite inferencia médica (nivel 4-5 ATC).

### R6: Taxonomía cerrada
- El modelo NO puede inventar categorías, subcategorías ni dominios.
- Si no encaja en el catálogo, devolver null con justificación.

### R7: Campo `origen` = solo país soberano
- Prohibido: "Importado", "Nacional", "Genérico", nombres de laboratorios.
- Solo: "VENEZUELA", "COLOMBIA", "USA", "ESPAÑA", etc. o null.

### R8: Insumos Médicos y Especificación Técnica
- Para Insumos Médicos (`dominio: MATERIAL_MEDICO_INSUMO`), la taxonomía se debe mantener limpia y agrupada.
- Los detalles técnicos (calibres, grosores, tallas, diámetros) NUNCA se usan para inventar subcategorías, sino que se extraen de manera pura en el campo `especificacion_tecnica`.
- *Decisión de Arquitectura*: Las columnas SQL para soportar la V2 (`especificacion_tecnica`, `dominio`, `categoria`, `subcategoria`) se difirieron para implementarse cuando haya conexión a la BD, pero los scripts de Python ya cargan el prompt V2.

### R9: Condición de Venta y Psicotrópicos
- El atributo `requiere_recipe` es exclusivamente para medicamentos Psicotrópicos o Estupefacientes controlados.
- Todo lo demás (incluyendo antibióticos) se asume como venta libre por defecto (`requiere_recipe = 0`).

---

## 3. Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `scratch/evaluate_optimized_local.py` | Orquestador principal de evaluación |
| `scratch/prompt_agente_v2.txt` | Template del prompt del agente (separado del .py) |
| `modelos_activos.json` | Configuración de modelos y precios |
| `scratch/taxonomias_local.txt` | Cache local del catálogo de taxonomías |
| `scratch/eval_5_combined.json` | Dataset de entrada (productos + fuentes web + imágenes) |
| `CONTEXT.md` | ESTE ARCHIVO — reglas del proyecto |

---

## 4. Modelos Activos (Catálogo Cerrado)

Solo estos modelos están en uso. No agregar ni referenciar otros sin confirmación del usuario:

| Clave | Model ID OpenRouter | Rol | Visión |
|-------|-------------------|-----|--------|
| deepseek_v4_flash | deepseek/deepseek-v4-flash | Texto (Caballo de batalla principal) | ❌ Solo texto |
| deepseek_v4_pro | deepseek/deepseek-v4-pro | Texto (Rescate/Cuarentena) | ❌ Solo texto |
| gemini_flash_2_5 | google/gemini-2.5-flash | Pre-filtro visual y OCR | ✅ Visión/OCR |

---

## 5. Campos JSON de Salida (Esquema Vigente)

Campos nuevos agregados en la última revisión:
- `volumen_unidad` (Float o Null): Peso/volumen de UNA unidad mínima de dosificación
- `volumen_unidad_medida` (String o Null): Unidad del volumen_unidad
- `atributos_baja_confianza` (Array): Lista de campos con duda
- `alertas_auditoria` (String o Null): Justificación de atributos faltantes

---

## 6. Historial de Decisiones del Usuario

| Fecha | Decisión | Estado |
|-------|----------|--------|
| 2026-06-26 | Bajar umbral de legibilidad de 4 a 3 | ✅ Aplicado |
| 2026-06-26 | Eliminar prioridad visual, usar fuentes complementarias | ✅ Aplicado |
| 2026-06-27 | Agregar campo volumen_unidad | ✅ Aplicado |
| 2026-06-27 | Agregar glosario crítico al prompt | ✅ Aplicado |
| 2026-06-27 | Agregar checklist de verificación al prompt | ✅ Aplicado |
| 2026-06-27 | Ampliar a 5 ejemplos Few-Shot | ✅ Aplicado |
| 2026-06-27 | Scoring de confianza por discrepancia → puntaje final = MIN | ✅ Aplicado |
| 2026-06-27 | Clarificar ATC: catálogo=solo corchetes, profundo=inferencia OK | ✅ Aplicado |
| 2026-06-27 | Separar prompt en archivo independiente | ✅ Aplicado |
| 2026-06-27 | Agregar aserciones defensivas en código | ✅ Aplicado |
| 2026-06-27 | Agregar regla de desambiguación: concentración en imagen vs descripción del EAN | ✅ Aplicado |
| 2026-06-27 | Crear CONTEXT.md | ✅ Este archivo |
| 2026-06-27 | Implementar OCR farmacéutico con Gemini Flash (transcribir_imagenes_gemini) | ✅ Aplicado |
| 2026-06-27 | DeepSeek ahora recibe transcripciones OCR completas en nota_vision | ✅ Aplicado |
| 2026-06-28 | Actualizar reglas: requiere_recipe solo para psicotrópicos, agregar registro_sanitario al prompt | ✅ Aplicado |
| 2026-06-28 | Purga completa de la arquitectura legacy (modelo Gemma borrado, asignación exclusiva a DeepSeek/Gemini) | ✅ Aplicado |
| 2026-06-28 | Implementar compresión automática a .webp con Pillow y nomenclatura por EAN | ✅ Aplicado |
| 2026-06-29 | Activar reasoning effort 'xhigh' por defecto para todos los modelos DeepSeek | ✅ Aplicado |

---

## 7. Variables de Configuración del Pipeline

Para evitar pérdida de información o alucinaciones por dilución de atención en lotes grandes, se define la siguiente configuración global:

```python
# Tamaño de lote (Batch Size) para la llamada al LLM principal
BATCH_SIZE = 1  # Procesamiento estricto "uno por uno"
```

Esta variable define que cada producto se procesa en su propia llamada individual del LLM, lo que incrementa sustancialmente la precisión del modelo DeepSeek V4 Flash.

- **Esfuerzo de Razonamiento (Reasoning Effort)**: Todos los modelos de la familia DeepSeek (incluyendo Flash y Pro) se ejecutan obligatoriamente con el parámetro `"reasoning": {"effort": "xhigh"}` para maximizar la profundidad lógica y justificación clínica de sus clasificaciones.


---

## 8. Gestión de Imágenes y Compresión WebP
- **Formato Obligatorio**: Todas las imágenes descargadas (independiente de su formato original) se convierten activamente en memoria a `.webp` usando la librería `Pillow` de Python con `quality=80`.
- **Estructura Plana**: No se crean subcarpetas por producto. Todas las imágenes aprobadas van al directorio centralizado `scratch/imagenes_productos/`.
- **Nomenclatura**: El archivo se nombra usando el código de barras para acceso directo. Ejemplo: `[EAN].webp`. Si hay secundarias: `[EAN]_2.webp`.
- **Ruta de Base de Datos**: El script que genera SQL inyecta la ruta local al servidor web (`/imagenes/[EAN].webp`) en lugar de rutas externas.
