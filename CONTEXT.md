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
| `prompt_agente_v3_solidificado_final.txt` | Prompt canónico (bugfix + optimización Opus 4.8, 2026-07-20; 244 líneas) |
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
| --- | **Sesión 2026-07-20 — Bugfix del prompt + optimización Opus 4.8** | --- |
| 2026-07-20 | Bug 1 + re-grounding: ejemplos few-shot usaban tuplas dominio/categoría/subcategoría inventadas (`subcategoria:"IBUPROFENO"`) que no existen en el catálogo; reconstruidos con tuplas REALES de `taxonomias_local.txt` y `codigo_atc` extraído de los corchetes `[ATC]` | ✅ Aplicado |
| 2026-07-20 | Bug 2: ejemplos 7 y 8 completados con las 27 llaves del diccionario + wrapper `registro` (anti-key-dropping); Ej7 `codigo_atc` null→"A03B"; Ej8 concretado (Paracetamol [N02B], conflicto marca/fabricante cap 3) | ✅ Aplicado |
| 2026-07-20 | Bug 3: `contenido_neto` redefinido sin la contradicción "Float … entero sin decimales" (ahora conserva decimales reales) | ✅ Aplicado |
| 2026-07-20 | Bug 4: `segmento_etario` puesto a null en ejemplos sin palabra clave etaria explícita (§4.5, prohibido deducir) | ✅ Aplicado |
| 2026-07-20 | Migrar `generador.py` del skill generador-de-prompts a Claude Opus 4.8 (API Anthropic, key ANTHROPIC_OPUS_4_8_SONNET_5_API_KEY) por rate-limit de Z.ai GLM-5.2 | ✅ Aplicado |
| 2026-07-20 | Optimizar el prompt corregido con Opus 4.8 (43KB→30KB): estructura Markdown, few-shot minificados; verificado que preserva placeholders, 27 llaves, tuplas del catálogo y los 4 bugfixes. Adoptado como canónico | ✅ Aplicado |

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

### Última actualización: 2026-07-19

- **16,388 filas totales** en la tabla.
- **2 columnas pobladas universalmente**: `codbarras` + `descrip1art` (nunca NULL).
- **Backup disponible**: `Procurement.por_aprobacion_equivalencias_BKP_20260715_1533` (estructura previa al reset del 2026-07-15).

### Distribución por `estado_ciclo`

| estado_ciclo | Cantidad | Última modificación | Qué significa |
|---|---|---|---|
| `pendiente` | 13,219 | 2026-07-15 16:43 | Nunca entró al orquestador |
| `ABIERTO` | 3,169 | 2026-07-18 02:22 | En cola activa del orquestador |
| `CERRADO` | 0 | — | (se llena al clasificar con score ≥ umbral) |
| `AGOTADO` | 0 | — | (se llena tras 3 reintentos fallidos) |
| `NULL` | 0 | — | — |

### Origen de los datos

Cruce confirmado por `codigo_barras` contra `Analitica.Mercado_Vivo` (con DISTINCT para no duplicar por sucursal):

| estado_ciclo | Total | En Mercado_Vivo | No encontrados |
|---|---|---|---|
| `ABIERTO` | 3,169 | 2,482 (78%) | 687 |
| `pendiente` | 13,219 | 11,252 (85%) | 1,967 |

**Conclusión**: la mayoría de los productos provienen de Mercado Vivo, sin distinción entre `ABIERTO` y `pendiente`. La tabla `dbo.productos` (con `codigo_barras`) **NO** crusa — 0 coincidencias en ambos sentidos, no es SAPROD.

### Distribución por tipo de código de barras

| Tipo | Cantidad | % | Scrapeable |
|---|---|---|---|
| EAN-13 (13 dígitos) | 13,544 | 82.6% | ✅ |
| UPC-A (12 dígitos) | 1,378 | 8.4% | ✅ (se scrapea igual) |
| ITF-14 (14 dígitos) | 228 | 1.4% | ⚠️ es de caja, no unidad |
| EAN-8 (8 dígitos) | 214 | 1.3% | ✅ (formato corto GS1) |
| Códigos internos cortos (1-5 díg) | 113 | 0.7% | ❌ |
| `BLI_*` | 102 | 0.6% | ❌ |
| Otros | 704 | 4.3% | Mixto |

### Tablas de trazabilidad (4)

