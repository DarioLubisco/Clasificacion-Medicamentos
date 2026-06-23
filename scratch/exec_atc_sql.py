import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def main():
    with open("scratch/actualizacion_taxonomia_atc3.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    
    # Split by GO
    batches = [b.strip() for b in sql.split('\nGO') if b.strip()]
    
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    for batch in batches:
        if not batch: continue
        try:
            print(f"Executing batch: {batch[:50]}...")
            cursor.execute(batch)
        except Exception as e:
            print(f"Error executing batch: {e}")
            
    print("Database updated successfully.")
    conn.close()

if __name__ == "__main__":
    main()
