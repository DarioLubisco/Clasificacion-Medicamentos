import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json

conn = pyodbc.connect(f'Driver={{ODBC Driver 17 for SQL Server}};Server=10.200.8.5\\efficacis3;Database=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};')
cursor = conn.cursor()

cursor.execute("SELECT codigo, codbarras, descrip1art FROM Procurement.por_aprobacion_equivalencias WHERE principio_activo_Des IS NULL AND clasificacion_insumo_Des IS NULL")
rows = cursor.fetchall()

result = []
for row in rows:
    result.append({
        "codigo": row[0],
        "codbarras": row[1] if row[1] else "",
        "descrip1art": row[2] if row[2] else ""
    })

with open('input_scraper_v10.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Exportados {len(result)} registros a input_scraper_v10.json")
