import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def check():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    
    queries = {
        "Total registros": "SELECT COUNT(*) FROM Procurement.por_aprobacion_equivalencias",
        "Por estado_ciclo": "SELECT estado_ciclo, COUNT(*) FROM Procurement.por_aprobacion_equivalencias GROUP BY estado_ciclo",
        "Por origen_dato": "SELECT origen_dato, COUNT(*) FROM Procurement.por_aprobacion_equivalencias GROUP BY origen_dato",
        "Por ciclos_reproceso": "SELECT ciclos_reproceso, COUNT(*) FROM Procurement.por_aprobacion_equivalencias GROUP BY ciclos_reproceso",
        "Abiertos por ciclo": "SELECT ISNULL(ciclos_reproceso, 0), COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE estado_ciclo = 'ABIERTO' GROUP BY ISNULL(ciclos_reproceso, 0)"
    }
    
    for name, q in queries.items():
        print(f"\n=== {name} ===")
        try:
            cursor.execute(q)
            for r in cursor.fetchall():
                print(r)
        except Exception as e:
            print(f"Error: {e}")
            
    conn.close()

if __name__ == '__main__':
    check()
