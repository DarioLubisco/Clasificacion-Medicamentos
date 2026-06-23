import requests
url = 'https://www.farmadon.com.ve/producto/discolayte-polvo-69-7gr-distrilab/'
response = requests.post("http://127.0.0.1:8005/scrape", json={"url": url}, timeout=45)
print(response.status_code, response.text)
