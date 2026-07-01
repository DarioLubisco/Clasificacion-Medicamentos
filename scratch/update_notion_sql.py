import urllib.request
import json
import os
import sys
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

PAGE_ID = "38dc22d5817781eeb757eda3ca1f6bbf"

def update_notion_sql():
    sql_path = sys.argv[1] if len(sys.argv) > 1 else "scratch/actualizacion_resultados_20_vision.sql"
    if not os.path.exists(sql_path):
        print(f"Error: {sql_path} does not exist.")
        return
        
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split sql_content into chunks of 2000 characters
    chunks = [sql_content[i:i+2000] for i in range(0, len(sql_content), 2000)]
    rich_text = [{"type": "text", "text": {"content": chunk}} for chunk in chunks]

    # First, list blocks on the page to delete the existing code block
    req_list = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
        headers=HEADERS,
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req_list) as res:
            blocks = json.loads(res.read().decode()).get("results", [])
            for block in blocks:
                # Delete existing blocks
                block_id = block["id"]
                req_del = urllib.request.Request(
                    f"https://api.notion.com/v1/blocks/{block_id}",
                    headers=HEADERS,
                    method="DELETE"
                )
                urllib.request.urlopen(req_del)
                print(f"Deleted old block {block_id}")
    except Exception as e:
        print(f"Error deleting old blocks: {e}")

    # Append the new code block
    data = {
        "children": [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "language": "sql",
                    "rich_text": rich_text
                }
            }
        ]
    }
    
    req_append = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
        data=json.dumps(data).encode('utf-8'),
        headers=HEADERS,
        method="PATCH"
    )
    
    try:
        with urllib.request.urlopen(req_append) as res:
            print("Successfully updated Notion task with actual SQL!")
    except Exception as e:
        print(f"Error appending new block: {e}")
        if hasattr(e, "read"):
            print(e.read().decode())

if __name__ == "__main__":
    update_notion_sql()
