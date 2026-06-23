import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM Procurement.scraping_farmacias_raw")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE procesado_fase1=1 AND procesado_fase2=1 AND fabricante_Des IS NULL")
fase2_processed_but_null = cursor.fetchone()[0]

cursor.execute("SELECT TOP 5 url_origen FROM Procurement.scraping_farmacias_raw")
urls = cursor.fetchall()

print(f"Total urls scraped: {total}")
print(f"Items processed by phase 2 but still NULL: {fase2_processed_but_null}")
if urls:
    for u in urls:
        print(u.url_origen)

