import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("""
    SELECT TOP 100 codbarras, descripcion_mercado_concat,
           principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, marca_Des, fabricante_Des, contenido_neto
    FROM Procurement.por_aprobacion_equivalencias
    WHERE es_medicamento = 1 
      AND descripcion_mercado_concat IS NOT NULL 
      AND (principio_activo_Des IS NULL OR concentracion_Des IS NULL OR forma_farmaceutica_Des IS NULL OR marca_Des IS NULL OR fabricante_Des IS NULL)
""")
rows = cursor.fetchall()
res = []
for r in rows:
    res.append({
        "EAN": r[0],
        "Desc": r[1],
        "Act": r[2],
        "Con": r[3],
        "Form": r[4],
        "Marca": r[5],
        "Fab": r[6],
        "Net": r[7]
    })
with open("scratch/batch_100.json", "w") as f:
    json.dump(res, f, indent=2)
conn.close()
print("Saved 100 to scratch/batch_100.json")
