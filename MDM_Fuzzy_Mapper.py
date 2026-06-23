import os
import json
import pyodbc
from rapidfuzz import process, fuzz
import unicodedata
from dotenv import load_dotenv

# Configuración y Constantes
load_dotenv()
UMBRAL_CONFIANZA = 90.0

def normalize_text(text):
    if not text:
        return ""
    # Remove accents and convert to uppercase
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8').upper()
    # Estandarizar separadores comunes en farmacia
    text = text.replace('+', '-').replace('/', '-')
    # Quitar espacios múltiples
    return " ".join(text.split())

def get_db_connection():
    # Intentar leer desde .env usando los nombres estándar del proyecto
    server = os.environ.get('DB_SERVER', '10.200.8.5\\efficacis3')
    database = os.environ.get('DB_DATABASE', 'EnterpriseAdmin_AMC')
    user = os.environ.get('DB_USERNAME', 'sa')
    password = os.getenv('DB_PASSWORD')
    driver = os.environ.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    conn_str = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={user};PWD={password}'
    
    return pyodbc.connect(conn_str)

def main():
    print("=== Iniciando Conciliador MDM Inteligente ===")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        return

    # 1. Cargar el Catálogo Maestro de Principios Activos
    print("[1/4] Cargando Catálogo Maestro...")
    cursor.execute("SELECT codigo, descripcion FROM Procurement.principio_activo")
    maestro_records = cursor.fetchall()
    
    # Crear diccionario de búsqueda normalizado
    catalogo_maestro = {}
    nombres_normalizados = []
    
    for row in maestro_records:
        codigo_id = row[0]
        nombre_original = row[1]
        nombre_norm = normalize_text(nombre_original)
        
        # Mapeo de normalizado a tupla (ID, Nombre Original)
        catalogo_maestro[nombre_norm] = (codigo_id, nombre_original)
        nombres_normalizados.append(nombre_norm)

    # 2. Extraer Registros Huérfanos
    print("[2/4] Extrayendo descriptores huérfanos de la tabla de staging...")
    query_staging = """
        SELECT codigo, principio_activo_Des, codbarras 
        FROM Procurement.por_aprobacion_equivalencias 
        WHERE es_medicamento = 1 
          AND principio_activo IS NULL 
          AND principio_activo_Des IS NOT NULL
    """
    cursor.execute(query_staging)
    huerfanos = cursor.fetchall()
    
    print(f"-> Se encontraron {len(huerfanos)} registros para conciliar.")

    updates_sql = []
    faltantes_reales = []
    
    # 3. Fuzzy Matching (Conciliación)
    print("[3/4] Procesando Inteligencia de Conciliación (Fuzzy Mapping)...")
    for row in huerfanos:
        codigo_staging = row[0]
        desc_original = row[1]
        codbarras = row[2]
        
        # PASO A: Normalización
        desc_norm = normalize_text(desc_original)
        
        # PASO B: Búsqueda Fuzzy
        # extractOne devuelve (mejor_coincidencia, score, indice)
        match = process.extractOne(desc_norm, nombres_normalizados, scorer=fuzz.WRatio)
        
        if match:
            mejor_texto_norm, score, _ = match
            if score >= UMBRAL_CONFIANZA:
                # Match Exitoso
                id_maestro, nombre_oficial = catalogo_maestro[mejor_texto_norm]
                sql = f"UPDATE Procurement.por_aprobacion_equivalencias SET principio_activo = '{id_maestro}' WHERE codigo = '{codigo_staging}';"
                updates_sql.append(sql)
            else:
                # Faltante Real (Bajo Score)
                faltantes_reales.append({
                    "codigo": codigo_staging,
                    "codbarras": codbarras,
                    "descriptor_original": desc_original,
                    "mejor_coincidencia_sugerida": catalogo_maestro[mejor_texto_norm][1] if score > 70 else "Ninguna",
                    "score": round(score, 2)
                })
        else:
            faltantes_reales.append({
                "codigo": codigo_staging,
                "codbarras": codbarras,
                "descriptor_original": desc_original,
                "mejor_coincidencia_sugerida": "N/A",
                "score": 0.0
            })

    # 4. Generación de Artefactos (SQL y JSON)
    print("[4/4] Generando artefactos de salida...")
    
    # Guardar SQL de Updates exitosos
    with open('MDM_Phase4_Fuzzy_Mapping.sql', 'w', encoding='utf-8') as f:
        f.write("-- Script Generado Automáticamente por MDM_Fuzzy_Mapper\n")
        f.write("BEGIN TRANSACTION;\n\n")
        for sql in updates_sql:
            f.write(sql + "\n")
        f.write("\n-- Revise los cambios antes de descomentar el COMMIT\n")
        f.write("-- COMMIT;\n")
    
    # Guardar Faltantes para revisión (Hermes / Intervención Humana)
    with open('Faltantes_Reales.json', 'w', encoding='utf-8') as f:
        json.dump(faltantes_reales, f, indent=4, ensure_ascii=False)

    print(f"=== Proceso Completado ===")
    print(f"-> Mapeos Exitosos (SQL Generado): {len(updates_sql)}")
    print(f"-> Faltantes Reales / Dudosos (JSON Generado): {len(faltantes_reales)}")

if __name__ == "__main__":
    main()
