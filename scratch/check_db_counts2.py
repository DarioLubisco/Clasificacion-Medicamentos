import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM Procurement.scraping_farmacias_raw")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM Procurement.scraping_farmacias_raw WHERE procesado_fase3 = 0")
pending = cursor.fetchone()[0]

print(f"Total en raw: {total}")
print(f"Pendientes fase 3: {pending}")

cursor.execute("SELECT COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE procesado_fase1=1 AND procesado_fase2=0 AND fabricante_Des IS NULL")
fase2_pendientes = cursor.fetchone()[0]
print(f"Pendientes fase 2: {fase2_pendientes}")
