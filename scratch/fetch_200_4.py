import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def fetch_lote4():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 200 codbarras, descripcion_mercado_concat,
               marca_Des, fabricante_Des
        FROM Procurement.por_aprobacion_equivalencias
        WHERE es_medicamento = 1 
          AND descripcion_mercado_concat IS NOT NULL 
          AND procesado_fase1 = 0
          AND (marca_Des IS NULL OR fabricante_Des IS NULL)
    """)
    rows = cursor.fetchall()
    res = []
    for r in rows:
        res.append(f"{r[0]}|{r[1]}|M:{r[2]}|F:{r[3]}")
    with open("scratch/compact_200_4.txt", "w") as f:
        for line in res:
            f.write(line + "\n")
    conn.close()
    print(f"Saved {len(res)} to scratch/compact_200_4.txt")

if __name__ == "__main__":
    fetch_lote4()
