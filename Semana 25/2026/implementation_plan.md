# Lógica de Herencia de Segmento Etario (Diario)

Este plan detalla la implementación de la lógica de herencia para el atributo `segmento_etario` (referido como "diario" en la solicitud). La finalidad es enriquecer automáticamente los registros a los que el scraper no pudo extraerles este segmento, utilizando la información de otros registros que coinciden exactamente en ciertos parámetros médicos.

## User Review Required

> [!IMPORTANT]
> Confirmación de término: Asumo que al decir **segmento "diario"** te refieres a **`segmento_etario`**. El plan ha sido diseñado en torno a la columna `segmento_etario` que recién formalizamos. Si te referías a otro campo, indícalo por favor.

> [!NOTE]
> Integración con el ciclo: Mencionas que "El proceso debe ejecutarse después de cada ciclo de scraping fallido". Propongo crear un nuevo endpoint en el backend (ej. `/api/orquestador/heredar-segmento`) que `n8n` puede llamar de forma automática justo después de que falle la extracción con IA para un lote de registros.

## User Review Required

> [!NOTE]
> Aprobado. Procedemos con la integración de la IA para complementar el proceso (extracción de los 16 atributos incluyendo el segmento etario y los otros 6 nuevos) y la lógica de herencia de coincidencia exacta que se ejecutará como respaldo si la extracción falla. Todo contenido de manera secuencial dentro del mismo flujo. 

## Proposed Changes

### Backend FastAPI (Synapse)

#### [MODIFY] `backend/routers/orquestador.py`
En lugar de crear un endpoint nuevo, inyectaremos la lógica de herencia de forma secuencial y contenida dentro de la función `run_scraper_task`, justo después de que la base de datos se actualice con la extracción principal (`update_database_sync`).
- **Lógica**:
  1. Justo después de procesar el lote fallido (o exitoso) en la BD, consultaremos a la base de datos para ejecutar un proceso de herencia para esos productos específicos.
  2. La herencia buscará productos en la BD que coincidan exactamente en `(principio_activo, forma_farmaceutica, concentracion)`.
  3. Si existe la coincidencia, el producto sin segmento heredará el valor (ej. `PEDIATRICO`) del producto fuente.
  4. Todo ocurre de forma transparente y secuencial antes de enviar el webhook final a n8n. No se generarán nodos ni endpoints adicionales en la arquitectura.

## Verification Plan

### Automated Tests
- Ejecutar el script contra la base de datos actual. Mis cálculos preliminares indican que hay unos **500 productos** que podrían heredar inmediatamente este segmento.
- Revisar que los productos actualizados efectivamente tengan `(principio_activo, forma_farmaceutica, concentracion)` idéntico al producto de origen.
- Verificar que el campo `cantidad_presentacion` **no** interfiere en la coincidencia.

### Manual Verification
- Validar visualmente en la tabla `Procurement.por_aprobacion_equivalencias` que los registros afectados hayan cambiado de `NO_DEFINIDO` a la categoría correspondiente (ej. `ADULTO`, `PEDIATRICO`, etc.).
- Probar el llamado HTTP desde Postman o cURL para asegurar que funciona correctamente antes de integrarlo en el flujo de `n8n`.
