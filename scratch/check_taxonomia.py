import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("SELECT dominio, categoria, subcategoria FROM Procurement.Taxonomia ORDER BY dominio, categoria")
rows = cursor.fetchall()
print(f"Total entries: {len(rows)}")
for r in rows:
    print(f"{r.dominio} | {r.categoria} | {r.subcategoria}")
conn.close()
