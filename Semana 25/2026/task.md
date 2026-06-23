# Rediseño Orquestador IA - Extracción Completa

- [x] Ampliar columna `concentracion_Des` a 500 caracteres
- [x] Modificar `orquestador.py`
    - [x] Rediseñar prompt de IA para extraer 9 atributos
    - [x] Modificar `fetch_pending_records` para priorizar SAPROD
    - [x] Ampliar `UPDATE` local para guardar todos los campos
- [x] Reiniciar `synapse-api`
- [x] Corregir bug en consulta de records pendientes para evitar loops cuando `marca_Des` es NULL
- [x] Prueba manual con `curl` (TriggerID 1000)
- [x] Verificar que los registros se rellenan correctamente (10 productos verificados)
- [x] Monitorear progreso en las próximas 2 horas (~2,342 productos internos pendientes)
- [x] Procesar exitosamente el 100% del catálogo interno (5,517 de 5,517 productos completados)
- [x] Procesar exitosamente el 100% del catálogo externo (Mercado Vivo) (10,433 de 10,433 productos completados)
- [x] Create `Procurement.segmento_etario` table
- [x] Populate `Procurement.segmento_etario` table
- [x] Map dirty values in `Procurement.por_aprobacion_equivalencias.segmento_etario`
- [x] Add Foreign Key constraint

## 2. Expandir Inteligencia Artificial y Herencia
- [x] Modificar prompt de `analyze_with_ai` en `orquestador.py` para incluir 7 nuevos atributos (origen, fabricante, generico, blister, codigo_atc, requiere_recipe, segmento_etario).
- [x] Modificar `update_database_sync` para guardar los 16 atributos.
- [x] Crear función `run_exact_match_inheritance_sync` en `orquestador.py` para la lógica de herencia.
- [x] Inyectar la función de herencia secuencialmente en `run_scraper_task`.
