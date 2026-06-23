import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import re
import collections

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

STOP_WORDS = {
    'TAB', 'CAP', 'COMP', 'REC', 'MG', 'ML', 'GR', 'SUSP', 'JBE', 'AMP', 'CREMA', 'GEL', 'UNG', 'OFT', 'VAG', 'ORAL',
    'TABLETAS', 'MCG', 'CAPSULAS', 'COMPRIMIDOS', 'UNGUENTO', 'SOL', 'SOLUCION', 'GOTAS', 'JARABE', 'INYECTABLE',
    'FRASCO', 'CAJA', 'BLISTER', 'SOBRES', 'POLVO', 'GRANULADO', 'AEROSOL', 'SPRAY', 'PEDIATRICO', 'ADULTO',
    'FORTE', 'PLUS', 'RETARD', 'XR', 'LP', 'AP', 'UI', 'IU', 'U.I', 'G', 'KG', 'L', 'M', 'CM', 'MM', 'DOSIS', 'INHALADOR'
}

# Keep the static dictionary as a base
BASE_DICT = {
    "SPEFAR", "PSICOFARMA", "H & M", "H&M", "S&G", "KMPLUS", "GLOBAL MEDIC", "MALLEN", "ALPHARMA", "NOW", 
    "ALFA", "PISA", "SAN LORENZO", "ARTE MEDICO", "EXELTIS", "FAHD", "LATTAN MEDIC", "GAMA", "MEGALABS", 
    "HETERO", "VICK", "MEDVAL", "NUVILLE", "ADIUM", "ROWE", "NEOLPHARMA", "POLINAC", "ZUKATI", "GSK", 
    "CHEMO", "GRUNENTHAL", "DALT PHARMA", "DISKAM", "FARDEL", "ASOFARMA", "RIMOSS", "VITSUPPLY",
    "OFTALMI", "BIOTECH", "VALMORCA", "GENCER", "ELMOR", "MEDIGEN", "ZAKIMED", "MCK", "BIOSANO", "PONCE", "KLAS"
}

def clean_word(w):
    w = w.strip().replace(")", "").replace("(", "").strip()
    return w

def run_dynamic_lote():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    # Fetch 4000 records
    cursor.execute("""
        SELECT TOP 4000 codbarras, descripcion_mercado_concat, marca_Des, fabricante_Des
        FROM Procurement.por_aprobacion_equivalencias
        WHERE es_medicamento = 1 
          AND descripcion_mercado_concat IS NOT NULL 
          AND procesado_fase1 = 0
          AND (marca_Des IS NULL OR fabricante_Des IS NULL)
    """)
    rows = cursor.fetchall()
    if not rows:
        print("No hay suficientes registros.")
        return

    # First pass: identify dynamic manufacturers
    candidates = collections.Counter()
    codbarras_list = []
    textos_dict = {}
    
    for r in rows:
        cb = r[0]
        texto = (r[1] or "").upper()
        codbarras_list.append(cb)
        textos_dict[cb] = texto
        
        descs = texto.split(' | ')
        for desc in descs:
            desc = desc.strip()
            
            # Parens
            parens = re.findall(r'\(([A-Z&\s\.\-]+)\)', desc)
            for p in parens:
                p_clean = clean_word(p)
                if len(p_clean) > 2 and p_clean not in STOP_WORDS:
                    candidates[p_clean] += 1
                    
            # Last word
            match = re.search(r'\b([A-Z&]+)\s*\)?$', desc)
            if match:
                w_clean = clean_word(match.group(1))
                if len(w_clean) > 2 and w_clean not in STOP_WORDS:
                    candidates[w_clean] += 1

    # Valid dynamic manufacturers: appeared at least 2 times
    dynamic_manufacturers = set([k for k, v in candidates.items() if v >= 2])
    all_manufacturers = BASE_DICT.union(dynamic_manufacturers)
    
    print(f"Diccionario creció dinámicamente a {len(all_manufacturers)} laboratorios.")

    # Second pass: Apply
    updates = []
    for cb in codbarras_list:
        texto = textos_dict[cb]
        fabricante = None
        
        # Check from all_manufacturers
        for lab in all_manufacturers:
            # We want exact word match or parenthesis match to avoid partials
            if f" {lab} " in f" {texto} " or f"({lab})" in texto or texto.endswith(lab):
                fabricante = lab
                break
                
        if fabricante:
            updates.append((fabricante, cb))

    # Apply updates
    count_updated = 0
    try:
        # Update in batches of 500 to avoid locking
        for i in range(0, len(updates), 500):
            batch = updates[i:i+500]
            cursor.executemany("UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = ? WHERE codbarras = ? AND fabricante_Des IS NULL", batch)
            count_updated += len(batch)
            
        print(f"Lote 4000: Actualizados {count_updated} campos de fabricante de {len(codbarras_list)} registros leídos.")
        
        # Mark as processed
        for i in range(0, len(codbarras_list), 500):
            batch_cb = codbarras_list[i:i+500]
            placeholders = ','.join(['?'] * len(batch_cb))
            sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 1 WHERE codbarras IN ({placeholders})"
            cursor.execute(sql, batch_cb)
            
        porcentaje = round((count_updated / len(codbarras_list)) * 100, 2)
        print(f"Porcentaje de exito: {porcentaje}%")
        
    except Exception as e:
        print("Error en actualizacion lote 4000:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    run_dynamic_lote()
