import os
from dotenv import load_dotenv
load_dotenv()
import paramiko
import os

DOCKER_COMPOSE = """
version: '3.8'

services:
  scrapling-mcp:
    build: .
    container_name: scrapling-mcp
    restart: unless-stopped
    ports:
      - "8005:8000"
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 1536M
"""

DOCKERFILE = """
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

RUN pip install --no-cache-dir scrapling[all] curl_cffi playwright browserforge fastapi uvicorn pydantic cloakbrowser
RUN python -m cloakbrowser install

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

MAIN_PY = """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cloakbrowser import launch
import uvicorn

app = FastAPI(title="CloakBrowser API Bridge")

class ScrapeRequest(BaseModel):
    url: str
    wait_selector: str = None
    timeout: int = 30000

@app.post("/scrape")
def scrape_url(request: ScrapeRequest):
    try:
        # Initialize CloakBrowser
        browser = launch(headless=True)
        page = browser.new_page()
        page.goto(request.url, timeout=request.timeout)
        content = page.content()
        browser.close()
        
        return {"url": request.url, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

def deploy():
    host = "10.147.18.204"
    port = 22
    username = "root"
    password = os.getenv("DEBIAN_PASSWORD")
    
    print(f"Connecting to {host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)
    
    print("Creating directory /opt/scrapling-mcp...")
    ssh.exec_command("mkdir -p /opt/scrapling-mcp")
    
    sftp = ssh.open_sftp()
    
    def write_file(filename, content):
        path = f"/opt/scrapling-mcp/{filename}"
        with sftp.file(path, 'w') as f:
            f.write(content)
        print(f"Written {path}")

    write_file("docker-compose.yaml", DOCKER_COMPOSE)
    write_file("Dockerfile", DOCKERFILE)
    write_file("main.py", MAIN_PY)
    
    print("Running docker compose up...")
    stdin, stdout, stderr = ssh.exec_command("cd /opt/scrapling-mcp && docker compose up -d --build")
    print("STDOUT:", stdout.read().decode())
    print("STDERR:", stderr.read().decode())
    
    ssh.close()
    print("Deployment complete!")

if __name__ == "__main__":
    deploy()
