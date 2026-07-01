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
    except urllib.error.HTTPError as e:
        print(f"Error updating task {task_id}: {e.read().decode('utf-8')}")
        return False

def main():
    patch_task_status("38dc22d5-8177-817b-8edf-f22e5ffe101a", "Done")

if __name__ == "__main__":
    main()
