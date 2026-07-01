import urllib.request
import json
import sys
import os
from dotenv import load_dotenv

# Cargar dotenv desde la raíz del proyecto si es posible
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

TOKEN = os.getenv("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def create_task(title, status, priority, tipo, epic_id, sprint_id, sql_code=""):
    data = {
        "parent": {"database_id": "381c22d5-8177-81fb-89ee-e34715f74d63"},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Estado": {"status": {"name": status}},
            "Prioridad": {"select": {"name": priority}},
            "Tipo": {"select": {"name": tipo}},
            "Épica": {"relation": [{"id": epic_id}]},
            "Sprint": {"relation": [{"id": sprint_id}]}
        }
    }
    
    if sql_code:
        data["children"] = [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "language": "sql",
                    "rich_text": [{"type": "text", "text": {"content": sql_code}}]
                }
            }
        ]
        
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=json.dumps(data).encode('utf-8'),
        headers=HEADERS,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            resp = json.loads(res.read().decode())
            print(f"Created: {resp.get('url')}")
    except Exception as e:
        print(f"Error creating task: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode())

epic_id = "387c22d5-8177-816d-9d81-f059ef66f248"
sprint_id = "382c22d5-8177-818a-9328-ce752e4bcab8"

sql_text = """BEGIN TRANSACTION;

-- (Sentencias UPDATE de los medicamentos analizados)
UPDATE Procurement.por_aprobacion_equivalencias SET principio_activo_Des = 'Buprenorfina', ... WHERE codbarras = '759100000001';
-- (Sentencias INSERT para las imágenes pre-aprobadas)
INSERT INTO Procurement.Imagenes_Productos_Crudas (codbarras, url_imagen, score_legibilidad) VALUES ('...', '...', 1);

COMMIT;
"""

create_task(
    title="Implementar Orquestador SQL (generar scripts SQL desde resultados)",
    status="Done",
    priority="🟡 Media",
    tipo="✨ Feature",
    epic_id=epic_id,
    sprint_id=sprint_id
)

create_task(
    title="Ejecutar sentencias SQL de resultados",
    status="Not started",
    priority="🟡 Media",
    tipo="⚙️ Chore",
    epic_id=epic_id,
    sprint_id=sprint_id,
    sql_code=sql_text
)
