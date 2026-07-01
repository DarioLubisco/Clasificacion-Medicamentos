import urllib.request
import json
import urllib.error
import os
from dotenv import load_dotenv

# Cargar dotenv desde la raíz del proyecto si es posible
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

token = os.getenv("NOTION_TOKEN")
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def create_task(name, status, priority, type_val, sprint_id):
    url = "https://api.notion.com/v1/pages"
    properties = {
        "Name": {
            "title": [{"text": {"content": name}}]
        },
        "Estado": {
            "status": {"name": status}
        },
        "Prioridad": {
            "select": {"name": priority}
        },
        "Tipo": {
            "select": {"name": type_val}
        }
    }
    if sprint_id:
        properties["Sprint"] = {
            "relation": [{"id": sprint_id}]
        }
        
    data = {
        "parent": {"database_id": "381c22d5-8177-81fb-89ee-e34715f74d63"},
        "properties": properties
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            print(f"Created task: {name}")
            return res_data['url']
    except urllib.error.HTTPError as e:
        print(f"Error creating task '{name}': {e.read().decode('utf-8')}")
        return None

def main():
    sprint_id = "382c22d5-8177-818a-9328-ce752e4bcab8" # Sprint Jun 17-30
    
    tasks = [
        {
            "name": "Actualizar Prompt V2: Extraer registro_sanitario y afinar requiere_recipe (Psicotrópicos)",
            "status": "Done",
            "priority": "🔴 Crítica",
            "type": "✨ Feature",
            "sprint": sprint_id
        },
        {
            "name": "Alterar tabla por_aprobacion_equivalencias (PK Compuesta: codigo + modelo_ia_Des) para Multi-Agente",
            "status": "Not started",
            "priority": "🔴 Crítica",
            "type": "🔨 Refactor",
            "sprint": sprint_id
        },
        {
            "name": "Refactorizar Orquestador Python V2 a UPSERT (MERGE) para soportar N modelos por producto",
            "status": "Not started",
            "priority": "🟠 Alta",
            "type": "🔨 Refactor",
            "sprint": sprint_id
        },
        {
            "name": "Diseñar Job de Depuración y Consenso Multi-Agente para promoción a PROCUREMENT.equivalencias",
            "status": "Not started",
            "priority": "🟡 Media",
            "type": "✨ Feature",
            "sprint": sprint_id
        }
    ]
    
    urls = []
    for t in tasks:
        url = create_task(t["name"], t["status"], t["priority"], t["type"], t["sprint"])
        if url:
            urls.append((t["name"], url))
            
    print("\n=== ENLACES A NOTION ===")
    for name, url in urls:
        print(f"- [{name}]({url})")

if __name__ == "__main__":
    main()
