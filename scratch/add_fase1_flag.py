import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def add_column():
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()
    
    try:
        # Añadir la columna procesado_fase1
        sql = """
        IF COL_LENGTH('Procurement.por_aprobacion_equivalencias', 'procesado_fase1') IS NULL
        BEGIN
            ALTER TABLE Procurement.por_aprobacion_equivalencias
            ADD procesado_fase1 BIT DEFAULT 0;
            
            -- Actualizar los valores existentes a 0
            EXEC('UPDATE Procurement.por_aprobacion_equivalencias SET procesado_fase1 = 0 WHERE procesado_fase1 IS NULL;');
        END
        """
        cursor.execute(sql)
        print("Columna 'procesado_fase1' añadida con éxito.")
    except Exception as e:
        print("Error al añadir la columna:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
