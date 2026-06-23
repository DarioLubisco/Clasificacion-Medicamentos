# Plan de Implementación: Agente Autónomo de Búsqueda MDM

## Objetivo
Crear un pipeline 100% desatendido que no dependa de una página específica. El script actuará como un "Agente Autónomo": buscará el medicamento en internet por su cuenta, abrirá los resultados evadiendo bloqueos con `Scrapling`, e interpretará el texto usando `OpenRouter`.

## Arquitectura del Agente Autónomo (El "Cerebro")
Para replicar lo que hace mi sub-agente (navegar y buscar sin una URL fija), dotaremos a tu script de Python de tres habilidades:

1. **El Buscador (DuckDuckGo Search):** Una librería gratuita que buscará en internet (ej. `"Principio activo de [Nombre del Medicamento]"`) y obtendrá los primeros 2 o 3 enlaces.
2. **El Lector (Scrapling + Playwright):** Tomará esos enlaces obtenidos y entrará a las páginas de forma anónima, saltándose los bloqueos de Cloudflare, para extraer todo el texto de la página.
3. **El Analista (OpenRouter - Gemini/Claude):** Recibirá ese texto extraído de las páginas y lo resumirá en el formato JSON estructurado que necesita tu base de datos (ATC, Principio Activo, etc.).

## Cambios Propuestos

### 1. Instalación de Dependencias
- [NEW] Añadir `scrapling`, `playwright`, `openai` (para OpenRouter) y **`duckduckgo-search`** (para darle la capacidad de buscar en internet) al archivo `C:\source\repos\Clasificacion Medicamentos\requirements.txt`.
- Instalación de las librerías en el entorno.

### 2. Creación del Script del Agente (`Agente_Buscador_Web.py`)
- [NEW] Crear un nuevo script con la siguiente lógica por cada medicamento pendiente:
  1. **Buscar:** El script busca en internet: `"{descripción_medicamento} principio activo indicaciones"`.
  2. **Extraer:** Obtiene la URL del primer resultado útil y la abre usando `Scrapling`.
  3. **Analizar:** Pasa el texto de la página a OpenRouter con el prompt: *"A partir de este texto web que encontré, extrae el principio activo y el código ATC en este formato JSON..."*
  4. **Guardar:** Escribe el resultado en SQL Server.

### 3. Configuración del Entorno (`.env`)
- [MODIFY] Añadir `OPENROUTER_API_KEY` y `OPENROUTER_MODEL` (usaremos `google/gemini-2.0-flash` por defecto por su velocidad) al `.env`.

## Preguntas Abiertas
> [!IMPORTANT]
> Todo está claro por ahora. Esta solución te da lo mejor de ambos mundos: la autonomía de un agente que "sale a buscar" a internet, pero automatizado en un script local que nadie te puede bloquear. ¿Procedemos a escribir el código de este Agente Buscador?

## Plan de Verificación
- Ejecutar una prueba con 3 medicamentos desconocidos. Veremos en la consola cómo el script busca en DuckDuckGo, elige un link, Scrapling entra a la página, OpenRouter la lee, y el JSON aparece en tu consola.
