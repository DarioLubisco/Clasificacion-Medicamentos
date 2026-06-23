import os
from dotenv import load_dotenv
load_dotenv()
import json
import urllib.request

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def test_qwen():
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = """
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
      {
        "registro": {"codigo": "...", "codbarras": "...", "descripcion_original": "...", "ciclos_reproceso": 0},
        "atributos_ya_encontrados": {},
        "atributos_nuevos_consolidados": {"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": "ADULTO", "origen": "IA", "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}
      }
    ]

    LOTE A PROCESAR:
    [
      {
        "registro": {"codigo": "111", "codbarras": "111", "descripcion_original": "TYLENOL CAJA X 20 TABLETAS", "ciclos_reproceso": 0},
        "atributos_ya_encontrados": {"forma_farmaceutica": "Tableta", "cantidad_presentacion": 20}
      },
      {
        "registro": {"codigo": "222", "codbarras": "222", "descripcion_original": "IBUPROFENO SUSPENSION PEDIATRICA 120ML", "ciclos_reproceso": 1},
        "atributos_ya_encontrados": {"principio_activo": "IBUPROFENO", "concentracion": "500MG", "segmento_etario": "ADULTO"} 
      }
    ]
    """

    data = {
        "model": "qwen/qwen-2.5-72b-instruct", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode())
        content = result['choices'][0]['message']['content']
        print(content)

if __name__ == '__main__':
    test_qwen()
