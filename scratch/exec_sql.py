import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR, autocommit=True)
cursor = conn.cursor()
with open('scratch/update_100_fase1.sql', 'r') as f:
    sql = f.read()

# sqlcmd batches separated by GO aren't used here, we just execute the whole block
try:
    cursor.execute(sql)
    print("Ejecucion exitosa de Fase 1 para el lote de 100.")
except Exception as e:
    print("Error:", e)
conn.close()
