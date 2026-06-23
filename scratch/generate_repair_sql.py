import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import sys
import os

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

# Import MasterCatalog
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MDM_Unified_Mapper import MasterCatalog

def main():
    catalog = MasterCatalog(CONN_STR)
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    query = """
    SELECT 
        codbarras,
        fabricante_Des, fabricante,
        marca_Des, marca,
        origen_Des, origen,
        codigo_atc_Des, codigo_atc,
        contenido_neto_unidad_Des, contenido_neto_unidad,
        clasificacion_insumo_Des, clasificacion_insumo
    FROM Procurement.por_aprobacion_equivalencias
    WHERE 
        (fabricante_Des IS NOT NULL AND fabricante_Des != '' AND fabricante_Des != 'NULL' AND fabricante IS NULL) OR
        (marca_Des IS NOT NULL AND marca_Des != '' AND marca_Des != 'NULL' AND marca IS NULL) OR
        (origen_Des IS NOT NULL AND origen_Des != '' AND origen_Des != 'NULL' AND origen IS NULL) OR
        (codigo_atc_Des IS NOT NULL AND codigo_atc_Des != '' AND codigo_atc_Des != 'NULL' AND codigo_atc IS NULL) OR
        (contenido_neto_unidad_Des IS NOT NULL AND contenido_neto_unidad_Des != '' AND contenido_neto_unidad_Des != 'NULL' AND contenido_neto_unidad IS NULL) OR
        (clasificacion_insumo_Des IS NOT NULL AND clasificacion_insumo_Des != '' AND clasificacion_insumo_Des != 'NULL' AND clasificacion_insumo IS NULL)
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()

    updates = []
    
    # Track statistics
    stats = {
        "fabricante": {"total": 0, "found": 0},
        "marca": {"total": 0, "found": 0},
        "origen": {"total": 0, "found": 0},
        "codigo_atc": {"total": 0, "found": 0},
        "contenido_neto_unidad": {"total": 0, "found": 0},
        "clasificacion_insumo": {"total": 0, "found": 0}
    }

    print(f"Buscando IDs para {len(rows)} registros huérfanos...")

    for r in rows:
        codbarras = r.codbarras
        
        # We collect all IDs we can find for this codbarras
        set_clauses = []
        
        def process_field(name, val_des, current_id):
            if val_des and val_des.strip() and val_des != 'NULL' and current_id is None:
                stats[name]["total"] += 1
                found_id = catalog.find_id(name, val_des)
                if found_id is not None:
                    set_clauses.append(f"{name} = {found_id}")
                    stats[name]["found"] += 1
        
        process_field("fabricante", r.fabricante_Des, r.fabricante)
        process_field("marca", r.marca_Des, r.marca)
        process_field("origen", r.origen_Des, r.origen)
        process_field("codigo_atc", r.codigo_atc_Des, r.codigo_atc)
        process_field("contenido_neto_unidad", r.contenido_neto_unidad_Des, r.contenido_neto_unidad)
        process_field("clasificacion_insumo", r.clasificacion_insumo_Des, r.clasificacion_insumo)

        if set_clauses:
            set_clauses.append("LastUpdated = GETDATE()")
            clause_str = ", ".join(set_clauses)
            safe_codbarras = str(codbarras).replace("'", "''")
            updates.append(f"UPDATE Procurement.por_aprobacion_equivalencias SET {clause_str} WHERE codbarras = '{safe_codbarras}';")

    conn.close()

    out_file = "scratch/repair_ids.sql"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("-- SQL Safety Protocol - Dry-Run\n")
        f.write("BEGIN TRANSACTION;\n\n")
        for u in updates:
            f.write(u + "\n")
        f.write("\n-- Para aplicar los cambios de forma definitiva, reemplace ROLLBACK por COMMIT\n")
        f.write("ROLLBACK TRANSACTION;\n")
            
    print(f"\nArchivo generado: {out_file} con {len(updates)} sentencias UPDATE.")
    print("Estadísticas de resolución (Encontrados / Totales huérfanos):")
    for k, v in stats.items():
        print(f"  - {k}: {v['found']} / {v['total']} ({v['found']/v['total']*100 if v['total'] > 0 else 0:.1f}%)")

if __name__ == "__main__":
    main()
