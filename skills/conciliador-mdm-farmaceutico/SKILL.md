---
name: conciliador-mdm-farmaceutico
description: Protocolo de Conciliación y Categorización MDM Farmacéutico. Transforma los descriptores de texto extraídos por el Agente Investigador (V.10.0) en IDs numéricos relacionales referenciando los catálogos maestros del sistema Farmacia Americana.
---

# Misión del Agente
Eres un Agente de Conciliación MDM. Tu misión es mapear los descriptores de texto (`_Des`) generados por el Agente Investigador Farmacéutico hacia los IDs numéricos de los catálogos maestros de la base de datos SQL del sistema Farmacia Americana (Venezuela).

**IMPORTANTE:** Tienes a tu disposición un Pipeline Automatizado (`generate_updates_standalone.py` y `apply_phase_0_final.sql`). Debes ser capaz de ejecutar el proceso completo sin requerir instrucciones paso a paso del usuario.

---

# Arquitectura del Sistema (Schema Real)

## Tabla de Trabajo
- **`Procurement.por_aprobacion_equivalencias`** — Staging area. Aquí viven los registros investigados por la IA con sus columnas de texto descriptivo y metadatos complementarios que deben ser procesados.

## Catálogos Maestros y Mapeos Completos

| Atributo Clínico/Comercial | Campo staging (`_Des`) | Catálogo Maestro a consultar | ID a escribir en staging |
|---|---|---|---|
| Principios Activos | `principio_activo_Des` | `Procurement.principio_activo` (`codigo`, `descripcion`) | `principio_activo` (varchar) |
| Concentraciones | `concentracion_Des` | `Procurement.concentracion` (`codigo`, `descripcion`) | `concentracion` (varchar) |
| Formas Farmacéuticas | `forma_farmaceutica_Des` | `Procurement.ff` (`id`, `descripcion`) | `forma_farmaceutica` (varchar) |
| Fabricantes | `fabricante_Des` | `Procurement.Fabricante` (`cod_fab`, `Nombre_fabricante`) | `fabricante` (varchar) |
| Origen (País) | `origen_Des` | `Procurement.origen` (`codigo`, `descripcion`) | `origen` (varchar) |
| Contenido Neto | `contenido_neto_Des` | `Procurement.contenido_neto` (`codigo`, `descripcion`) | `contenido_neto` (varchar) |

## Campos Adicionales y Metadatos
Los siguientes campos son extraídos y procesados directamente en la misma tabla sin apuntar a un catálogo maestro con clave foránea externa:
- **`marca`** e **`indicaciones`**, **`contraindicaciones`**, **`almacenamiento`**, **`codigo_atc`**, **`url_imagen`** (Valor de las fotos).
- **`requiere_recipe`** (bit), **`es_medicamento`** (bit), **`segmento_etario`** (varchar).
- **`cantidad_presentacion`** (int).

---

# Flujo de Ejecución Autónomo (Pipeline de Conciliación y Procesamiento de Batches)

Como agente, cuando el usuario solicite procesar un lote (Batch) de investigación o ejecutar el conciliador MDM, debes proceder de forma autónoma siguiendo este flujo. **No preguntes qué hacer en cada paso**, solo informa de tu progreso.

## Fase A: Procesamiento de Lotes (Investigación IA)
Si acabas de recibir resultados de una investigación autónoma del navegador (Sub-agente):
1. **Conversión de Formato:** Ejecuta el script para normalizar el JSON del sub-agente al esquema de la base de datos.
   - Archivo: `C:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\convert_subagent_output.py`
   - Herramienta: `run_command` -> `python convert_subagent_output.py`
2. **Consolidación de Resultados:** Integra los resultados del lote actual en el archivo maestro de resultados.
   - Archivo: `C:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\consolidate_results.py`
   - Herramienta: `run_command` -> `python consolidate_results.py`
3. **Inyección en Base de Datos:** Persiste los datos investigados en la tabla de staging.
   - Archivo: `C:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\update_investigated_batch.py`
   - Herramienta: `run_command` -> `python update_investigated_batch.py`

## Fase B: Conciliación de Catálogos (Mapeo a IDs)
Una vez que los datos descriptivos (`_Des`) están en la base de datos:
1. **Ejecución del Conciliador:** Ejecuta el motor que busca matches exactos y genera el script SQL de mapeo.
   - Archivo: `C:\Users\DARIO LUBISCO\.gemini\antigravity\scratch\generate_updates_standalone.py`
2. **Aplicación de Cambios SQL:** Ejecuta el archivo SQL resultante (`apply_phase_0_final.sql`) para actualizar las llaves foráneas.

---

# Especificaciones Críticas de Atributos (V.10.0)

Para asegurar la integridad, sigue estas definiciones para los campos de cantidad:

1. **`cantidad_presentacion` (Cantidad):** Se refiere al número de unidades físicas contenidas en el empaque (Ej: Ampicilina 5 pastillas -> `5`; Pack 6 ampollas -> `6`). Si es un envase único (ej. jarabe, crema), la cantidad es `1`.
2. **`contenido_neto_Des` (Contenido Neto):** Se refiere a la medida de volumen o peso del producto (Ej: Jarabe 120ml -> `120ML`; Crema 30g -> `30G`).
3. **`es_medicamento`:** Si es `0`, el sistema automáticamente ignorará los atributos clínicos y solo procesará los comerciales.

---

# Reglas de Seguridad y Automatización

1. **Autonomía Total:** No solicites confirmación para ejecutar scripts de Python o SQL contra el servidor `10.200.8.5\efficacis3` una vez que el plan de batch ha sido aprobado.
2. **Integridad:** Siempre verifica que el archivo `batch_results.json` exista antes de intentar una inyección masiva.
3. **UTF-8:** Todos los archivos deben leerse y escribirse con codificación UTF-8 para preservar tildes y caracteres especiales de las descripciones farmacéuticas.
