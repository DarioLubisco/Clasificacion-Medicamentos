import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def update_processed_flags():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    # Vamos a marcar todos los procesados hasta ahora. 
    # Para la prueba, ya procesamos los primeros lotes, así que podemos marcarlos
    # extrayendo los codbarras de los archivos compact_200.txt y compact_200_more.txt
    codbarras_procesados = []
    
    try:
        with open('scratch/compact_200.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    codbarras_procesados.append(line.split('|')[0])
    except FileNotFoundError:
        pass

    try:
        with open('scratch/compact_200_more.txt', 'r') as f:
            for line in f:
                if '|' in line:
                    codbarras_procesados.append(line.split('|')[0])
    except FileNotFoundError:
        pass
        
    if not codbarras_procesados:
        print("No se encontraron códigos de barras para marcar.")
        return

    print(f"Marcando {len(codbarras_procesados)} registros como procesados en fase 1...")
    
    try:
        # Hacer el update en batches pequeños o en uno solo usando IN
        placeholders = ','.join(['?'] * len(codbarras_procesados))
        sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 1 WHERE codbarras IN ({placeholders})"
        cursor.execute(sql, codbarras_procesados)
        print("Banderas actualizadas correctamente.")
    except Exception as e:
        print("Error actualizando banderas:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    update_processed_flags()