| Tabla | Filas | Propósito |
|---|---|---|
| `Procurement.OrquestadorLog` | 0 (limpia 2026-07-19) | Log de alertas INFO/WARN/ERROR |
| `Procurement.OrquestadorLLMLog` | 0 (limpia 2026-07-19) | Trazabilidad LLM: prompt, raw, reasoning, tokens, costo |
| `Procurement.Imagenes_Productos_Crudas` | 0 (limpia 2026-07-19) | URLs + score de legibilidad por imagen |
| `Procurement.scraping_farmacias_raw` | 0 (limpia 2026-07-19) | URLs + texto extraído por fuente web |

Las 4 tablas fueron vaciadas el 2026-07-19 al detectarse logs huérfanos (apuntaban a `LogID`s que ya no existían en `OrquestadorLLMLog`).

---

## 10. Ciclo de vida del `estado_ciclo` y del disparo del trigger

### Máquina de estados

```
                  [carga inicial externa]
                          │
                          ▼
                    ┌───────────┐
                    │ pendiente │  ◄── estado de fábrica tras reset
                    └───────────┘
                          │
                  [PROMOCIÓN MANUAL]
                   (ver §10.2 abajo)
                          │
                          ▼
   ┌──────────────────────────────────────┐
   │ estado_ciclo = 'ABIERTO'             │ ◄── SOLO ESTE ENTRA AL ORQUESTADOR
   │ (orquestador_produccion.py:89)       │
   └──────────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────┐
            │  Procesa batch (5 prod) │
            │  scraping + MiMo + GLM  │
            │  calcula score_calidad  │
            └─────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
      score ≥ 88 (med)             score < 88
      o ≥ 70 (no-med)                   │
            │                           ▼
            ▼                   ¿ciclos_reproceso ≥ 3?
      ┌──────────┐              ┌───────┴───────┐
      │ CERRADO  │              ▼               ▼
      └──────────┘          ABIERTO          AGOTADO
      (FINAL ✅)            ciclos+1          (FINAL ❌)
                            (sigue en cola)
```

### 10.1 Transiciones que SÍ hace el orquestador

Implementadas en `orquestador_produccion.py:251-259` (`build_update_clauses`):

| Condición | estado_ciclo resultante |
|---|---|
| `score >= 88` (medicamento) o `>= 70` (no-medicamento) | `CERRADO` |
| `score < umbral` Y `ciclos_reproceso < 3` | `ABIERTO` con `ciclos_reproceso + 1` |
| `score < umbral` Y `ciclos_reproceso >= 3` | `AGOTADO` |

Umbrales (`SCORE_CIERRE`, `SCORE_CIERRE_NO_MED`, `MAX_REINTENTOS`) configurables desde `.env`.

### 10.2 GAP ARQUITECTÓNICO — la transición `pendiente → ABIERTO` no tiene ejecutor

**Hallazgo crítico (auditado 2026-07-19)**: ningún script del repositorio ejecuta `UPDATE ... SET estado_ciclo = 'ABIERTO' WHERE estado_ciclo = 'pendiente'`. La búsqueda se hizo con patrones `UPDATE.*ABIERTO`, `SET.*ABIERTO`, `UPDATE.*pendiente` en todos los `.py` y `.sql` — cero resultados.

- `etl_mercado_vivo_incremental.py:95-99` hace el único INSERT de la tabla pero **sin** `estado_ciclo` → las filas nuevas quedan `NULL`, no `pendiente`.
- El `'pendiente'` textual masivo (13.219 filas con `LastUpdated=2026-07-15 16:43`) fue un **reset SQL manual externo** — el script no está en el repo.
- El orquestador solo filtra `WHERE estado_ciclo = 'ABIERTO'` (`orquestador_produccion.py:89`) — no acepta `NULL` ni `pendiente`.
- Un workflow n8n `[PROD] Agente Clasificador (Automatico)` (`/home/synapse/source/N8N/workflows/AAnxxGYtgg5sD0o8.json`) existe pero está **INACTIVO** y su filtro es por `origen_dato IS NULL`, no por `estado_ciclo`.
- No hay triggers SQL, ni cron, ni systemd timer, ni schedule activo que mueva `pendiente → ABIERTO`.

**Implicación operativa**: para que el orquestador procese los 13.219 `pendiente`, alguien o algo externo al repo debe ejecutar manualmente un UPDATE como:

```sql
UPDATE Procurement.por_aprobacion_equivalencias
SET estado_ciclo = 'ABIERTO'
WHERE estado_ciclo = 'pendiente'
  AND <criterio_de_promocion>;  -- ej: AND LEN(codbarras) = 13
```

Ese `<criterio_de_promocion>` no está definido en ningún archivo — es decisión operativa pendiente.

### 10.3 Mecanismo de disparo del trigger

