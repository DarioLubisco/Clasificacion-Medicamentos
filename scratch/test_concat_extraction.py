import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_incomplete_products():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 20 codbarras, descrip1art, descripcion_mercado_concat 
        FROM Procurement.por_aprobacion_equivalencias
        WHERE es_medicamento = 1 
          AND descripcion_mercado_concat IS NOT NULL 
          AND (principio_activo_Des IS NULL OR concentracion_Des IS NULL OR forma_farmaceutica_Des IS NULL)
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"codbarras": r[0], "descrip1art": r[1], "descripcion_mercado_concat": r[2]} for r in rows]

def run_extraction(products):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # We construct a clean instructions prompt
    prompt = """
    Analiza las descripciones concatenadas de Mercado Vivo para cada uno de los siguientes productos farmacéuticos.
    Extrae la información faltante con máxima precisión. Si no se puede deducir de forma segura, devuelve null.
    
    Atributos a extraer:
    1. principio_activo (Molécula activa o principio activo. Ej: Losartán, Ibuprofeno, etc.)
    2. concentracion (Ej: 500mg, 50mg/ml, etc.)
    3. forma_farmaceutica (Ej: Tabletas, Cápsulas, Jarabe, Suspensión, etc.)
    4. marca (Nombre comercial. Ej: Atamel, Tempra, etc.)
    5. fabricante (Laboratorio)
    6. contenido_neto (Volumen o peso total, Ej: 120ml, 15g)

    Devuelve un objeto JSON estructurado con la clave "productos" que sea un array de objetos con este formato:
    {
      "codbarras": "...",
      "principio_activo": "...",
      "concentracion": "...",
      "forma_farmaceutica": "...",
      "marca": "...",
      "fabricante": "...",
      "contenido_neto": "..."
    }
    
    Productos a analizar:
    """ + json.dumps(products, indent=2)

    data = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            content = result['choices'][0]['message']['content']
            return json.loads(content)
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        return None

def main():
    print("Obteniendo 20 productos incompletos...")
    products = get_incomplete_products()
    print(f"Productos obtenidos: {len(products)}")
    
    print("Invocando a la IA para extracción de atributos...")
    extracted = run_extraction(products)
    
    if not extracted or "productos" not in extracted:
        print("Error en la extracción.")
        return
        
    print("\n--- RESULTADOS DE LA PRUEBA DE EXTRACCIÓN ---")
    for prod in extracted["productos"]:
        # Find original description to display
        orig = next((p for p in products if p["codbarras"] == prod["codbarras"]), {})
        print(f"\nEAN: {prod['codbarras']}")
        print(f"Original: {orig.get('descrip1art')}")
        print(f"Concatenado Mercado: {orig.get('descripcion_mercado_concat')}")
        print(f"  -> Principio Activo: {prod.get('principio_activo')}")
        print(f"  -> Concentración: {prod.get('concentracion')}")
        print(f"  -> Forma Farmacéutica: {prod.get('forma_farmaceutica')}")
        print(f"  -> Marca: {prod.get('marca')}")
        print(f"  -> Fabricante: {prod.get('fabricante')}")
        print(f"  -> Contenido Neto: {prod.get('contenido_neto')}")

if __name__ == "__main__":
    main()
