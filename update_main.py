import os
from dotenv import load_dotenv
load_dotenv()
import paramiko

MAIN_PY = """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scrapling import Fetcher
import uvicorn

app = FastAPI(title="Scrapling API Bridge")

class ScrapeRequest(BaseModel):
    url: str
    wait_selector: str = None
    timeout: int = 30000

@app.post("/scrape")
def scrape_url(request: ScrapeRequest):
    try:
        fetcher = Fetcher(stealth=True, headless=True)
        page = fetcher.get(request.url)
        # scrapling fetcher returns a Response object
        # which usually has `.text`
        content = page.text if hasattr(page, 'text') else str(page)
        return {"url": request.url, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

host = '10.147.18.204'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, 22, 'root', os.getenv("DEBIAN_PASSWORD"))

sftp = ssh.open_sftp()
with sftp.file('/opt/scrapling-mcp/main.py', 'w') as f:
    f.write(MAIN_PY)

print("Restarting docker container...")
stdin, stdout, stderr = ssh.exec_command('cd /opt/scrapling-mcp && docker compose build && docker compose up -d')
print(stdout.read().decode())
ssh.close()
print("Done.")
