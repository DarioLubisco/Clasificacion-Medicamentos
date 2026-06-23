import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def update_lote5():
    # 1. Read the barcodes and strings
    codbarras_procesados = []
    updates = []
    
    with open('scratch/compact_200_5.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if '|' not in line: continue
            parts = line.strip().split('|')
            codbarras = parts[0]
            texto = line.upper()
            codbarras_procesados.append(codbarras)
            
            fabricante = None
            if "2N" in texto: fabricante = "2N"
            elif "ITN" in texto: fabricante = "ITN"
            elif "NEILMED" in texto or "SINUS " in texto or "NASAMIST" in texto: fabricante = "NEILMED"
            elif "ALL-DOVARI" in texto: fabricante = "ALL-DOVARI"
            elif "GAMA" in texto: fabricante = "GAMA"
            elif " VAL " in texto or " VAL" in texto.split("|")[1][-4:]: fabricante = "VAL"
            elif "LATTAN" in texto: fabricante = "LATTAN MEDIC"
            elif "FAHD" in texto: fabricante = "FAHD"
            elif "SNC PHARMA" in texto: fabricante = "SNC PHARMA"
            elif "KMPLUS" in texto or "KM PLUS" in texto or "KMP" in texto: fabricante = "KMPLUS"
            elif "ALPINE" in texto: fabricante = "ALPINE"
            
            if fabricante:
                updates.append((fabricante, codbarras))

    # 2. Execute updates
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    try:
        count_updated = 0
        for fab, cb in updates:
            sql = "UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = ? WHERE codbarras = ? AND fabricante_Des IS NULL"
            cursor.execute(sql, (fab, cb))
            count_updated += 1
            
        print(f"Lote 5: Actualizados {count_updated} campos de fabricante.")
        
        # 3. Mark all 200 as processed
        if codbarras_procesados:
            placeholders = ','.join(['?'] * len(codbarras_procesados))
            sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 1 WHERE codbarras IN ({placeholders})"
            cursor.execute(sql, codbarras_procesados)
            print(f"Marcados {len(codbarras_procesados)} registros como procesados (procesado_fase1 = 1).")
            
    except Exception as e:
        print("Error en actualizacion lote 5:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    update_lote5()
