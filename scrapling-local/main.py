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
