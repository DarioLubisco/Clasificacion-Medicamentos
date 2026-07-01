import urllib.request
import json
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

def patch_task_status(task_id, status_name):
    url = f"https://api.notion.com/v1/pages/{task_id}"
    data = {
        "properties": {
            "Estado": {
                "status": {
                    "name": status_name
                }
            }
        }
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as res:
            print(f"Updated status for task {task_id} to {status_name}")
            return True
    except Exception as e:
        print(f"Error updating task {task_id}: {e}")
        return False

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
            print(f"Created task: {name} (ID: {res_data['id']})")
            return res_data['url']
    except Exception as e:
        print(f"Error creating task '{name}': {e}")
        # Print response body if available for debugging
        if hasattr(e, 'read'):
            print(e.read().decode("utf-8"))
        return None

def main():
    print("=== INICIANDO SINCRONIZACIÓN EN NOTION ===")
    
    # 1. Update existing task "Implementar Prueba Quirúrgica (Top 5)" to Done
    patch_task_status("387c22d5-8177-8120-89af-f6053ef70254", "Done")
    
    # Sprints and Epics IDs
    sprint_id = "382c22d5-8177-818a-9328-ce752e4bcab8" # Sprint Jun 17-30
    epic_orquestador = "387c22d5-8177-816d-9d81-f059ef66f248" # Orquestador
    epic_analytics = "382c22d5-8177-8176-99ae-c655c68d34ab" # Analytics Engine v2.0
    
    # 2. Create the 4 tasks
    tasks_to_create = [
        {
            "name": "Oficializar Prompt V2 e inyectar en el Orquestador",
            "status": "Done",
            "priority": "🟠 Alta",
            "type": "🔨 Refactor",
            "epic": epic_orquestador,
            "sprint": sprint_id
        },
        {
            "name": "Ejecutar Alteración de Tabla SQL para soporte de Agente V2 (especificacion_tecnica)",
            "status": "Not started",
            "priority": "🟠 Alta",
            "type": "⚙️ Chore",
            "epic": epic_orquestador,
            "sprint": sprint_id
        },
        {
            "name": "Extraer Registro Sanitario y Condición de Venta en la Clasificación",
            "status": "Not started",
            "priority": "🟡 Media",
            "type": "✨ Feature",
            "epic": epic_orquestador,
            "sprint": sprint_id
        },
        {
            "name": "Diseñar e implementar Grafo de Venta Cruzada (Cross-Selling) para Insumos",
            "status": "Not started",
            "priority": "🟢 Baja",
            "type": "✨ Feature",
            "epic": epic_analytics,
            "sprint": sprint_id
        }
    ]
    
    urls = []
    for t in tasks_to_create:
        url = create_task(t["name"], t["status"], t["priority"], t["type"], t["epic"], t["sprint"])
        if url:
            urls.append((t["name"], url))
            
    print("\n=== RESUMEN DE ENLACES CREADOS ===")
    for name, url in urls:
        print(f"- [{name}]({url})")

if __name__ == "__main__":
    main()
