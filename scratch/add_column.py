import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
conn.autocommit = True
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE Procurement.por_aprobacion_equivalencias ADD descripcion_mercado_concat NVARCHAR(MAX);")
    print("Column added.")
except pyodbc.Error as e:
    print(f"Error (maybe already exists?): {e}")

# Now backfill the existing records
update_sql = """
UPDATE p
SET p.descripcion_mercado_concat = sub.raw_desc
FROM Procurement.por_aprobacion_equivalencias p
JOIN (
    SELECT codigo_barras, STRING_AGG(descripcion_producto, ' | ') AS raw_desc
    FROM Analitica.Mercado_Vivo_PDR
    GROUP BY codigo_barras
) sub ON p.codbarras = sub.codigo_barras
WHERE p.descripcion_mercado_concat IS NULL
"""
cursor.execute(update_sql)
print(f"Backfilled rows: {cursor.rowcount}")

conn.close()