- `Config.AutomationTriggers` define los triggers (TriggerID 1 = MDM_Farmaceutico_Scraper, IsActive=true).
- `CheckQuery` del TriggerID 1: `SELECT COUNT(*) FROM por_aprobacion_equivalencias WHERE estado_ciclo = 'ABIERTO'`. Se dispara si `count >= ThresholdValue (1)`.
- `LastTriggered = 2026-07-14` — el último disparo real fue hace 5 días.
- **No hay polling automático**: no hay proceso que lea `AutomationTriggers`, ejecute `CheckQuery`, y dispare `ActionCommand`. Ese mecanismo (antes `synapse-api` en `10.147.18.204:8012`) está caído.
- `ActionCommand` apunta a `http://10.147.18.204:8012/api/orquestador/start` — URL muerta. El reemplazo legítimo es `orquestador_local_api.py` (FastAPI en `:8012`) que recibe POST con la fila del trigger y ejecuta `handle_trigger` en background.

### 10.4 Orden de selección dentro de ABIERTO

`fetch_productos_abiertos` (`orquestador_produccion.py:88-94`) ordena:

```sql
ORDER BY
    -- EAN-13 primero (scrapeables), códigos internos al final (GLM solo)
    CASE WHEN LEN(codbarras) = 13 AND codbarras NOT LIKE 'BLI_%' THEN 0 ELSE 1 END,
    ISNULL(LastUpdated, '1900-01-01') ASC
```

- **Grupo 0** (prioridad): EAN-13 válidos (2,717 de los 3,169 ABIERTO).
- **Grupo 1** (al final): `BLI_*` o `len ≠ 13` (452 productos) — se clasifican con GLM solo, sin scraping.
- Dentro de cada grupo, los `LastUpdated` más viejos van primero (FIFO por antigüedad).

**Nota**: este filtro excluye implícitamente los UPC-A (12 díg) y EAN-8 (8 díg) que también son scrapeables. Hay 1.592 productos válidos en ese grupo (1.378 + 214) que irían al grupo 1 aunque podrían scrapearse. Pendiente de revisar.

---

## 11. Schedule automático (n8n) — Ventanas de operación

### Configuración activa

**8 workflows n8n en paralelo** (W1–W8), cada uno un worker independiente:

| Worker | id n8n |
|---|---|
| W1 | `lhyC7T3DGv3JARMl` |
| W2 | `F9N2WFUy5resyC0s` |
| W3 | `VEIWQVVCYSIZyKd8` |
| W4 | `mGXtApnQSccxmVsP` |
| W5 | `aYOTAgqaV7YaLZcJ` |
| W6 | `Bd842ucLzPPsssHM` |
| W7 | `59iyej0RpP0omFX5` |
| W8 | `G0R0E1w2TSvIcJUa` |

Estado: todos `active=true`. Cada worker dispara su propio proceso Python vía SSH. El **claim atómico `EN_PROCESO`** (ver `orquestador_produccion.py: fetch_productos_abiertos`) garantiza que los 8 tomen códigos de barras distintos — no se pisan.

> El workflow original `[PROD] Orquestador Clasificador (Ventanas)` (id `AAnxxGYtgg5sD0o8`, 3 ventanas, 1 hilo) **fue eliminado de n8n el 2026-07-24**. Su `.json` queda en git como respaldo dormido (`/home/synapse/source/N8N/workflows/AAnxxGYtgg5sD0o8.json`). Tenía la ventana 19:00 VET que entraba en pico de DeepSeek.

### 5 ventanas diarias off-peak (hora Venezuela, `America/Caracas`)

n8n corre con `GENERIC_TIMEZONE=America/Caracas` (VET, UTC-4, **sin DST**). Los `scheduleTrigger` se programan en hora VET.

| Ventana | Hora VET | Hora host (UTC-5) | DeepSeek |
|---|---|---|---|
| Madrugada | **06:00** | 05:00 | off-peak ✅ |
| Mañana | **08:00** | 07:00 | off-peak ✅ |
| Mediodía | **12:00** | 11:00 | off-peak ✅ |
| Tarde | **16:00** | 15:00 | off-peak ✅ |
| Cierre | **18:00** | 17:00 | off-peak ✅ (cierre interno 18:55 VET) |

Cada worker: 5 ventanas × 8 workers = 40 arranques/día, 8 procesos concurrentes por ventana.

### Horarios peak/off-peak de DeepSeek (proveedor de texto activo)

`IA_PROVEEDOR=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-flash`. DeepSeek introdujo pricing pico/valle con V4 (mediados de 2025). El pico cobra **~2×**.

| Franja (Beijing, UTC+8) | Franja host (UTC-5) | Costo |
|---|---|---|
| 09:00–12:00 y 14:00–18:00 (pico) | **20:00–23:00** y **01:00–05:00** | **2×** 🔴 |
| resto (off-peak) | 05:00–20:00 y 23:00–01:00 | 1× ✅ |

