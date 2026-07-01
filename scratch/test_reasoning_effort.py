import os
import json
import urllib.request
import time
import sys

# Añadir el path raíz para los imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scratch.evaluate_optimized_local import (
    filtrar_imagenes_legibles,
    transcribir_imagenes_gemini,
    obtener_taxonomias_estrictas
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    # Intentar cargar de .env local
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(dotenv_path):
        with open(dotenv_path, 'r') as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    OPENROUTER_API_KEY = line.strip().split("=")[1].replace("'", "").replace('"', '')
                    break

if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY no encontrada.")
    sys.exit(1)

def llamar_openrouter_test(prompt, model, effort):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 0.9
    }
    
    if effort:
        data["reasoning"] = {"effort": effort}
        
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            elapsed = time.time() - start_time
            result = json.loads(response.read().decode())
            usage = result.get('usage', {})
            choices = result.get('choices', [{}])
            content = choices[0].get('message', {}).get('content', '')
            reasoning = choices[0].get('message', {}).get('reasoning', '')
            
            return {
                "success": True,
                "elapsed": elapsed,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": usage.get("reasoning_tokens", 0),
                "content": content,
                "reasoning": reasoning
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    print("=== INICIANDO EXPERIMENTO DE TOKENS (CON VISIÓN Y OCR) ===")
    
    # Cargar los productos del dataset de visión
    with open("scratch/eval_20_vision.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    # Seleccionar dos productos que tengan imágenes (el 2 y el 3 en el dataset: Diosmina e Isospray)
    productos = [dataset[1], dataset[2]] 
    taxonomias_str = obtener_taxonomias_estrictas()
    
    # Cargar prompt template
    with open("prompt_agente_v3_solidificado_final.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    model = "deepseek/deepseek-v4-flash"
    
    scenarios = [
        ("Por defecto (medium)", None),
        ("High (alto)", "high"),
        ("XHigh (máximo)", "xhigh")
    ]
    
    results = []
    
    for i, prod in enumerate(productos, 1):
        ean = prod["ean"]
        desc = prod["descripcion"]
        fuentes_web = prod["fuentes_web"]
        imagenes_b64 = prod.get("imagenes_b64", [])
        
        print(f"\nProcesando Producto {i}: {ean} - {desc[:50]}...")
        print(f"  > Evaluando legibilidad de {len(imagenes_b64)} imágenes...")
        
        # ═══════════════════════════════════════════════════════════════════
        # Lógica de Visión y OCR de Producción
        # ═══════════════════════════════════════════════════════════════════
        fotos_aprobadas, _, _ = filtrar_imagenes_legibles(imagenes_b64, desc, model)
        
        transcripciones = []
        if fotos_aprobadas:
            print(f"  > {len(fotos_aprobadas)} imágenes aprobadas. Ejecutando OCR con Gemini Flash...")
            transcripciones, _ = transcribir_imagenes_gemini(fotos_aprobadas, desc)
            
        if not fotos_aprobadas:
            nota_vision = "[Nota: No se logró conseguir ninguna imagen de calidad suficiente (legibilidad < 3). Procede usando únicamente los datos de texto web.]"
        else:
            texto_ocr = "\n".join(transcripciones)
            nota_vision = (
                f"[Nota: Se procesaron {len(fotos_aprobadas)} imagen(es) pre-aprobadas mediante OCR (Gemini Flash). "
                f"A continuación el texto extraído de las imágenes del producto:]\n\n"
                f"--- INICIO TRANSCRIPCIÓN OCR ---\n{texto_ocr}\n--- FIN TRANSCRIPCIÓN OCR ---"
            )
            
        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]
        
        prompt = prompt_template.replace(
            "{taxonomias_existentes}", taxonomias_str
        ).replace(
            "{context_json_str}", json.dumps(context_block, indent=2)
        ).replace(
            "{nota_vision}", nota_vision
        )
        
        for name, effort in scenarios:
            print(f"  > Ejecutando escenario: {name}...")
            res = llamar_openrouter_test(prompt, model, effort)
            
            if res["success"]:
                print(f"    [Éxito] Tiempo: {res['elapsed']:.1f}s | In: {res['prompt_tokens']} | Out: {res['completion_tokens']} | Reasoning: {res['reasoning_tokens']}")
                results.append({
                    "producto": desc[:45],
                    "escenario": name,
                    "tiempo": f"{res['elapsed']:.1f}s",
                    "in_tokens": res["prompt_tokens"],
                    "out_tokens": res["completion_tokens"],
                    "reasoning_tokens": res["reasoning_tokens"],
                    "total_tokens": res["prompt_tokens"] + res["completion_tokens"],
                    "resumen_respuesta": res["content"][:100].replace("\n", " ") + "..."
                })
            else:
                print(f"    [Error] {res['error']}")
                results.append({
                    "producto": desc[:45],
                    "escenario": name,
                    "tiempo": "N/A",
                    "in_tokens": 0,
                    "out_tokens": 0,
                    "reasoning_tokens": 0,
                    "total_tokens": 0,
                    "resumen_respuesta": f"ERROR: {res['error']}"
                })
                
    # Generar tabla final de comparación
    print("\n\n=== TABLA COMPARATIVA DE CONSUMO DE TOKENS (CON VISIÓN EAN) ===")
    print("| Producto | Escenario | Tiempo | In Tokens | Out Tokens | Reasoning Tokens | Total Tokens | Resumen Respuesta |")
    print("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    for r in results:
        print(f"| {r['producto']} | {r['escenario']} | {r['tiempo']} | {r['in_tokens']} | {r['out_tokens']} | {r['reasoning_tokens']} | {r['total_tokens']} | {r['resumen_respuesta']} |")

if __name__ == "__main__":
    main()
