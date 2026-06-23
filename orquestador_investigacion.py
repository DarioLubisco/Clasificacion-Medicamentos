import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import sys

# Configuración de Conexión a la base de datos Synapse
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=10.200.8.5\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")}'

def obtener_lote_para_investigar(limite=50):
    """Obtiene registros de la tabla equivalencias que requieren investigación web."""
    print(f"Buscando los últimos {limite} registros pendientes...")
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        # Buscamos registros donde el principio activo esté vacío o nulo y no tenga origen_dato marcado por la IA v10
        query = f"""
        SELECT TOP {limite} codigo, codbarras, descrip1art 
        FROM Procurement.por_aprobacion_equivalencias 
        WHERE principio_activo_Des IS NULL AND es_medicamento IS NULL
        AND (origen_dato IS NULL OR origen_dato NOT LIKE 'IA_INVESTIGATED%')
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        lote = []
        for row in rows:
            lote.append({
                "codigo": row[0],
                "codbarras": row[1],
                "descripcion_original": row[2]
            })
        
        conn.close()
        return lote
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return []

def generar_sql_updates(archivo_json_resultados):
    """Convierte el JSON de la IA en comandos SQL seguros y los guarda en un archivo."""
    print(f"\nGenerando sentencias SQL leyendo de {archivo_json_resultados}...")
    
    try:
        with open(archivo_json_resultados, 'r', encoding='utf-8') as f:
            resultados_ia = json.load(f)
            
        sql_statements = []
        
        for item in resultados_ia:
            codigo = item.get('registro', {}).get('codigo')
            if not codigo:
                continue
                
            atrib = item.get('atributos', {})
            
            # Helper para formatear valores SQL
            def fmt(val, is_string=True):
                if val is None or val == 'None' or str(val).strip() == '':
                    return "NULL"
                if is_string:
                    v_str = str(val).replace("'", "''")
                    return f"'{v_str}'"
                return str(val)

            set_clauses = [
                f"principio_activo_Des = {fmt(atrib.get('principio_activo'))}",
                f"concentracion_Des = {fmt(atrib.get('concentracion'))}",
                f"forma_farmaceutica_Des = {fmt(atrib.get('forma_farmaceutica'))}",
                f"fabricante_Des = {fmt(atrib.get('fabricante'))}",
                f"marca_Des = {fmt(atrib.get('marca'))}",
                f"codigo_atc_Des = {fmt(atrib.get('codigo_atc'))}",
                f"url_imagen = {fmt(atrib.get('url_imagen'))}",
                f"requiere_recipe = {fmt(atrib.get('requiere_recipe'), False)}",
                f"segmento_etario = {fmt(atrib.get('segmento_etario'))}",
                f"origen_Des = {fmt(atrib.get('origen'))}",
                "origen_dato = 'IA_INVESTIGATED_V10'"
            ]
            
            update_query = f"UPDATE Procurement.por_aprobacion_equivalencias SET {', '.join(set_clauses)} WHERE codigo = '{codigo}';"
            sql_statements.append(update_query)
        
        output_file = 'actualizacion_investigacion.sql'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('-- Script generado automaticamente por Orquestador IA\n')
            f.write('\n'.join(sql_statements))
        
        print(f"Se han generado {len(sql_statements)} actualizaciones en '{output_file}'.")
        print("Puedes revisar el archivo y luego ejecutarlo en SQL Server Management Studio.")
        
    except FileNotFoundError:
        print(f"Error: No se encontro el archivo {archivo_json_resultados}")
    except json.JSONDecodeError:
        print(f"Error: El archivo {archivo_json_resultados} no tiene un formato JSON valido.")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        # Modo generacion de SQL: Si le pasas un archivo JSON como argumento
        generar_sql_updates(sys.argv[1])
    else:
        # Modo extraccion: Si lo ejecutas sin argumentos (o pasas un número)
        limite = 100
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            limite = int(sys.argv[1])
            
        batch = obtener_lote_para_investigar(limite)
        
        if batch:
            print("\n--- COPIA Y PEGA EL SIGUIENTE BLOQUE EN EL CHAT DE LA IA ---")
            print(json.dumps(batch, indent=4))
            print("------------------------------------------------------------")
            print("\nInstruccion para el script: Una vez que la IA te responda con el JSON estructurado,")
            print("guardalo en un archivo (ej: 'resultados.json') y ejecuta este script asi:")
            print("python orquestador_investigacion.py resultados.json")
        else:
            print("No hay registros pendientes de investigación.")
