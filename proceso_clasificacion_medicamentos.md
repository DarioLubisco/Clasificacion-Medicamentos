# Proceso Completo de Clasificación Farmacéutica

A continuación se detalla el diagrama de flujo exhaustivo (logorreico) que describe cada una de las fases, reglas de negocio y validaciones que ejecuta nuestro Agente Investigador Farmacéutico. Esta versión está optimizada y garantizada para renderizar en Mermaid Live Editor.


```mermaid
%%{init: { "flowchart": { "htmlLabels": false } }}%%
flowchart TD
   A["Inicio: Orquestador Autónomo"] --> B["Conexión a BD EnterpriseAdmin_AMC SQL Server"]
  
   subgraph "Fase 1: Extracción y Limpieza Previa"
       B --> C{"Consulta SQL: Extraer Lote de Productos"}
       C --> D["Obtener campos clave: codbarras, descrip1art, ciclos_reproceso"]
       D --> E["Obtener atributos existentes: principio_activo, concentracion, fabricante, marca, etc."]
       E --> F["Filtro de Ruido: Identificar basuras previas en BD \n ej. 'origen: IA', 'origen: NO_MEDICAMENTO'"]
       F --> G["Estructuración del Payload Inicial: Array de diccionarios \n con 'registro' y 'atributos_ya_encontrados'"]
   end

   G --> H["Agrupación en Bloques / Chunking"]

   subgraph "Fase 2: Procesamiento Paralelo y Anti-Rate Limits"
       H --> I["Dividir el Lote Total en 'Chunks' pequeños \n ej. Tamaño del Chunk = 2"]
       I --> J["Inicio Bucle: Iterar por cada Chunk"]
       J --> K["Construcción Dinámica del Prompt del Agente Investigador"]
   end

   subgraph "Fase 3: Inyección de Reglas de Tolerancia Cero"
       K --> L["Regla 1: Precisión Absoluta - Sin deducciones alucinadas"]
       L --> M["Regla 2: Separación de Contenido Neto y Concentración"]
       M --> N["Regla 3: Marcas y Fabricantes explícitos únicamente"]
       N --> O["Regla 4: Segmento Etario solo por palabras clave explícitas"]
       O --> P["Regla 5: El Origen DEBE ser un país soberano - Null a descriptores como 'Nacional'"]
       P --> Q["Regla 6: Múltiples P.A. ORDENADOS ALFABÉTICAMENTE \n Separados por ' + ' y concentraciones alineadas"]
   end

   subgraph "Fase 4: Comunicación con la IA vía OpenRouter"
       Q --> R{"Llamada HTTP a OpenRouter \n Modelo: google/gemma-4-26b-a4b-it"}
       R -- "Fallo de Red o HTTP 429 / 500" --> S["Espera Activa: time.sleep de 5 segundos"]
       S --> T{"Intento < Max_Retries 3?"}
       T -- "Sí" --> R
       T -- "No" --> U["Abortar Chunk y Retornar NULL"]
       R -- "Éxito HTTP 200" --> V["Recepción del Payload de Respuesta de Gemma"]
   end

   subgraph "Fase 5: Robust JSON Extraction y Validación"
       V --> W["Extractor de JSON de Alta Resiliencia \n Busca los límites '[' y ']' en todo el string de respuesta"]
       W --> X{"¿Es un JSON Válido?"}
       X -- "No" --> Y["Fallo de Parseo JSON: Retorna NULL"]
       X -- "Sí" --> Z["Deserialización Exitosa a Objeto Python"]
       Z --> AA["Validar estructura de llaves retornadas \n 'razonamiento', 'dominio', 'principio_activo', etc."]
       AA --> AB["Extracción del 'razonamiento' logorreico generado por la IA"]
   end

   subgraph "Fase 6: Consolidación Final"
       Y --> AC["Agrupar Resultados del Chunk"]
       U --> AC
       AB --> AC
       AC --> AD{"¿Quedan más Chunks por procesar?"}
       AD -- "Sí" --> J
       AD -- "No" --> AE["Generación del Lote Completo de Resultados"]
       AE --> AF["Guardar Resultados en Archivo de Depuración Local: debug_resultados_torsilax.json"]
       AF --> AG["Volcado a Reporte Excel o Actualización SQL a Procurement.por_aprobacion_equivalencias"]
   end

   AG --> AH["Fin del Proceso de Clasificación Multimodal"]

    style A fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style AH fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style S fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style T fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style U fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Y fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style D fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style E fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style F fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style G fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style H fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style I fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style J fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style K fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style R fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style V fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style W fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style Z fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style AB fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style AC fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style AD fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style AE fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style L fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style M fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style N fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style O fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style P fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Q fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style X fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style AA fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style B fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    style C fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    style AF fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
    style AG fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff

```
