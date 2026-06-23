import os
import json
import time
import requests
import pyodbc
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
SCRAPLING_API_URL = "http://10.147.18.204:8005/scrape"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OUTPUT_JSON = "investigacion_faltantes_lote2.json"
OUTPUT_SQL = "actualizacion_faltantes_lote2.sql"

# Configuración Base de Datos
DB_SERVER = os.environ.get("DB_SERVER", "10.200.8.5\\efficacis3")
DB_DATABASE = os.environ.get("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.environ.get("DB_USERNAME", "sa")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def obtener_faltantes_bd():
    """Obtiene de la BD los registros que son medicinas y tienen algún atributo clínico importante en NULL."""
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Filtramos medicinas del Lote 2 que tengan algún campo crítico vacío
        query = """
        SELECT 
            codigo, 
            codbarras, 
            descrip1art,
            principio_activo_Des,
            concentracion_Des,
            forma_farmaceutica_Des,
            codigo_atc_Des,
            fabricante_Des,
            marca_Des
        FROM Procurement.por_aprobacion_equivalencias
        WHERE origen_dato = 'IA_INVESTIGATED_V10_LOTE2' 
          AND es_medicamento = 1
          AND (
              principio_activo_Des IS NULL OR
              concentracion_Des IS NULL OR
              forma_farmaceutica_Des IS NULL OR
              codigo_atc_Des IS NULL OR
              fabricante_Des IS NULL OR
              marca_Des IS NULL
          )
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        lote = []
        for row in rows:
            # Determinamos exactamente qué falta
            faltantes = []
            if row.principio_activo_Des is None: faltantes.append("principio_activo")
            if row.concentracion_Des is None: faltantes.append("concentracion")
            if row.forma_farmaceutica_Des is None: faltantes.append("forma_farmaceutica")
            if row.codigo_atc_Des is None: faltantes.append("codigo_atc")
            if row.fabricante_Des is None: faltantes.append("fabricante")
            if row.marca_Des is None: faltantes.append("marca")
            
            lote.append({
                "codigo": row.codigo,
                "codbarras": row.codbarras,
                "descrip1art": row.descrip1art,
                "faltantes": faltantes
            })
            
        conn.close()
        return lote
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        return []

def extraer_texto_web(query: str) -> str:
    """Usa el Scrapling API de Debian para buscar la query en Vademecum/Google"""
    try:
        # Aquí usamos un truco: le pedimos a Debian que busque en Google directamente
        # En la vida real, el MCP Scrapling API asume que le pasas una URL, 
        # pero si tu endpoint acepta querys directas, lo ajustas.
        # Por ahora simularemos la búsqueda de Google redirigida.
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        payload = {"url": url}
        response = requests.post(SCRAPLING_API_URL, json=payload, timeout=40)
        if response.status_code == 200:
            data = response.json()
            return data.get("content", "")[:12000]
        return ""
    except:
        return ""

def analizar_faltantes_con_llm(texto_contexto: str, desc: str, codbarras: str, faltantes: list) -> dict:
    contexto = f"CONTEXTO WEB:\n{texto_contexto}\n" if texto_contexto else "SIN CONTEXTO WEB.\n"
    
    # Creamos un bloque JSON dinámico solo con lo que falta
    json_keys = ",\n      ".join([f'"{f}": str' for f in faltantes])
    
    prompt = f"""
    Eres el Agente Experto de Clasificación Farmacéutica V.10.4 (Modo Quirúrgico).
    Analiza el producto: "{desc}" (EAN: {codbarras}).
    
    {contexto}
    
    TAREA EXCLUSIVA:
    A este registro le faltan SOLO los siguientes atributos: {', '.join(faltantes)}.
    Tu objetivo es buscar en el contexto provisto y devolver ÚNICAMENTE estos atributos. No reescribas otros datos.
    Si no encuentras alguno, devuélvelo como nulo (null).
    
    Responde ÚNICAMENTE en JSON con este esquema exacto:
    {{
      {json_keys}
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error LLM: {e}")
        return {}

def procesar():
    lote = obtener_faltantes_bd()
    if not lote:
        print("No hay registros faltantes o hubo un error.")
        return

    print(f"Iniciando pasada de relleno para {len(lote)} registros...")
    
    resultados = []
    procesados = 0

    def task(item):
        nonlocal procesados
        codbarras = item["codbarras"].strip() if item["codbarras"] else ""
        desc = item["descrip1art"].strip()
        faltantes = item["faltantes"]
        
        # 1. Intentamos buscar por código de barras primero (ACCIÓN PRINCIPAL)
        texto_web = ""
        if codbarras and not codbarras.startswith("BLI_") and len(codbarras) == 13:
            texto_web = extraer_texto_web(f"vademecum {codbarras}")
        
        # 2. Si no hay resultados buenos con el codbarras, usamos texto (ACCIÓN SECUNDARIA)
        if not texto_web or len(texto_web) < 100:
            texto_web = extraer_texto_web(desc)

        # 3. Consultamos al LLM SOLAMENTE por los atributos faltantes
        datos = analizar_faltantes_con_llm(texto_web, desc, codbarras, faltantes)
        
        resultados.append({
            "codigo": item["codigo"],
            "atributos_recuperados": datos
        })
        
        procesados += 1
        print(f"[{procesados}/{len(lote)}] Recuperados para {item['codigo']}...")

    # Ejecución paralela
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(task, lote)

    # Generar SQL de relleno
    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        f.write("BEGIN TRANSACTION;\n")
        for res in resultados:
            cod = res["codigo"]
            attr = res["atributos_recuperados"]
            if not attr: continue
            
            updates = []
            for k, v in attr.items():
                if v is not None and str(v).strip().lower() != 'null' and str(v).strip() != '':
                    val = str(v).replace("'", "''")
                    updates.append(f"{k}_Des = '{val[:255]}'")
            
            if updates:
                f.write(f"UPDATE Procurement.por_aprobacion_equivalencias SET {', '.join(updates)} ")
                f.write(f"WHERE codigo = '{cod}';\n")
                
        f.write("COMMIT;\n")
    print(f"Proceso finalizado. SQL generado en {OUTPUT_SQL}")

if __name__ == "__main__":
    procesar()
