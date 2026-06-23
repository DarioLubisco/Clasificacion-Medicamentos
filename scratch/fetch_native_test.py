import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("""
    SELECT TOP 3 codbarras, descrip1art, principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, descripcion_mercado_concat 
    FROM Procurement.por_aprobacion_equivalencias
    WHERE es_medicamento = 1 
      AND descripcion_mercado_concat IS NOT NULL 
      AND (principio_activo_Des IS NOT NULL)
      AND (concentracion_Des IS NULL)
      AND descrip1art LIKE '%mg%'
""")
rows = cursor.fetchall()
print("Con concentracion en descrip pero no en BD:")
for r in rows:
    print(r)
conn.close()
