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

@app.post("/scrape")
def scrape_url(request: ScrapeRequest):
    try:
        fetcher = Fetcher(stealth=True, headless=True)
        page = fetcher.get(request.url)
        content = page.body.decode("utf-8") if isinstance(page.body, bytes) else str(page.body)
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

ssh.exec_command('cd /opt/scrapling-mcp && docker compose build && docker compose up -d')
ssh.close()
