import os
from dotenv import load_dotenv
load_dotenv()
import json
import urllib.request
import time

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def llamar_openrouter(batch_json_str, model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Tu único objetivo es la PRECISIÓN ABSOLUTA (Zero-Tolerance). Extraer un dato que no está explícitamente en la descripción o que no se deduce inequívocamente es un ERROR CRÍTICO. Ante la menor duda, o si el dato no existe, debes devolver null.

    Para cada producto, extrae los siguientes atributos basándote ÚNICAMENTE en la descripción:
    - dominio (string OBLIGATORIO: "MEDICAMENTO_ALOPATICO", "PRODUCTO_NATURAL_HOMEOPATICO", "SUPLEMENTO_VITAMINICO", "COSMETICO_CUIDADO_PERSONAL", "MATERIAL_MEDICO_INSUMO", "MISCELANEO")
    - principio_activo (string o null si no aplica/es insumo)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - cantidad_presentacion (int o null, ej. 30 para "30 pastillas", o 1 para un envase único como un jarabe o tubo de crema)
    - contenido_neto (float o null, ej. 120 para "120ml")
    - contenido_neto_unidad_Des (string o null, ej. 'ml', 'g')
    - fabricante (string o null)
    - marca (string o null)
    - codigo_atc (string o null)
    - blister (1 o 0, si viene en blister explícitamente)
    - generico (1 o 0, si dice genérico explícitamente)

    REGLAS ESTRICTAS ANTI-ALUCINACIÓN:
    1. ATC: NO deduzcas el código ATC a partir del principio activo. Solo extráelo si aparece explícitamente en el texto.
    2. Contenido Neto vs Concentración: La concentración del PA (ej. 500mg) NO es el contenido neto. El contenido neto es el volumen/peso total del envase (ej. 120ml).
    3. Marca / Fabricante: Si no hay una marca o fabricante explícito en el texto, usa null. NO asumas 'Genérico' como marca, ni adivines laboratorios.
    4. Segmento Etario: NO lo deduzcas a menos que haya palabras clave claras (infantil, niños, pediátrico, adulto, forte). Ante la duda, null.

    IMPORTANTE: 
    - En "atributos_ya_encontrados" te informamos qué datos ya extrajimos antes. Puedes corregirlos si son contradictorios o parecen inventados, si no, consérvalos.
    - Debes generar una llave "razonamiento" con una breve cadena de pensamiento explicando tu análisis (qué ves en el texto, qué extraes y qué falta).
    
    Devuelve ÚNICAMENTE un array JSON válido con este formato:
    [
      {{
        "registro": {{"codigo": "...", "codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0}},
        "atributos_ya_encontrados": {{}},
        "atributos_nuevos_consolidados": {{"razonamiento": "...", "dominio": "...", "principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR:
    {batch_json_str}
    """
    
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content']
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip())
    except Exception as e:
        print(f"Error {model}: {e}")
        return None

if __name__ == "__main__":
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/lote_30.json', 'r', encoding='utf-8') as f:
        lote = json.load(f)
    
    mod = "z-ai/glm-5.2" 
    
    chunk_size = 5
    chunks = [lote[i:i + chunk_size] for i in range(0, len(lote), chunk_size)]
    
    resultado = []
    print(f"\n[{mod}] Analizando los 30 productos (en {len(chunks)} bloques)...")
    fallo_modelo = False
    
    for idx, chunk in enumerate(chunks):
        batch_json_str = json.dumps(chunk, indent=2)
        print(f"  Enviando bloque {idx+1}/{len(chunks)}...")
        res = llamar_openrouter(batch_json_str, mod)
        
        if res is None:
            print(f"  Fallo en bloque {idx+1}. Se cancela el resto para este modelo.")
            fallo_modelo = True
            break
        else:
            resultado.extend(res)
        time.sleep(1)
        
    if fallo_modelo:
        resultado = None
    
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/glm_5_2_30_complex.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("\nBenchmark GLM 5.2 completado. Datos guardados.")
