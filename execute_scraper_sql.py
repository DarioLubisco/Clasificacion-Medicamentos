import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json

conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=10.200.8.5\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")}'
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

with open('debug_scraper.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

count = 0
for item in results:
    codbarras = item['codbarras']
    datos = item.get('extraido', {})
    
    pa = datos.get('principio_activo')
    conc = datos.get('concentracion')
    ff = datos.get('forma_farmaceutica')
    
    # Trucate lengths for db columns
    if pa: pa = str(pa)[:100]
    if conc: conc = str(conc)[:100]
    if ff: ff = str(ff)[:100]
    
    set_clauses = []
    params = []
    
    if pa and str(pa).strip() != '' and str(pa).lower() != 'none':
        set_clauses.append('principio_activo_Des = ?')
        params.append(pa)
    if conc and str(conc).strip() != '' and str(conc).lower() != 'none':
        set_clauses.append('concentracion_Des = ?')
        params.append(conc)
    if ff and str(ff).strip() != '' and str(ff).lower() != 'none':
        set_clauses.append('forma_farmaceutica_Des = ?')
        params.append(ff)
        
    if set_clauses:
        set_clauses.append('origen_dato = ?')
        params.append('IA_SCRAPED_V10')
        params.append(codbarras)
        
        sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET {', '.join(set_clauses)} WHERE codbarras = ? AND (principio_activo_Des IS NULL OR concentracion_Des IS NULL OR forma_farmaceutica_Des IS NULL)"
        try:
            cursor.execute(sql, params)
            count += 1
        except Exception as e:
            print(f'Error updating {codbarras}: {e}')

conn.commit()
print(f'Updated {count} records using parameterized queries.')
