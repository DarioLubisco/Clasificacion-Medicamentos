import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def main():
    try:
        conn = pyodbc.connect(CONN_STR, timeout=30)
        cursor = conn.cursor()
        
        print("Iniciando TRANSACCIÓN DRY-RUN...")
        
        with open('scratch/repair_ids.sql', 'r', encoding='utf-8') as f:
            queries = f.read().split(';')
            
        valid_queries = [q.strip() for q in queries if q.strip()]
        
        total_affected = 0
        
        for q in valid_queries:
            cursor.execute(q)
            total_affected += cursor.rowcount
            
        print(f"La simulación afectó un total de {total_affected} combinaciones de campos/filas.")
        
        # Validar algunos datos
        cursor.execute("SELECT TOP 5 codbarras, marca, fabricante, codigo_atc FROM Procurement.por_aprobacion_equivalencias WHERE marca IS NOT NULL")
        rows = cursor.fetchall()
        print("\nMuestra de campos llenados (IDs reales referenciando catálogos):")
        for r in rows:
            print(f"EAN: {r[0]} | MarcaID: {r[1]} | FabID: {r[2]} | ATC_ID: {r[3]}")
            
        # ROLLBACK
        conn.rollback()
        print("\nROLLBACK ejecutado exitosamente. (Ningún dato ha sido guardado aún).")
        conn.close()
        
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    main()
