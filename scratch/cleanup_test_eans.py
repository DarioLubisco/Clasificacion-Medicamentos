import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
EANS_TEST = [
    '0000000030373', '0000000163774', '0000000201629', '0000000206815',
    '0000025525755', '0000025525762', '0000075971199', '0004', '0008', '001004002941515'
]

conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()

placeholders = ','.join(['?'] * len(EANS_TEST))
cursor.execute(f"DELETE FROM Procurement.scraping_farmacias_raw WHERE codbarras IN ({placeholders})", EANS_TEST)
print("Deleted rows from scraping_farmacias_raw:", cursor.rowcount)

cursor.execute(f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase2 = 0 WHERE codbarras IN ({placeholders})", EANS_TEST)
print("Updated rows in por_aprobacion_equivalencias:", cursor.rowcount)

conn.close()
