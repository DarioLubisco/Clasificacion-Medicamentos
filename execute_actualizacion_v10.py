import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import re

conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=10.200.8.5\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")}'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

print("Leyendo actualizacion_scraper_v10.sql...")
with open('actualizacion_scraper_v10.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Dividir por líneas para ejecutar una a una (excepto BEGIN TRANSACTION y COMMIT que los manejamos con pyodbc)
statements = []
for line in sql_content.splitlines():
    line = line.strip()
    if not line:
        continue
    if "BEGIN TRANSACTION" in line or "COMMIT" in line:
        continue
    if line.startswith("UPDATE"):
        statements.append(line)

print(f"Detectadas {len(statements)} sentencias UPDATE para ejecutar.")

success_count = 0
try:
    for stmt in statements:
        cursor.execute(stmt)
        success_count += 1
    
    conn.commit()
    print(f"¡Éxito! Se ejecutaron y confirmaron {success_count} sentencias UPDATE en la base de datos.")
except Exception as e:
    conn.rollback()
    print(f"Error durante la ejecución. Se realizó ROLLBACK. Detalle: {e}")
finally:
    conn.close()
