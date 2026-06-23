import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Mercado%' OR TABLE_NAME LIKE '%Vivo%'")
for r in cursor.fetchall():
    print(r)
conn.close()
