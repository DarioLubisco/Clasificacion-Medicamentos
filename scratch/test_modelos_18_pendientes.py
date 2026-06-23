import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_ciclo2_items():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    # Los items que llegaron al ciclo 2 tienen ciclos_reproceso >= 2
    # y origen_dato = 'IA_INVESTIGATED_V10_AUTO'
    query = """
    SELECT codbarras, descrip1art, ciclos_reproceso,
        principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, fabricante_Des, marca_Des,
        codigo_atc_Des, clasificacion_insumo_Des, requiere_recipe, blister, generico, 
        cantidad_presentacion, contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
    FROM Procurement.por_aprobacion_equivalencias 
    WHERE origen_dato = 'IA_INVESTIGATED_V10_AUTO' 
    AND ciclos_reproceso >= 2
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    lote = []
    for r in rows:
        ya_encontrados = {}
        keys = ['principio_activo', 'concentracion', 'forma_farmaceutica', 'fabricante', 'marca',
                'codigo_atc', 'clasificacion_insumo_Des', 'requiere_recipe', 'blister', 'generico',
                'cantidad_presentacion', 'contenido_neto', 'contenido_neto_unidad_Des', 'segmento_etario', 'origen']
        for idx, k in enumerate(keys):
            val = r[3+idx]
            if val is not None and str(val).strip() != '':
                ya_encontrados[k] = val
                
        lote.append({
            "registro": {"codigo": r[0], "codbarras": r[0], "descripcion_original": r[1], "ciclos_reproceso": r[2]},
            "atributos_ya_encontrados": ya_encontrados
        })
    conn.close()
    return lote

def test_models_on_18():
    lote = get_ciclo2_items()
    if not lote:
        print("No se encontraron los 18 items del ciclo 2.")
        return
        
    print(f"Encontrados {len(lote)} items que entraron al Ciclo 2.")
    
    prompt_template = """
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Para cada producto, extrae los siguientes atributos basándote en la descripción:
    - principio_activo (string o null si no aplica/es material médico)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - fabricante (string o null)
    - marca (string o null)
    - codigo_atc (string o null)
    - cantidad_presentacion (int o null, cantidad de unidades en el empaque, ej. 30 pastillas = 30)
    - contenido_neto (float o null, ej. 500 para 500ml)
    - contenido_neto_unidad_Des (string o null, ej. 'ml', 'g')
    - blister (1 o 0, si viene en blister)
    - generico (1 o 0, si es genérico)

    Si el producto claramente no es un medicamento (ej. Teteros, Mamilas, Chupones, Toallas húmedas, Guata, Aspirador nasal, Tubos de ensayo, Bolsas recolectoras, Tapabocas, Centros de cama, Inyectadoras), debes poner:
    - principio_activo: null
    - concentracion: null
    - forma_farmaceutica: null
    - requiere_recipe: 0
    - origen: "NO_MEDICAMENTO" (o el tipo de insumo)

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
        "atributos_nuevos_consolidados": {{"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": "ADULTO", "origen": "IA", "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR:
    {lote_json}
    """

    models = [
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mixtral-8x22b-instruct",
        "nousresearch/hermes-3-llama-3.1-405b"
    ]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Dividir en chunks si es necesario, pero como son 18 items, los podemos mandar juntos o en dos chunks de 9 para evitar timeouts.
    chunk_size = 9
    
    for model in models:
        print(f"\\n{'='*80}\\nPROBANDO MODELO: {model}\\n{'='*80}")
        resultados = []
        for i in range(0, len(lote), chunk_size):
            chunk = lote[i:i+chunk_size]
            prompt = prompt_template.format(lote_json=json.dumps(chunk, indent=2))
            data = {
                "model": model, 
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode())
                    content = result['choices'][0]['message']['content'].strip()
                    # Limpieza básica por si devuelven ```json ... ```
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    res_json = json.loads(content)
                    resultados.extend(res_json)
            except Exception as e:
                print(f"Error con {model} chunk {i//chunk_size}: {e}")
            time.sleep(2)
            
        print(f"RESULTADOS PARA {model}:")
        print(json.dumps(resultados, indent=2))

if __name__ == '__main__':
    test_models_on_18()
