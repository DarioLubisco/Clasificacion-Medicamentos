import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def update_lote7():
    # 1. Read the barcodes and strings
    codbarras_procesados = []
    updates = []
    
    with open('scratch/compact_400_7.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if '|' not in line: continue
            parts = line.strip().split('|')
            codbarras = parts[0]
            texto = line.upper()
            codbarras_procesados.append(codbarras)
            
            fabricante = None
            # Old rules
            if "SPEFAR" in texto: fabricante = "SPEFAR"
            elif "PSICOFARMA" in texto: fabricante = "PSICOFARMA"
            elif "H & M" in texto or "H&M" in texto: fabricante = "H&M"
            elif "S&G" in texto or "S & G" in texto: fabricante = "S&G"
            elif "KMPLUS" in texto or "KM PLUS" in texto: fabricante = "KMPLUS"
            elif "GLOBAL MEDIC" in texto or "GLOBALMEDIC" in texto: fabricante = "GLOBAL MEDIC"
            elif "MALLEN" in texto: fabricante = "MALLEN"
            elif "ALPHARMA" in texto: fabricante = "ALPHARMA"
            elif " NOW " in texto or "(NOW)" in texto or "NOW DE VENEZUELA" in texto: fabricante = "NOW"
            elif " ALFA " in texto or "(ALFA)" in texto: fabricante = "ALFA"
            elif " PISA " in texto or "(PISA)" in texto: fabricante = "PISA"
            elif "SAN LORENZO" in texto: fabricante = "SAN LORENZO"
            elif "ARTE MEDICO" in texto: fabricante = "ARTE MEDICO"
            elif "EXELTIS" in texto: fabricante = "EXELTIS"
            elif "FAHD" in texto: fabricante = "FAHD"
            elif "LATTAN" in texto: fabricante = "LATTAN MEDIC"
            elif "GAMA" in texto: fabricante = "GAMA"
            elif "MEGALABS" in texto: fabricante = "MEGALABS"
            elif "HETERO" in texto: fabricante = "HETERO"
            elif "VICK" in texto: fabricante = "VICK"
            elif "MEDVAL" in texto: fabricante = "MEDVAL"
            elif "NUVILLE" in texto: fabricante = "NUVILLE"
            elif "ADIUM" in texto: fabricante = "ADIUM"
            elif " ROWE " in texto or "(ROWE)" in texto: fabricante = "ROWE"
            elif "NEOLPHARMA" in texto: fabricante = "NEOLPHARMA"
            elif "POLINAC" in texto: fabricante = "POLINAC"
            elif " ZUKATI " in texto or "(ZUKATI)" in texto: fabricante = "ZUKATI"
            elif " GSK " in texto or "(GSK)" in texto: fabricante = "GSK"
            elif " CHEMO " in texto or "(CHEMO)" in texto: fabricante = "CHEMO"
            elif " GRUNENTHAL " in texto or "(GRUNENTHAL)" in texto: fabricante = "GRUNENTHAL"
            elif " DALT PHARMA " in texto or "(DALT PHARMA)" in texto or "DALTPHARMA" in texto: fabricante = "DALT PHARMA"
            elif " DISKAM " in texto or "(DISKAM)" in texto: fabricante = "DISKAM"
            elif " FARDEL " in texto or "(FARDEL)" in texto: fabricante = "FARDEL"
            elif " ASOFARMA " in texto or "(ASOFARMA)" in texto: fabricante = "ASOFARMA"
            elif " RIMOSS " in texto or "(RIMOSS)" in texto: fabricante = "RIMOSS"
            elif " VITSUPPLY " in texto or "(VITSUPPLY)" in texto: fabricante = "VITSUPPLY"
            
            # New rules for lote 7
            elif "OFTALMI" in texto: fabricante = "OFTALMI"
            elif "BIOTECH" in texto: fabricante = "BIOTECH"
            elif "VALMORCA" in texto: fabricante = "VALMORCA"
            elif "GENCER" in texto: fabricante = "GENCER"
            elif "ELMOR" in texto: fabricante = "ELMOR"
            elif "MEDIGEN" in texto: fabricante = "MEDIGEN"
            elif "ZAKIMED" in texto: fabricante = "ZAKIMED"
            elif "MCK" in texto: fabricante = "MCK"
            elif "BIOSANO" in texto: fabricante = "BIOSANO"
            elif " PONCE " in texto or "(PONCE)" in texto: fabricante = "PONCE"
            elif " KLAS " in texto or "(KLAS)" in texto: fabricante = "KLAS"
            
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
            if cursor.rowcount > 0:
                count_updated += 1
            
        print(f"Lote 7: Actualizados {count_updated} campos de fabricante de {len(codbarras_procesados)} registros leídos.")
        
        # 3. Mark all 400 as processed
        if codbarras_procesados:
            placeholders = ','.join(['?'] * len(codbarras_procesados))
            sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 1 WHERE codbarras IN ({placeholders})"
            cursor.execute(sql, codbarras_procesados)
            print(f"Marcados {len(codbarras_procesados)} registros como procesados (procesado_fase1 = 1).")
            
        porcentaje = round((count_updated / len(codbarras_procesados)) * 100, 2)
        print(f"Porcentaje de exito: {porcentaje}%")
        
    except Exception as e:
        print("Error en actualizacion lote 7:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    update_lote7()
