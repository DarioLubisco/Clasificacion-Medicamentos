import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def run_schema():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    with open('scratch/schema_scraping_table.sql', 'r') as f:
        sql = f.read()
        
    batches = sql.split('GO')
    for batch in batches:
        if batch.strip():
            print("Executing:", batch[:50], "...")
            cursor.execute(batch)
            
    print("Schema updated successfully.")

if __name__ == "__main__":
    run_schema()
