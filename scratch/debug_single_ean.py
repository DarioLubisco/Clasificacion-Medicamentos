import os
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import json
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def obtener_taxonomias_estrictas():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
    tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
    conn.close()
    return "\n".join(tax)

def main():
    taxonomias_str = obtener_taxonomias_estrictas()
    ean = '0000000030373'
    desc = "DISCOLAYTE POLVO 69.7 G X 10 SOBRES"
    
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("SELECT texto_extraido FROM Procurement.scraping_farmacias_raw WHERE codbarras = ?", (ean,))
    bloques = cursor.fetchall()
    conn.close()
    
    fuentes_web = [{"url": "http://mock", "texto": b[0]} for b in bloques if b[0]]
    context_block = [{
        "registro": {"codbarras": ean, "descripcion_original": desc},
        "fuentes_web": fuentes_web
    }]
    
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos y sus descripciones, contextos web y TAMBIÉN IMÁGENES de referencia que debes analizar junto con el texto.
    Tu único objetivo es la PRECISIÓN ABSOLUTA (Zero-Tolerance). Extraer un dato que no está explícitamente en la descripción, en el contexto web adjunto o en las imágenes de referencia es un ERROR CRÍTICO. Ante la menor duda, debes devolver null.

    Analiza TODOS los elementos proporcionados (texto y visuales) para extraer los siguientes atributos:
    - dominio (string OBLIGATORIO)
    - categoria (string OBLIGATORIO)
    - subcategoria (string OBLIGATORIO)
    - principio_activo (string o null si no aplica/es insumo)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)
    - cantidad_presentacion (int o null)
    - contenido_neto (float o null, formato numérico entero si no tiene decimales ej. 500)
    - contenido_neto_unidad_Des (string o null)
    - fabricante (string o null)
    - marca (string o null)
    - origen (string o null)
    - codigo_atc (string o null)
    - blister (1 o 0)
    - generico (1 o 0)
    - clasificacion_insumo_Des (string o null, ej: Inyectadora, Pañal)

    REGLAS ESTRICTAS ANTI-ALUCINACIÓN Y DE NEGOCIO:
    1. ATC: NO deduzcas el código ATC. Solo extráelo si aparece explícitamente.
    2. Sólidos vs Líquidos/Tópicos: 
       - Sólidos (Tabletas/Cápsulas): cantidad_presentacion = total de unidades (ej. 20), contenido_neto = 1, contenido_neto_unidad_Des = 'Caja' o 'Blister'.
       - Líquidos/Cremas/Pomadas: cantidad_presentacion = total de envases (ej. 1), contenido_neto = volumen/peso (ej. 120 o 500 sin decimales '.0'), contenido_neto_unidad_Des = 'ml' o 'g'.
    3. Forma Farmacéutica: Simplifica formas complejas a su familia base (ej. "Comprimido de liberación prolongada" -> "Comprimido"). MANTÉN la vía de administración si es crítica (ej. "Solución Oftálmica").
    4. Marca / Fabricante / Origen: Si no hay información explícita, usa null. NO asumas 'Genérico' como marca. Si ves el laboratorio en la caja de la imagen, utilízalo.
    5. Segmento Etario: NO lo deduzcas sin evidencia (infantil, niños, pediátrico, adulto). Ante la duda, null.

    REGLA DE TAXONOMIA (INQUEBRANTABLE):
    {taxonomias_str}
    
    NIVELES DE CONFIANZA (OBLIGATORIOS):
    Debes autoevaluar tu clasificación usando un "confianza_nivel" (entero del 1 al 5) y explicarlo en "confianza_razonamiento".
    5 - TOTAL: Dato explícito, inequívoco, sin contradicciones en el contexto web o imagen.
    4 - ALTA: Se deduce lógicamente con total certeza científica, aunque haya diferencias menores en campos no críticos.
    3 - MEDIA: Información suficiente pero con discrepancias entre sitios o ambigüedad leve.
    2 - BAJA: Inferencias o aproximaciones por información escasa o contradictoria.
    1 - NULA: Falta de información crítica.
    
    Devuelve ÚNICAMENTE un array JSON válido con este formato exacto:
    [
      {{
        "registro": {{"codbarras": "...", "descripcion_original": "..."}},
        "atributos_nuevos_consolidados": {{"razonamiento": "...", "confianza_nivel": 5, "confianza_razonamiento": "...", "dominio": "...", "categoria": "...", "subcategoria": "...", "principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "...", "requiere_recipe": 1, "segmento_etario": null, "origen": null, "fabricante": null, "marca": null, "codigo_atc": null, "cantidad_presentacion": null, "contenido_neto": null, "contenido_neto_unidad_Des": null, "blister": 0, "generico": 0, "clasificacion_insumo_Des": null}}
      }}
    ]

    LOTE A PROCESAR (Contexto Web Incluido):
    {json.dumps(context_block, indent=2)}
    """
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    content_payload = [{"type": "text", "text": prompt}]
    
    data = {
        "model": "google/gemini-2.5-pro", 
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.1
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
