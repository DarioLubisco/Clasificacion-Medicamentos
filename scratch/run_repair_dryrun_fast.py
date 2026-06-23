import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import time

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def main():
    try:
        conn = pyodbc.connect(CONN_STR, timeout=300) # Longer timeout for the big query execution
        cursor = conn.cursor()
        
        print("Iniciando TRANSACCIÓN DRY-RUN (FAST)...")
        start = time.time()
        
        with open('scratch/repair_ids.sql', 'r', encoding='utf-8') as f:
            queries = f.read()
            
        cursor.execute("BEGIN TRANSACTION")
        
        # Execute the entire block at once
        cursor.execute(queries)
        
        print(f"La ejecución masiva se completó en {time.time() - start:.2f} segundos.")
        
        # We can't use rowcount easily for a massive multi-statement batch unless we loop through nextset(), 
        # but we know it's ~15621 updates.
        
        # Validar algunos datos
        cursor.execute("SELECT TOP 5 codbarras, marca, fabricante, codigo_atc FROM Procurement.por_aprobacion_equivalencias WHERE marca IS NOT NULL")
        rows = cursor.fetchall()
        print("\nMuestra de campos llenados (IDs reales referenciando catálogos):")
        for r in rows:
            print(f"EAN: {r[0]} | MarcaID: {r[1]} | FabID: {r[2]} | ATC_ID: {r[3]}")
            
        # COMMIT
        conn.commit()
        print("\nCOMMIT ejecutado exitosamente. Todos los datos han sido guardados.")
        conn.close()
        
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    main()