Las 5 ventanas del orquestador caen todas en off-peak. Concurrencia DeepSeek: **2.500** (v4-flash) / 500 (v4-pro) — no es cuello de botella para 8 workers.

### ⚠️ Reset obligatorio al cambiar una ventana horaria (bug conocido de n8n)

Los `scheduleTrigger` de n8n **no recalculan la próxima ejecución** cuando se edita su hora si el workflow sigue `active=true`. Sintoma: la ventana vieja sigue disparando (o no dispara la nueva) hasta que n8n se reinicia.

**Procedimiento al cambiar cualquier ventana horaria:**
1. Editar el/los `scheduleTrigger` (o reemplazar workers).
2. **Desactivar** los workflows afectados (`deactivateWorkflow`).
3. **Reactivarlos** (`activateWorkflow`). Esto re-registra el cron en el active-workflow-runner.
4. Si el desactivar/reactivar no alcanza, **reiniciar el contenedor n8n**:
   ```bash
   docker restart n8n-N8N
   ```
5. Verificar la próxima ejecución esperada en la UI de n8n (pestaña del trigger).

> Nota: como `America/Caracas` no tiene DST, el cambio de horario de verano/invierno **no** afecta a n8n. Este reset solo aplica cuando **un humano edita** una ventana.

### Bot de notificaciones Telegram

- **Bot**: credential `RkijxthBpMtc1pDO` (`[PROD] Telegram - Bot Pago Movil`)
- **Chat**: `ERROR_CHAT_ID` (vía `$env`)
- Cada worker envía su propio resumen etiquetado (`W1`...`W8`) al final de cada ventana.

### Flujo de cada worker

```
5× scheduleTrigger (06/08/12/16/18) → Iniciar Ventana → Seguir Procesando? ─no─→ Resumen Telegram
                                                              │ sí
                                                              ▼
                                              ┌─<─<─ Parse y Acumular <─┐
                                              │                         │
                                              ▼                         │
                                     Check Tiempo Restante               │
                                              │ (>5 min)                 │
                                              ▼                         │
                                     Ejecutar Batch (SSH) ───────────────┘
```

- `BATCH_SIZE=5` (lo decide `.env`, NO se toca desde n8n).
- Una invocación SSH = 1 batch de `BATCH_SIZE` productos.
- El loop corta cuando quedan <5 min de ventana (cierre 18:55 VET) o cuando el batch devuelve `intentados=0` (no quedan ABIERTO).
- Estado acumulado viaja en el `json` del item entre iteraciones.

### Comando SSH que ejecuta cada worker

```bash
cd "/home/synapse/source/repos/Clasificacion Medicamentos" \
  && export DB_SERVER="100.94.5.108,49751" \
  && python3 -u orquestador_produccion.py \
       --trigger-json '{"TriggerID":1,"ProcessName":"MDM_Farmaceutico_Scraper","CheckQuery":"SELECT COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE estado_ciclo = ''ABIERTO''","ThresholdValue":1}' \
       --sync
```

El último renglón del stdout debe ser un JSON `{status, procesados, escritos, intentados}` que `Parse y Acumular` extrae.

### Alertas Telegram

3 canales independientes:

1. **`alertas.py`** (Python, dentro del script): WARN/ERROR del orquestador → `TELEGRAM_AMC_NOTIFICACION_BOT` + `ERROR_CHAT_ID`.
2. **Error Trigger de cada worker n8n**: cualquier fallo del SSH/script → bot `RkijxthBpMtc1pDO` + `ERROR_CHAT_ID`, etiquetado con el worker (W1...W8).
3. **Resumen al final de cada ventana** (nodo Telegram): iters, procesados, escritos, motivo de parada → mismo bot+chat.

### Credenciales involucradas

- SSH: `q9XQyJD7Uu17tWSl` (`[PROD] SSH - Debian WebServices`) — n8n (Docker) → host Debian.
- Telegram: `RkijxthBpMtc1pDO` (`[PROD] Telegram - Bot Pago Movil`).
- MSSQL no se usa directo en el workflow (el script Python la maneja via `synapse.credentials`).

### Qué NO hace el workflow

- **No maneja la transición `pendiente → ABIERTO`** (ver §10.2). El gap arquitectónico sigue.
- **No monitorea cuota de APIs** (DeepSeek/ValueSERP/MiMo): si se agotan créditos, los batches fallan y el Error Trigger avisa por Telegram.
- **No prueba SSH+Telegram end-to-end antes de activarse**: la primera ventana real es la prueba de fuego.
