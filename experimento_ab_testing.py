import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import csv
from datetime import datetime
from MDM_Unified_Mapper import MasterCatalog
from limpiador_farmaceutico_regex import procesar_farmacos
from mega_orquestador_autonomo import calcular_score_calidad

# ==============================================================================
# CONFIGURACION DEL EXPERIMENTO
# ==============================================================================
LIMITE_REGISTROS = 25 # Cambiar a 200 o más para la prueba final
MODELOS = [
    "deepseek/deepseek-chat", # Fallback in case v4-flash is not available, but let's use the ones user requested
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-r1"
]
# Forzamos los que el usuario pidió estrictamente
MODELOS = ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro", "deepseek/deepseek-r1"]

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ==============================================================================
# PROMPTS
# ==============================================================================
PROMPT_A_ESTRICTO = """
Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
Para cada producto, extrae principio_activo y concentracion.

REGLA A (100% IA - Formato Estricto):
Si es combinación (múltiples principios activos), DEBES EXTRAERLOS TODOS. 
Ordénalos ESTRICTAMENTE en orden alfabético de izquierda a derecha y sepáralos por un guion (Ej: "Betametasona-Loratadina").
Para la concentración, separa sus concentraciones con un guion (-) manteniendo el mismo orden alfabético. 
RESERVA el símbolo / ÚNICAMENTE para expresar dilución. Ej: 0.25MG-5MG.

Devuelve ÚNICAMENTE un array JSON válido con este formato:
[
  {
    "registro": {"codigo": "...", "codbarras": "...", "descripcion_original": "..."},
    "atributos": {"principio_activo": "...", "concentracion": "..."}
  }
]

LOTE A PROCESAR:
{batch_json_str}
"""

PROMPT_B_RELAJADO = """
Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
Para cada producto, extrae principio_activo y concentracion.

REGLA B (Híbrido - Extracción Cruda):
Si hay múltiples ingredientes, extráelos todos separados por un guion o coma. 
NO intentes ordenarlos alfabéticamente ni darles un formato estricto, extrae exactamente lo que ves en el orden en que aparecen.

Devuelve ÚNICAMENTE un array JSON válido con este formato:
[
  {
    "registro": {"codigo": "...", "codbarras": "...", "descripcion_original": "..."},
    "atributos": {"principio_activo": "...", "concentracion": "..."}
  }
]

LOTE A PROCESAR:
{batch_json_str}
"""

def obtener_lote(limite):
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    query = f"""
    SELECT TOP {limite} codbarras, descrip1art
    FROM Procurement.por_aprobacion_equivalencias
    WHERE es_medicamento IS NULL AND origen_dato IS NULL
    """
    cursor.execute(query)
    filas = cursor.fetchall()
    conn.close()
    
    lote = []
    for f in filas:
        lote.append({
            "registro": {
                "codigo": f.codbarras,
                "codbarras": f.codbarras,
                "descripcion_original": f.descrip1art
            }
        })
    return lote

def llamar_openrouter_experimento(batch_str, model, prompt_template):
    prompt = prompt_template.replace("{batch_json_str}", batch_str)
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            t1 = time.time()
            content = res_json['choices'][0]['message']['content']
            # Cost calc approximate
            p_tokens = res_json.get('usage', {}).get('prompt_tokens', 0)
            c_tokens = res_json.get('usage', {}).get('completion_tokens', 0)
            # Estimate cost arbitrarily for reporting if rates aren't known, or just record tokens
            costo = (p_tokens * 0.0001 / 1000) + (c_tokens * 0.0002 / 1000) 
            
            # Limpiar markdown
            if content.startswith('```json'): content = content[7:]
            elif content.startswith('```'): content = content[3:]
            if content.endswith('```'): content = content[:-3]
            content = content.strip()
            
            return json.loads(content), t1 - t0, costo
    except Exception as e:
        print(f"Error llamando a {model}: {e}")
        return [], time.time() - t0, 0

def ejecutar_experimento():
    lote = obtener_lote(LIMITE_REGISTROS)
    if not lote:
        print("No hay registros para probar.")
        return
        
    print(f"Iniciando A/B Testing con {len(lote)} registros.")
    
    resultados_csv = []
    
    # Procesar en chunks de 1 para medir exacto (o en batch pequeño)
    for index, item in enumerate(lote):
        print(f"\nProcesando {index+1}/{len(lote)}: {item['registro']['descripcion_original']}")
        batch_str = json.dumps([item], indent=2)
        
        for modelo in MODELOS:
            print(f"  -> Probando Modelo: {modelo}")
            
            # Ruta A
            res_a, t_a, c_a = llamar_openrouter_experimento(batch_str, modelo, PROMPT_A_ESTRICTO)
            if isinstance(res_a, dict): res_a = [res_a]
            a_pa = res_a[0].get("atributos", {}).get("principio_activo") if res_a else None
            a_conc = res_a[0].get("atributos", {}).get("concentracion") if res_a else None
            score_a = calcular_score_calidad({"principio_activo": a_pa, "concentracion": a_conc})
            
            # Ruta B
            res_b, t_b, c_b = llamar_openrouter_experimento(batch_str, modelo, PROMPT_B_RELAJADO)
            if isinstance(res_b, dict): res_b = [res_b]
            b_pa_raw = res_b[0].get("atributos", {}).get("principio_activo") if res_b else None
            b_conc_raw = res_b[0].get("atributos", {}).get("concentracion") if res_b else None
            
            # Post-procesar Ruta B
            limpieza_b = procesar_farmacos(b_pa_raw, b_conc_raw)
            if limpieza_b["exito"]:
                b_pa = limpieza_b["principio_activo"]
                b_conc = limpieza_b["concentracion"]
            else:
                b_pa = None
                b_conc = None
            score_b = calcular_score_calidad({"principio_activo": b_pa, "concentracion": b_conc})
            
            # Comparacion
            match_exacto = (a_pa == b_pa) and (a_conc == b_conc)
            
            resultados_csv.append({
                "codbarras": item["registro"]["codbarras"],
                "descripcion": item["registro"]["descripcion_original"],
                "modelo": modelo,
                "A_PA": a_pa,
                "A_Conc": a_conc,
                "A_Score": score_a,
                "B_PA": b_pa,
                "B_Conc": b_conc,
                "B_Score": score_b,
                "Match": match_exacto,
                "Tiempo_A": round(t_a, 2),
                "Tiempo_B": round(t_b, 2),
                "Costo_Total": round(c_a + c_b, 6)
            })
            
            time.sleep(1) # Rate limit protection

    # Guardar a CSV
    keys = resultados_csv[0].keys()
    with open('reporte_ab_testing_deepseek.csv', 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(resultados_csv)
        
    print(f"\n¡Experimento completado! Resultados guardados en reporte_ab_testing_deepseek.csv")

if __name__ == "__main__":
    ejecutar_experimento()
