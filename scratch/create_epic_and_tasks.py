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

def create_epic(name):
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": "381c22d5-8177-8159-a848-e2ece2dde69b"},
        "properties": {
            "Name": {
                "title": [{"text": {"content": name}}]
            },
            "Estado": {
                "status": {"name": "Not started"}
            }
        }
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            print(f"Created Epic: {name} (ID: {res_data['id']})")
            return res_data['id'], res_data['url']
    except urllib.error.HTTPError as e:
        print(f"Error creating Epic: {e.read().decode('utf-8')}")
        return None, None

def create_task(name, status, priority, type_val, epic_id, sprint_id):
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
    if epic_id:
        properties["Épica"] = {
            "relation": [{"id": epic_id}]
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

def update_task_epic(task_id, epic_id):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    data = {
        "properties": {
            "Épica": {
                "relation": [{"id": epic_id}]
            }
        }
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as res:
            print(f"Updated task {task_id} with new epic")
    except urllib.error.HTTPError as e:
        print(f"Error updating task {task_id}: {e.read().decode('utf-8')}")

def main():
    epic_name = "Grafo de Conocimiento Médico (Neo4j)"
    epic_id, epic_url = create_epic(epic_name)
    
    if not epic_id:
        return
        
    sprint_id = "382c22d5-8177-818a-9328-ce752e4bcab8" # Sprint Jun 17-30
    
    # 1. Update the cross-selling task created previously
    update_task_epic("38dc22d5-8177-8149-a7c6-eca4c6c03d7a", epic_id)
    
    tasks = [
        {
            "name": "Desplegar contenedor de Neo4j en servidor Debian",
            "status": "Not started",
            "priority": "🟠 Alta",
            "type": "⚙️ Chore",
            "epic": epic_id,
            "sprint": sprint_id
        },
        {
            "name": "Importar ontologías médicas globales (RxNorm/UMLS) a Neo4j",
            "status": "Not started",
            "priority": "🟠 Alta",
            "type": "✨ Feature",
            "epic": epic_id,
            "sprint": sprint_id
        },
        {
            "name": "Desarrollar script puente (SQL -> Neo4j) usando ATC",
            "status": "Not started",
            "priority": "🟡 Media",
            "type": "🔨 Refactor",
            "epic": epic_id,
            "sprint": sprint_id
        },
        {
            "name": "Integrar consultas de Neo4j en Dify Workflows",
            "status": "Not started",
            "priority": "🟡 Media",
            "type": "✨ Feature",
            "epic": epic_id,
            "sprint": sprint_id
        }
    ]
    
    urls = []
    urls.append((epic_name, epic_url))
    for t in tasks:
        url = create_task(t["name"], t["status"], t["priority"], t["type"], t["epic"], t["sprint"])
        if url:
            urls.append((t["name"], url))
            
    print("\n=== ENLACES ===")
    for name, url in urls:
        print(f"- [{name}]({url})")

if __name__ == "__main__":
    main()
