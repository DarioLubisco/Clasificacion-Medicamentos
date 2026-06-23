import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import time

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def generar_taxonomia_llm():
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = """
    Actúa como un taxonomista experto en productos de farmacia y supermercado.
    Tu objetivo es generar un CATÁLOGO MAESTRO de taxonomías (Categoría y Subcategoría) para los siguientes 6 dominios:
    1. MEDICAMENTO_ALOPATICO (Ej. ANALGESICOS -> PARACETAMOL, ANTIBIOTICOS -> AMOXICILINA, CARDIOVASCULAR -> ANTIHIPERTENSIVOS...)
    2. PRODUCTO_NATURAL_HOMEOPATICO (Ej. SUPLEMENTOS NATURALES -> VALERIANA, FITOTERAPIA -> GINKGO BILOBA...)
    3. SUPLEMENTO_VITAMINICO (Ej. VITAMINAS -> VITAMINA C, MULTIVITAMINICOS -> ADULTOS...)
    4. COSMETICO_CUIDADO_PERSONAL (Ej. CUIDADO CAPILAR -> CHAMPU, CUIDADO BUCAL -> CREMA DENTAL...)
    5. MATERIAL_MEDICO_INSUMO (Ej. INYECTADORAS -> JERINGAS, MATERIAL DE CURACION -> GASAS...)
    6. MISCELANEO (Ej. ALIMENTOS -> SNACKS, BEBIDAS -> AGUA, MISCELANEO -> VARIOS...)

    Reglas:
    - Genera al menos 15-20 combinaciones comunes por dominio para abarcar el 95% de los productos de una farmacia/retailer.
    - Sé preciso, no uses subcategorías exageradamente específicas.
    - Devuelve ÚNICAMENTE un JSON válido que sea una lista de objetos:
    [
      {"dominio": "MEDICAMENTO_ALOPATICO", "categoria": "ANALGESICOS Y ANTIPIRETICOS", "subcategoria": "PARACETAMOL"},
      {"dominio": "MEDICAMENTO_ALOPATICO", "categoria": "ANALGESICOS Y ANTIPIRETICOS", "subcategoria": "IBUPROFENO"},
      ...
    ]
    """
    
    data = {
        "model": "google/gemini-2.5-pro", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    print("Llamando a Gemini 2.5 Pro para generar la taxonomía base...")
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())
        content = result.get('choices', [{}])[0].get('message', {}).get('content')
        if not content:
            print("ERROR: La IA no devolvió 'content'. Raw result:", json.dumps(result))
            return None
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        data_json = json.loads(content.strip())
        # A veces envuelven la lista en un dict
        if isinstance(data_json, dict):
            for k, v in data_json.items():
                if isinstance(v, list):
                    return v
        return data_json

def sembrar_bd(taxonomia):
    print(f"Sembrando {len(taxonomia)} registros en la BD...")
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    
    # Limpiamos tabla solo por si acaso
    cursor.execute("DELETE FROM Procurement.Taxonomia;")
    
    insert_query = "INSERT INTO Procurement.Taxonomia (dominio, categoria, subcategoria, activo) VALUES (?, ?, ?, 1)"
    count = 0
    for item in taxonomia:
        try:
            d = str(item.get('dominio', 'SINEVAL')).strip().upper()
            c = str(item.get('categoria', 'SINEVAL')).strip().upper()
            s = str(item.get('subcategoria', 'SINEVAL')).strip().upper()
            
            # Limpiar nombres para que sean estandar
            cursor.execute(insert_query, (d, c, s))
            count += 1
        except Exception as e:
            print(f"Error insertando {item}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Sembrados {count} registros exitosamente.")

if __name__ == "__main__":
    tax = generar_taxonomia_llm()
    if tax:
        sembrar_bd(tax)
    else:
        print("Fallo la generacion.")
