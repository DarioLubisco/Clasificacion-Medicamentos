import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    fields_to_check = [
        ("fabricante", "fabricante_Des"),
        ("marca", "marca_Des"),
        ("origen", "origen_Des"),
        ("codigo_atc", "codigo_atc_Des"),
        ("contenido_neto_unidad", "contenido_neto_unidad_Des"),
        ("clasificacion_insumo", "clasificacion_insumo_Des"),
    ]

    print("--- Verificación de IDs Huérfanos ---")
    for id_col, des_col in fields_to_check:
        query = f"""
            SELECT COUNT(*)
            FROM Procurement.por_aprobacion_equivalencias
            WHERE {des_col} IS NOT NULL 
              AND {des_col} != 'NULL'
              AND {des_col} != ''
              AND {id_col} IS NULL
        """
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"[{id_col}] Registros con descripción ({des_col}) pero sin ID: {count}")

    conn.close()

if __name__ == "__main__":
    main()
