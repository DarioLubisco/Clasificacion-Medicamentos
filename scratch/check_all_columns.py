import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Procurement' AND TABLE_NAME = 'por_aprobacion_equivalencias'")
columns = [row[0] for row in cursor.fetchall()]
print(json.dumps(columns))
conn.close()
