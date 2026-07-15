# CONTEXT.md — Reglas Inquebrantables del Proyecto
> **OBLIGATORIO**: Leer este archivo ANTES de hacer cualquier cambio en el proyecto.
> Última actualización: 2026-07-15

---

## 0. DIRECTIVA ESTRICTA DE AUTONOMÍA CERO
- **PROHIBICIÓN DE EJECUCIÓN**: El agente (incluyendo subagentes) tiene PROHIBIDO ejecutar CUALQUIER comando o script (ej. `python evaluate_local.py`, `python run_experimento.py`, tests, etc.) en este entorno sin pedir permiso expreso y explícito al usuario primero.
- **PROHIBICIÓN DE REESTRUCTURACIÓN**: El agente no debe reestructurar, refactorizar, ni modificar la lógica de ejecución del pipeline o de los archivos del proyecto para hacer pruebas o saltar componentes (ej. excluir SQL) sin consultar y recibir aprobación explícita del usuario.
- **CERO ASUNCIONES**: Nunca asumas cómo se debe adaptar el flujo si el usuario menciona un cambio. Pide los requisitos exactos y espera aprobación antes de modificar o ejecutar.

---

## 1. Arquitectura del Pipeline de Evaluación

```
┌─────────────────────────────────────────────────────────────────┐
│                    evaluate_local.py                             │
│                                                                 │
│  Input: eval_5_combined.json (productos con fuentes web + URLs) │
│                                                                 │
│  │  Califica legibilidad 0-5. Aprobadas: score >= 3 (R3)   │   │
│  │  Salida: fotos_aprobadas (b64), fotos_a_guardar          │   │
└──────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │      PASO 2: OCR FARMACÉUTICO (MiMo v2.5)              │   │
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
- Toda información visual llega al LLM de texto como TEXTO transcrito por MiMo (OCR farmacéutico, vía `transcribir_imagenes_vision()`).
- La función `transcribir_imagenes_vision()` (alias legacy `transcribir_imagenes_gemini`) extrae el texto de las imágenes aprobadas.
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

### R10: Consenso de 2 Imágenes sobreescribe el EAN
- Cuando 2+ imágenes independientes (de distinto dominio, garantizado por scraper) reportan el mismo valor para un atributo (concentración, fabricante, marca, forma_farm., cantidad, registro_sanitario) Y ese valor difiere del declarado en `descripcion_original`, el **consenso de imágenes PREVALECE** sobre el EAN.
- Aplica a **todos los atributos incluida concentración**.
- `confianza_nivel` se capa a máximo 4 cuando aplica.
- Excepciones: menos de 2 imágenes, valores contradictorios entre imágenes, sin imágenes aprobadas.
- La regla de "EAN siempre gana en concentración" fue **eliminada** y reemplazada por esta.

### R11: Búsqueda EAN-exacto (no descripción)
- La búsqueda web se hace con `f'"{codbarras}" {descripcion}'` (EAN entrecomillado + descripción).
- Si la búsqueda por EAN no devuelve resultados, **se aborta** (no se cae a descripción) para evitar falsos positivos.
- Cross-check semántico de capa 1 (coincidencia principio activo/fabricante en OCR) ha sido **REVERTIDO**: era útil para búsqueda por descripción pero rechaza imágenes válidas cuando se busca por EAN-exacto.

---

## 3. Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `evaluate_local.py` | Orquestador principal (visión + web + LLM) |
| `orquestador_scraper.py` | Fase 1: búsqueda web e imágenes |
| `deepseek_client.py` | Cliente DeepSeek nativo (api.deepseek.com, reasoning_effort=max) |
| `zai_client.py` | Cliente GLM-4.7 vía Z.ai Coding Plan |
| `run_experimento.py` | Runner controlado por `experimento.conf` |
| `prompt_agente_v3_solidificado_final.txt` | Prompt canónico (versión auditada 2026-07-15) |
| `scratch/prompt_agente_v2.txt` | Template del prompt del agente (separado del .py) |
| `scratch/taxonomias_local.txt` | Cache local del catálogo de taxonomías |
| `scratch/eval_test_a_real.json` | Dataset de 5 EANs reales (Cialis, Bisoprolol, OMMUNAL, Ceftriaxona, Rifaximina) |
| `scratch/run_test_a_real.py` | Generador del dataset con EAN-exacto + dedup por dominio |
| `modelos_activos.json` | Configuración de modelos y precios |
| `CONTEXT.md` | ESTE ARCHIVO — reglas del proyecto |

---

## 4. Modelos Activos (Catálogo Cerrado)

Solo estos modelos están en uso. No agregar ni referenciar otros sin confirmación del usuario:

| Clave | Conexión | Rol | Visión |
|-------|---------|-----|--------|
| deepseek_v4_flash | API nativa api.deepseek.com | Texto (Caballo de batalla principal) | ❌ Solo texto |
| deepseek_v4_pro | API nativa api.deepseek.com | Texto (Rescate/Cuarentena) | ❌ Solo texto |
| glm_4_7 | Z.ai Coding Plan (api.z.ai/coding/paas/v4) | Texto (alternativa principal) | ❌ Solo texto |
| mimo_v2_5 | MiMo Token Plan (api token-plan-sgp) | Pre-filtro visual y OCR | ✅ Visión/OCR |

**DeepSeek V4 Flash** (nativo, no OpenRouter):
- reasoning_effort = "max" (mapeo nativo del "xhigh" del proyecto)
- thinking = enabled
- max_tokens = 16384 (budget amplio para razonar + JSON)
- temperature/top_p son NO-OP en thinking mode — no se envían

**GLM-4.7** (Z.ai Coding Plan):
- reasoning activado por defecto en el endpoint
- timeout = 300s (el prompt auditado exige más razonamiento)
- max_tokens = 4000

**MiMo v2.5** (pre-filtro + OCR):
- role: pre-filtro de imágenes (score 0-5) + OCR farmacéutico
- Las imágenes NO se envían al LLM de texto; solo sus transcripciones OCR via nota_vision.

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
| 2026-06-27 | Agregar regla de desambiguación: concentración en imagen vs descripción del EAN | ❌ REEMPLAZADA por R10 |
| 2026-06-27 | Crear CONTEXT.md | ✅ Este archivo |
| 2026-06-27 | Implementar OCR farmacéutico con Gemini Flash (transcribir_imagenes_gemini) | ✅ Aplicado (ahora MiMo) |
| 2026-06-27 | DeepSeek ahora recibe transcripciones OCR completas en nota_vision | ✅ Aplicado |
| 2026-06-28 | Actualizar reglas: requiere_recipe solo para psicotrópicos, agregar registro_sanitario al prompt | ✅ Aplicado |
| 2026-06-28 | Purga completa de la arquitectura legacy (modelo Gemma borrado, asignación a MiMo/DeepSeek/GLM) | ✅ Aplicado |
| 2026-06-28 | Implementar compresión automática a .webp con Pillow y nomenclatura por EAN | ✅ Aplicado |
| 2026-06-29 | Activar reasoning effort 'xhigh' por defecto para todos los modelos DeepSeek | ✅ Aplicado (nativo: max) |
| --- | **Sesión 2026-07-15 — Refactor profundo** | --- |
| 2026-07-15 | Migrar DeepSeek de OpenRouter a API nativa (api.deepseek.com) | ✅ Aplicado |
| 2026-07-15 | Crear deepseek_client.py con reasoning_effort=max, thinking enabled, max_tokens=16384, sin temp/top_p | ✅ Aplicado |
| 2026-07-15 | Revertir capa 1 (cross-check semántico tokens EAN vs OCR) — dañino con búsqueda EAN-exacto | ✅ Aplicado |
| 2026-07-15 | Conservar capa 2 (post-validación: si fabricante/marca en baja_confianza → cap confianza a ≤3) | ✅ Aplicado |
| 2026-07-15 | Promover capa 3 (cláusula fabricante/marca en conflicto generada por skill generador-de-prompts) | ✅ Aplicado |
| 2026-07-15 | Auditar prompt completo con generador-de-prompts (GLM-5.2): 4 contradicciones + 3 inconsistencias corregidas | ✅ Aplicado |
| 2026-07-15 | Reemplazar regla "EAN siempre gana en concentración" por Régimen de Consenso de 2 Imágenes (R10) | ✅ Aplicado |
| 2026-07-15 | Corregir checklist y ejemplos few-shot que contradecían las reglas (Ej1: Calox, Ej2: 27.9g) | ✅ Aplicado |
| 2026-07-15 | Añadir jerarquía de caps de confianza (cap más restrictivo prevalece cuando aplican varios) | ✅ Aplicado |
| 2026-07-15 | Clarificar contradicción §1 vs §2 del prompt (confianza = min críticos + excepciones aditivas) | ✅ Aplicado |
| 2026-07-15 | Subir max_imagenes_ocr de 3 a 4 (permitir 4 imágenes aprobadas para consenso) | ✅ Aplicado |
| 2026-07-15 | Implementar deduplicación de imágenes por dominio (1 imagen por página para independencia) | ✅ Aplicado |
| 2026-07-15 | Hacer robusto extract_json_from_content para envolturas &lt;analisis_clinico&gt; de DeepSeek | ✅ Aplicado |
| 2026-07-15 | Subir timeout de GLM-4.7 de 180s a 300s (el prompt auditado exige más razonamiento) | ✅ Aplicado |
| 2026-07-15 | Actualizar SKILL.md global/local + .env.example (GLM-5.2/Z.ai, no DeepSeek/OpenRouter) | ✅ Aplicado |
| 2026-07-15 | Reset DB: DROP 2 backups viejos, backup nuevo BKP_20260715_1533, reset 16,387 productos a solo codbarras+descrip1art | ✅ Aplicado |
| 2026-07-15 | Test final: DeepSeek auditado 19/25, GLM auditado 18/25 (5 EANs reales vs tabla Procurement) | ✅ Medido |

---

## 7. Variables de Configuración del Pipeline

Para evitar pérdida de información o alucinaciones por dilución de atención en lotes grandes, se define la siguiente configuración global:

```python
# Tamaño de lote (Batch Size) para la llamada al LLM principal
BATCH_SIZE = 1  # Procesamiento estricto "uno por uno"
```

Esta variable define que cada producto se procesa en su propia llamada individual del LLM.

- **Tamaño de lote**: BATCH_SIZE = 1 (procesamiento uno por uno).
- **Modelo de texto activo**: `EXPERIMENT_TEXTO_PROVIDER` = `glm` (default) o `deepseek`.
- **DeepSeek**: `reasoning_effort` = `max` (thinking enabled), `max_tokens` = 16384.
  `temperature` y `top_p` son NO-OP en thinking mode — no se envían.
- **GLM-4.7**: razona por defecto en el endpoint de Z.ai. `max_tokens` = 4000. `timeout` = 300s.
- **Visión (MiMo)**: `max_imagenes_prefiltro` = 10, `max_imagenes_ocr` = 4, `umbral_legibilidad` = 3.
- **Pre-filtro**: score 0-5 puro (SIN cross-check semántico — capa 1 revertida el 2026-07-15).
- **Independencia de imágenes**: scraper devuelve solo 1 imagen por página (la de mejor score de proximidad con la descripción). El dataset que acumula imágenes lo hace con deduplicación por dominio.
- **Post-validación (capa 2)**: tras GLM, si `fabricante` o `marca` ∈ `atributos_baja_confianza`, forzar `confianza_nivel = min(., 3)`.
- **Extract JSON**: `extract_json_from_content()` busca `[\s*{` (array JSON real) en vez del primer `[` suelto, manejando envolturas `<analisis_clinico>` y markdown.
- **Prompt**: regla de consenso de 2+ imágenes independientes sobreescribe el EAN en todos los atributos. Jerarquía de caps: cuando aplican múltiples caps (consenso, fabricante/marca), prevalece el más restrictivo (número menor).


---

## 8. Gestión de Imágenes e Independencia de Fuentes
- **Pre-filtro**: MiMo puntúa cada imagen 0-5. Aprobadas: >= 3. Máx 10 imágenes evaluadas, máx 4 aprobadas.
- **Independencia**: el scraper (`orquestador_scraper.py`) selecciona solo la mejor imagen por página (mayor score de proximidad con la descripción). El dataset (`run_test_a_real.py`, `run_20_vision.py`) acumula imágenes deduplicando por dominio — garantiza que 4 imágenes aprobadas vengan de 4 fuentes independientes.
- **OCR**: MiMo extrae el texto de cada imagen aprobada. Transcripciones etiquetadas `[Imagen 1]`, `[Imagen 2]`, etc.
- **Las imágenes NO se envían al LLM de texto**: solo sus transcripciones OCR via `nota_vision` entre delimitadores `--- INICIO/FIN TRANSCRIPCIÓN OCR ---`.
- **Formato Obligatorio**: Todas las imágenes descargadas se convierten en memoria a `.webp` usando Pillow con `quality=80`.
- **Estructura Plana**: No se crean subcarpetas por producto. Todas las imágenes aprobadas van al directorio `scratch/imagenes_productos/`.
- **Nomenclatura**: `[EAN].webp`. Si hay secundarias: `[EAN]_2.webp`.
- **Ruta de Base de Datos**: El script SQL inyecta la ruta local al servidor web (`/imagenes/[EAN].webp`).

---

## 9. Estado de la Base de Datos (Procurement.por_aprobacion_equivalencias)

### Último reset: 2026-07-15

La base de datos fue reseteada completamente. Estado actual:

- **16,387 productos** con solo `codbarras` y `descrip1art` poblados.
- **Todos los demás campos NULL o default** (fabricante_Des, marca_Des, principio_activo_Des, concentracion_Des, estado_ciclo='pendiente', procesado_fase1=0, etc.).
- **Backup disponible**: `Procurement.por_aprobacion_equivalencias_BKP_20260715_1533` (misma estructura, 16,387 filas con datos anteriores).
- **Backups anteriores eliminados**: `backup_20260618` y `BKP_20260624_131902` fueron DROPPED.
- **Estado para reprocesar**: todos los productos están en `estado_ciclo='pendiente'`, `procesado_fase1=0`, `procesado_fase2=0`. Listos para re-procesar desde el scraper (EAN-internet) hasta la extracción LLM con el nuevo prompt auditado.
