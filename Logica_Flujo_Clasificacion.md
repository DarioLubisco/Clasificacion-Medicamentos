# Documentación del Flujo de Clasificación de Medicamentos (MDM)

Este documento detalla la arquitectura, conexiones a base de datos y la lógica de flujo de los pipelines de procesamiento para la **Clasificación de Medicamentos** (Master Data Management - MDM). Existen dos enfoques/versiones principales actualmente desplegados en este workspace.

## 1. Conexión a la Base de Datos

Ambos scripts se conectan a un servidor **SQL Server** utilizando `pyodbc` y la capa ORM `SQLAlchemy`. Las credenciales y configuraciones se extraen de un archivo local `.env`.

### Variables de Entorno (`.env`)
- `DB_SERVER`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DRIVER`, `TIMEOUT`
- `DB_TRAIN_TABLE`: Tabla de histórico o maestros previamente clasificados.
- `DB_PREDICT_TABLE`: Tabla objetivo (stage) donde están los registros nuevos a predecir.

### Cadena de Conexión
La URL de conexión sigue el formato:
```python
mssql+pyodbc:///?odbc_connect={quoted_conn_str}
```
Esto permite usar la velocidad y robustez de la librería subyacente ODBC (por ej. `ODBC Driver 17 for SQL Server`), facilitando integraciones nativas con `pandas` (`read_sql`) y sentencias SQL crudas vía `text()`.

---

## 2. Flujo Lógico General (Común a ambas versiones)

El proceso sigue una jerarquía de clasificación en **2 Fases**, diseñada para ahorrar capacidad de cómputo/costos y evitar predecir datos que ya conocemos:

1. **Fase 1: Búsqueda Histórica (Lookup)**
   Se hace un `merge` (cruce) entre los datos no clasificados (`df_predict`) y el histórico (`df_train`) por `codbarras`. Si existe correspondencia, el sistema actualiza automáticamente la tabla destino en base a los valores previamente validados. 
   *Marca en Base de Datos: `origen_dato = 'HISTORICO'`*

2. **Fase 2: Predicción por IA**
   Se filtran los registros que no fueron resueltos en el paso anterior y se pasan por un motor de Inteligencia Artificial para extraer/clasificar los atributos a partir de su texto descriptivo (`descrip1art`).

---

## 3. Análisis de las Dos Versiones (Estrategias de IA)

Existen dos estrategias de Inteligencia Artificial implementadas:

### A. Versión basada en NLP Tradicional / Modelos Locales (`Clas_Med.py`)
Utiliza la biblioteca de Hugging Face (`transformers` y `datasets`) para entrenar o aplicar modelos BERT/RoBERTa locales.

- **Atributos Clasificados:** Principio Activo, Forma Farmacéutica, Fabricante, Patrocinador, Concentración.
- **Funcionamiento:** 
  1. Tokeniza los datos a analizar.
  2. Para cada atributo, carga/ejecuta un clasificador multiclase (entrenado previamente).
  3. Recupera la predicción con el `Score` de mayor confianza.
- **Salida:** Agrega los labels predichos y los puntajes. 
- *Marca en DB: `origen_dato = 'IA'`*

### B. Versión basada en LLMs / Agentes Generativos (`Agente_Clasificador.py`)
Utiliza el modelo **Gemini 1.5 Flash** (vía API). Esta aproximación "Zero/Few-Shot" es sumamente adaptable e ideal para extraer múltiples atributos estructurados en un solo paso.

- **Atributos Extraídos (Mayor amplitud):** Principio Activo, Forma Farmacéutica, Fabricante, Patrocinador, Concentración, Código ATC, Indicaciones, Contraindicaciones, Almacenamiento, y Requiere Récipe.
- **Funcionamiento:**
  1. Genera un prompt con un rol farmacológico que ingiere la descripción del artículo (`descrip1art`).
  2. Fuerza la respuesta como un formato JSON estricto (`application/json`).
  3. Modifica la base de datos registro a registro. Incluye bloqueos intencionales de tiempo (`time.sleep(0.5)`) para respetar los Rate Limits (cuotas de API).
- *Marca en DB: `origen_dato = 'IA_AGENTE'`*

---

## 4. Consideraciones para Producción y Próximos Pasos

1. **Costos vs. Velocidad:** `Agente_Clasificador.py` extraerá mucha más riqueza de datos (como ATC e indicaciones) y no necesita reentrenamiento si aparecen nuevos atributos. `Clas_Med.py` es mejor si los laboratorios están muy estandarizados y prefieres el cómputo 100% on-premise.
2. **Escalabilidad del Agente:** 
   - Implementar lotes (batching) usando prompts que procesen de a 10 productos a la vez reduciría el volumen total de peticiones a la API.
   - En `Agente_Clasificador.py` el `UPDATE` se hace fila por fila. Para grandes volúmenes, la inserción o actualización mediante sentencias en masa (bulk upload a tabla temporal + merge SQL) aceleraría el flujo dramáticamente.
3. **Manejo de Errores:** En la fase de la API de Gemini, considerar el uso de reintentos exponenciales en lugar de solo imprimir un error en pantalla (actualmente falla silenciosamente si se agota la cuota temporal).
