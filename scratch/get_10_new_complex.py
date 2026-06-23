import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()

prev_eans = ['0000000072410', '0000000104098', '0000020000264', '0000001100181', '0000001100198', '0000025525748', '000000000130', '0000000107839', '0000000193009', '0000075970543']

placeholders = ','.join(['?'] * len(prev_eans))
query = f"""
SELECT TOP 10 codbarras, descrip1art 
FROM Procurement.por_aprobacion_equivalencias 
WHERE codbarras NOT IN ({placeholders}) 
AND (
    descrip1art LIKE '%SUSP%' OR 
    descrip1art LIKE '%AMP%' OR 
    descrip1art LIKE '%GOTAS%' OR 
    descrip1art LIKE '%INY%' OR 
    descrip1art LIKE '%POLVO%' OR
    descrip1art LIKE '%JARABE%' OR
    descrip1art LIKE '%JBE%' OR
    descrip1art LIKE '%SOL %'
)
"""
cursor.execute(query, prev_eans)
for r in cursor.fetchall():
    print(f"'{r[0]}', # {r[1]}")
conn.close()
