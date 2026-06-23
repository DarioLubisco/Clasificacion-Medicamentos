# Handoff: Estado de Atributos MDM (porAprobarEquivalencias)

## Contexto Actual
El proyecto se centra en la normalización y consolidación del catálogo maestro de productos farmacéuticos (MDM) de Farmacia Americana. La meta principal ha sido resolver las lagunas de datos en el pipeline de compras (`Procurement.por_aprobacion_equivalencias`) utilizando IA autónoma.

## Logros Recientes
1. **Extracción de Datos:** Se ha desplegado y ejecutado el `Agente_Buscador_Web.py` integrado con OpenRouter (Scrapling) para buscar la información faltante de productos.
2. **Atributos Normalizados:** Se ha logrado extraer información clínica clave:
   - Principio Activo
   - Concentración
   - Forma Farmacéutica (FF)
   - Requerimientos de prescripción y códigos ATC.
3. **Conciliación:** Se procesaron los descriptores de texto crudo (`_Des`) arrojados por la IA y se mapearon a los IDs numéricos (Primary Keys) del catálogo maestro relacional en MSSQL (`EnterpriseAdmin_AMC`).
4. **Actualizaciones SQL:** Se realizaron actualizaciones (`UPDATE`) de alta fidelidad en los lotes pendientes manteniendo la política de "preservación primero".

## Estado de la Tabla `porAprobarEquivalencias`
- La tabla actúa como el staging area para los productos antes de ser homologados.
- Los atributos crudos extraídos de la web ya han pasado por la etapa de homologación semántica para asignarle las categorías correctas sin romper la integridad referencial.
- Gran parte del inventario activo y de compras pendientes ya cuenta con sus atributos clínicos llenos.

## Próximos Pasos para el Siguiente Agente
- **Validación Final:** Ejecutar un query de validación sobre `Procurement.por_aprobacion_equivalencias` para verificar si quedan registros huérfanos (NULL en Principio Activo o Forma Farmacéutica).
- **Sincronización:** Revisar si los cambios han sido promovidos exitosamente a la tabla definitiva de catálogo maestro.
- **Manejo de Excepciones:** Atender los productos que la IA no pudo categorizar por falta de información en internet o por ser insumos no médicos que requieren reglas de triaje manual.

## Skills Obligatorios para la Siguiente Sesión
Para continuar con este flujo de trabajo, el agente **debe** leer y aplicar las instrucciones de las siguientes Skills:

1. **`agente-investigador-farmaceutico_procesado_openrouter`**: Contiene el protocolo de navegación y extracción (V.10.0) para seguir recabando atributos faltantes de medicamentos usando Scrapling.
2. **`conciliador-mdm-farmaceutico_procesado_antigravity`**: Contiene el protocolo para transformar los descriptores crudos de texto en IDs numéricos válidos dentro del catálogo maestro de la Farmacia Americana.
3. **`procesador-html-farmaceutico_procesado_antigravity`**: Debe ser utilizado si se requiere hacer extracciones personalizadas del código HTML de las farmacias para estructurar atributos MDM.
4. **`sql-pro`**: Reglas de manipulación de bases de datos para garantizar actualizaciones SQL seguras al escribir en las tablas de `Procurement`.
5. **`sql-safety-protocol`**: Protocolo estricto para proteger la base de datos durante operaciones en la carpeta de Reportes y subcarpetas.
