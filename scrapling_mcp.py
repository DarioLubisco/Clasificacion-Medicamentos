from mcp.server.fastmcp import FastMCP
import urllib.request
import json

mcp = FastMCP("scrapling-mcp")

@mcp.tool()
def scrape_url(url: str) -> str:
    """Scrapes a URL using the remote Scrapling engine on the Debian server to bypass anti-bot protections and return the raw HTML."""
    data = json.dumps({'url': url}).encode('utf-8')
    req = urllib.request.Request('http://10.147.18.204:8005/scrape', data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            response_data = json.loads(res.read().decode())
            return response_data.get("content", "")
    except Exception as e:
        return f"Error scraping URL: {str(e)}"

if __name__ == "__main__":
    mcp.run()
