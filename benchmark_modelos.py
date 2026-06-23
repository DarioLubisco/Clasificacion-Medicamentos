import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
socket.setdefaulttimeout(180)
from MDM_Unified_Mapper import MasterCatalog
from limpiador_farmaceutico_regex import procesar_farmacos

gasto_lock = threading.Lock()

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Global cost tracking
gasto_por_ciclo = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

def llamar_openrouter(batch_json_str, model, ciclo_actual):
    global gasto_por_ciclo
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Para cada producto, extrae los siguientes atributos basándote en la descripción:
    - principio_activo (string o null si no aplica/es material médico)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - fabricante (string o null)
    - marca (string o null, si es un medicamento genérico sin marca comercial aparente, escribe "Generico")
    - origen (string o null, nación o país de origen de fabricación, ej. 'VENEZUELA', 'USA')
    - segmento_etario (string o null, ej. 'ADULTO', 'PEDIATRICO', 'PEDIATRICO/ADULTO')
    - codigo_atc (string o null, puedes deducirlo de tu base de conocimientos si identificas el principio activo)
    - cantidad_presentacion (int o null, cantidad de unidades en el empaque, ej. 30 pastillas = 30)
    - contenido_neto (float o null, ej. 500 para 500ml)
    - contenido_neto_unidad_Des (string o null, ej. 'ml', 'g')
    - blister (1 o 0, 1 estrictamente si la descripción contiene la palabra "blister", 0 en caso contrario)

    Si el producto claramente no es un medicamento (ej. Teteros, Mamilas, Chupones, Toallas húmedas, Guata, Aspirador nasal, Tubos de ensayo, Bolsas recolectoras, Tapabocas, Centros de cama, Inyectadoras), debes poner:
    - principio_activo: null
    - concentracion: null
    - forma_farmaceutica: null
    - clasificacion_insumo_Des: "NO_MEDICAMENTO" (o el tipo de insumo)

    Para los productos farmacéuticos válidos, extrae la información técnica estrictamente si está presente en el texto de la descripción original. NO ASUMAS, NO ADIVINES y NO INFIERAS valores que no estén explícitamente escritos. Si un dato técnico (como la concentración o el principio activo) falta, tu obligación es usar null.

    IMPORTANTE: 
    - En la llave "atributos_ya_encontrados" te informaremos qué datos ya logramos extraer en intentos pasados. 
    - Por defecto, conserva esos valores. Sin embargo, si los 'atributos_ya_encontrados' contienen información que contradice el texto original o parece inventada/alucinada por un modelo anterior, TIENES AUTORIZACIÓN PARA SOBREESCRIBIRLA Y CORREGIRLA.
    - Para los datos faltantes (nulos), enfócate en extraerlos literalmente. No infieras datos que no puedas sustentar con la descripción original.
    - Devuelve ÚNICAMENTE un array JSON válido con este formato, sin markdown, sin texto adicional:
    [
      {{
        "registro": {{"codigo": "...", "codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0}},
        "atributos_ya_encontrados": {{}},
        "atributos_nuevos_consolidados": {{"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR:
    {batch_json_str}
    """
    
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode())
                usage = result.get('usage', {})
                p_tokens = usage.get('prompt_tokens', 0)
                c_tokens = usage.get('completion_tokens', 0)
                model_lower = model.lower()
                if "gemini-2.5-flash" in model_lower:
                    costo = (p_tokens * 0.075 + c_tokens * 0.30) / 1000000.0
                elif "gemini-2.5-pro" in model_lower:
                    costo = (p_tokens * 1.25 + c_tokens * 5.00) / 1000000.0
                elif "deepseek-v4-flash" in model_lower:
                    costo = (p_tokens * 0.09 + c_tokens * 0.18) / 1000000.0
                elif "deepseek-v4-pro" in model_lower:
                    costo = (p_tokens * 0.44 + c_tokens * 0.87) / 1000000.0
                elif "deepseek-r1" in model_lower:
                    costo = (p_tokens * 0.55 + c_tokens * 2.19) / 1000000.0
                elif "minimax-m3" in model_lower:
                    costo = (p_tokens * 0.30 + c_tokens * 1.20) / 1000000.0
                elif "mixtral-8x22b" in model_lower:
                    costo = (p_tokens * 0.90 + c_tokens * 0.90) / 1000000.0
                elif "qwen-2.5-72b" in model_lower:
                    costo = (p_tokens * 0.36 + c_tokens * 0.40) / 1000000.0
                elif "llama-3.3-70b" in model_lower:
                    costo = (p_tokens * 0.35 + c_tokens * 0.40) / 1000000.0
                else:
                    costo = (p_tokens * 1.25 + c_tokens * 10.00) / 1000000.0
                
                with gasto_lock:
                    gasto_por_ciclo[ciclo_actual] += costo
                print(f"    [IA] {model} | Tokens: In={p_tokens}, Out={c_tokens} | Costo: ${costo:.5f}")
                
                if 'choices' not in result or not result['choices']:
                    print(f"    ERROR: Respuesta inesperada de OpenRouter (sin choices): {json.dumps(result, indent=2)}")
                    return None
                    
                message = result['choices'][0].get('message', {})
                content = message.get('content')
                if content is None:
                    print(f"    ERROR: El content de la respuesta es None. Mensaje completo: {json.dumps(message, indent=2)}")
                    return None
                    
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
        except Exception as e:
            print(f"    [Intento {attempt+1}/{max_retries}] Error llamando a OpenRouter ({model}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
    return None

def calcular_score_calidad(atrib):
    score = 0
    es_medicamento = not bool(atrib.get('clasificacion_insumo_Des'))
    
    # SINE QUA NON: Condición indispensable para medicamentos
    if es_medicamento:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0
            
    # TABLA DE PUNTOS NORMALIZADA A 100 PUNTOS EXACTOS
    if atrib.get('cantidad_presentacion') is not None: score += 26
    if atrib.get('origen'): score += 19
    if atrib.get('segmento_etario'): score += 13
    if atrib.get('fabricante'): score += 10
    if atrib.get('codigo_atc'): score += 10
    if atrib.get('marca'): score += 7
    
    # Lógica de Volumen vs Forma Farmacéutica (Mutuamente excluyentes para el score)
    ff = str(atrib.get('forma_farmaceutica')).upper()
    solidos = ['TABLETA', 'PASTILLA', 'CAPSULA', 'GRAGEA', 'POLVO', 'SOBRE', 'PIZARRA', 'SUPOSITORIO', 'OVULO', 'COMPRIMIDO', 'GRANULADO']
    viales_inyectables = ['INYECTABLE', 'AMPOLLA', 'VIAL']
    
    if any(s in ff for s in solidos):
        # Los sólidos no necesitan declarar volumen líquido, ganan los puntos de contenido por defecto
        score += 15
    elif atrib.get('contenido_neto') is not None or any(v in ff for v in viales_inyectables):
        # Los líquidos o inyectables sí requieren declarar el contenido neto para ganar estos puntos
        score += 15
        
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val:
        return "NO_DEFINIDO"
    val_upper = str(val).upper().strip()
    val_upper = val_upper.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    if "ADULTO" in val_upper:
        return "ADULTO"
    if "PEDIATRICO" in val_upper or "INFANTIL" in val_upper or "NIÑO" in val_upper or "HIJO" in val_upper or "KID" in val_upper:
        return "PEDIATRICO"
    if "NEONATAL" in val_upper or "NEONATO" in val_upper or "BEBE" in val_upper:
        return "NEONATAL"
    if "MIXTO" in val_upper:
        return "MIXTO"
    if "GENERAL" in val_upper or "TODO" in val_upper or "TODOS" in val_upper or "PUBLICO" in val_upper:
        return "GENERAL"
    if val_upper in ["ADULTO", "PEDIATRICO", "NEONATAL", "MIXTO", "GENERAL", "NO_DEFINIDO"]:
        return val_upper
    return "NO_DEFINIDO"

def main():
    print("=== INICIANDO BENCHMARK DE 4 MODELOS (30 PRODUCTOS ALEATORIOS DESDE CERO) ===")
    
    # 1. Obtener 30 productos TOTALMENTE ALEATORIOS de la tabla maestra
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT TOP 30 codbarras, descrip1art 
    FROM Procurement.por_aprobacion_equivalencias 
    ORDER BY NEWID()
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 30:
        print(f"Error: Solo se encontraron {len(rows)} productos en total.")
        return
        
    print(f"Se seleccionaron {len(rows)} productos aleatorios. Armando lote limpio...")
    
    lote_limpio = []
    for r in rows:
        lote_limpio.append({
            "registro": {"codigo": r[0], "codbarras": r[0], "descripcion_original": r[1], "ciclos_reproceso": 0},
            "atributos_ya_encontrados": {}  # Totalmente vacío para que compitan en igualdad de condiciones
        })
        
    print("Guardando lote original en benchmark_input.json")
    with open('benchmark_input.json', 'w', encoding='utf-8') as f:
        json.dump(lote_limpio, f, indent=2)

    lote_json_str = json.dumps(lote_limpio, indent=2)

    modelos_a_evaluar = [
        ("Qwen 2.5 72B", "qwen/qwen-2.5-72b-instruct", 0, "benchmark_qwen.json"),
        ("MiniMax M3", "minimax/minimax-m3", 1, "benchmark_minimax.json"),
        ("Mixtral 8x22B", "mistralai/mixtral-8x22b-instruct", 2, "benchmark_mixtral.json"),
        ("Gemini 2.5 Pro", "google/gemini-2.5-pro", 3, "benchmark_gemini.json")
    ]

    for nombre, modelo_id, ciclo, archivo_salida in modelos_a_evaluar:
        print(f"\n--- EVALUANDO MODELO: {nombre} ({modelo_id}) ---")
        res = llamar_openrouter(lote_json_str, model=modelo_id, ciclo_actual=ciclo)
        
        if res:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(res, f, indent=2)
            print(f"  -> Resultados guardados en {archivo_salida}")
            
            # Calcular puntuaciones localmente aplicando el post-procesamiento de producción
            puntajes = []
            for item in res:
                atrib = item.get('atributos_nuevos_consolidados', item.get('atributos', {}))
                
                # Clonar atributos para limpiar localmente
                atrib_clean = dict(atrib)
                
                # 1. Procesamiento y limpieza con Expresiones Regulares
                res_limpieza = procesar_farmacos(atrib_clean.get('principio_activo'), atrib_clean.get('concentracion'))
                if res_limpieza["exito"]:
                    atrib_clean['principio_activo'] = res_limpieza["principio_activo"]
                    atrib_clean['concentracion'] = res_limpieza["concentracion"]
                else:
                    atrib_clean['principio_activo'] = None
                    atrib_clean['concentracion'] = None
                
                # 2. Normalizar segmento etario
                atrib_clean['segmento_etario'] = normalizar_segmento_etario(atrib_clean.get('segmento_etario'))
                
                # 3. Normalizar Forma Farmaceutica (Plural a Singular)
                if atrib_clean.get('forma_farmaceutica'):
                    ff_upper = str(atrib_clean.get('forma_farmaceutica')).upper().strip()
                    reemplazos_ff = {
                        'SOBRES': 'SOBRE', 'GOMITAS': 'GOMITA', 'TABLETAS': 'TABLETA',
                        'ÓVULOS': 'ÓVULO', 'SUPOSITORIOS': 'SUPOSITORIO', 'CÁPSULAS': 'CÁPSULA',
                        'COMPRIMIDOS': 'COMPRIMIDO', 'GRAGEAS': 'GRAGEA', 'APÓSITOS': 'APÓSITO',
                        'PASTILLAS': 'PASTILLA', 'GASAS': 'GASA', 'CAPSULAS': 'CAPSULA',
                        'GALLETAS': 'GALLETA', 'SACHETS': 'SACHET', 'CARAMELOS': 'CARAMELO'
                    }
                    if ff_upper in reemplazos_ff:
                        atrib_clean['forma_farmaceutica'] = reemplazos_ff[ff_upper]
                
                # Calcular score de calidad
                score = calcular_score_calidad(atrib_clean)
                puntajes.append(score)
            
            aprobados = sum(1 for s in puntajes if s >= 88)
            promedio = sum(puntajes) / len(puntajes) if puntajes else 0
            print(f"  -> Aprobados simulados (>=88): {aprobados}/{len(rows)} | Promedio Score: {promedio:.1f}")
        else:
            print(f"  -> ERROR: No se obtuvieron resultados de {nombre}")
            
        time.sleep(3)
        
    # --- TABLA RESUMEN FINAL ---
    print("\n" + "="*70)
    print("         RESUMEN DE COSTOS DEL BENCHMARK")
    print("="*70)
    print(f"{'Modelo':<25}{'Costo':<12}")
    print("-"*70)
    
    total_gasto = 0.0
    for nombre, _, ciclo, _ in modelos_a_evaluar:
        costo = gasto_por_ciclo[ciclo]
        total_gasto += costo
        print(f"{nombre:<25} ${costo:.5f}")
        
    print("-"*70)
    print(f"{'TOTAL':<25} ${total_gasto:.4f}")
    print("="*70)

if __name__ == "__main__":
    main()
