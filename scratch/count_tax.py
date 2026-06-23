import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(DISTINCT dominio), COUNT(DISTINCT categoria), COUNT(DISTINCT subcategoria) FROM Procurement.Taxonomia")
row = cursor.fetchone()
print(f"Dominios: {row[0]}")
print(f"Categorias: {row[1]}")
print(f"Subcategorias: {row[2]}")

print("\nDominios:")
cursor.execute("SELECT dominio, COUNT(*) FROM Procurement.Taxonomia GROUP BY dominio")
for r in cursor.fetchall():
    print(f"- {r[0]}: {r[1]} combinaciones")
conn.close()
