import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def main():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1 ORDER BY dominio, categoria, subcategoria")
        rows = cursor.fetchall()
        
        tax_dict = {}
        for r in rows:
            d, c, s = r[0], r[1], r[2]
            if d not in tax_dict:
                tax_dict[d] = {}
            if c not in tax_dict[d]:
                tax_dict[d][c] = []
            if s not in tax_dict[d][c]:
                tax_dict[d][c].append(s)
                
        print(json.dumps(tax_dict, indent=2))
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
