import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("""
    SELECT TOP 200 codbarras, descripcion_mercado_concat,
           principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, marca_Des, fabricante_Des
    FROM Procurement.por_aprobacion_equivalencias
    WHERE es_medicamento = 1 
      AND descripcion_mercado_concat IS NOT NULL 
      AND (marca_Des IS NULL OR fabricante_Des IS NULL)
""")
rows = cursor.fetchall()
res = []
for r in rows:
    res.append(f"{r[0]}|{r[1]}|M:{r[5]}|F:{r[6]}")
with open("scratch/compact_200.txt", "w") as f:
    for line in res:
        f.write(line + "\n")
conn.close()
print(f"Saved {len(res)} to scratch/compact_200.txt")
