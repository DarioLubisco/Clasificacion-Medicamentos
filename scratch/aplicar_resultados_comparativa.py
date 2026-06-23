import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import sys
import os

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

# Add parent directory to path to import MDM_Unified_Mapper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MDM_Unified_Mapper import MasterCatalog

def fmt(val, is_string=True):
    if val is None or str(val).strip() == '' or str(val).lower() == 'null': return "NULL"
    val_str = str(val).strip()
    if val_str.lower() == 'true': return "1"
    if val_str.lower() == 'false': return "0"
    if is_string: return f"'{val_str.replace(chr(39), chr(39)+chr(39))}'"
    
    # Para valores numéricos
    try:
        num_clean = val_str.replace(',', '.')
        float(num_clean)
        return num_clean
    except ValueError:
        import re
        nums = re.findall(r'\d+(?:\.\d+)?', val_str)
        if nums: return nums[0]
        return "NULL"

def main():
    json_path = "scratch/resultados_comparativa.json"
    if not os.path.exists(json_path):
        print(f"Error: No existe el archivo {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        comparativa = json.load(f)

    catalog = MasterCatalog(CONN_STR)
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    print(f"Aplicando resultados del modelo Gemini 3.1 Pro en la Base de Datos para {len(comparativa)} registros...")

    for codbarras, data in comparativa.items():
        g31 = data.get("gemini_3_1_pro")
        if not g31:
            print(f"  [Error] No hay datos de gemini_3_1_pro para EAN {codbarras}")
            continue
            
        atrib = g31.get("atrib", {})
        score = g31.get("score", 0)
        
        dominio = atrib.get('dominio', 'SINEVAL')
        categoria = atrib.get('categoria', 'SINEVAL')
        subcategoria = atrib.get('subcategoria', 'SINEVAL')
        es_med = (dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO'])
        confianza = atrib.get('confianza_nivel', 1)

        # Determinar estado ciclo
        if (score >= 85 and confianza >= 4) or (not es_med and score >= 60 and confianza >= 3):
            estado_ciclo = 'CERRADO'
        else:
            estado_ciclo = 'REVISION_MANUAL'

        obs = fmt(str(atrib.get('razonamiento'))[:95]) if atrib.get('razonamiento') else "NULL"
        
        id_pa = catalog.find_id("principio_activo", atrib.get('principio_activo'))
        id_con = catalog.find_id("concentracion", atrib.get('concentracion'))
        id_ff = catalog.find_id("forma_farmaceutica", atrib.get('forma_farmaceutica'))
        id_fab = catalog.find_id("fabricante", atrib.get('fabricante'))
        id_mar = catalog.find_id("marca", atrib.get('marca'))
        id_ori = catalog.find_id("origen", atrib.get('origen'))
        id_atc = catalog.find_id("codigo_atc", atrib.get('codigo_atc'))
        id_cnu = catalog.find_id("contenido_neto_unidad", atrib.get('contenido_neto_unidad_Des'))
        id_cla = catalog.find_id("clasificacion_insumo", atrib.get('clasificacion_insumo_Des'))

        set_clauses = [
            f"principio_activo_Des = {fmt(atrib.get('principio_activo'))}",
            f"concentracion_Des = {fmt(atrib.get('concentracion'))}",
            f"forma_farmaceutica_Des = {fmt(atrib.get('forma_farmaceutica'))}",
            f"fabricante_Des = {fmt(atrib.get('fabricante'))}",
            f"marca_Des = {fmt(atrib.get('marca'))}",
            f"origen_Des = {fmt(atrib.get('origen'))}",
            f"codigo_atc_Des = {fmt(atrib.get('codigo_atc'))}",
            f"requiere_recipe = {fmt(atrib.get('requiere_recipe'), False)}",
            f"generico = {fmt(atrib.get('generico'), False)}",
            f"cantidad_presentacion = {fmt(atrib.get('cantidad_presentacion'), False)}",
            f"contenido_neto = {fmt(atrib.get('contenido_neto'), False)}",
            f"contenido_neto_unidad_Des = {fmt(atrib.get('contenido_neto_unidad_Des'))}",
            f"segmento_etario = {fmt(atrib.get('segmento_etario'))}",
            f"clasificacion_insumo_Des = {fmt(atrib.get('clasificacion_insumo_Des'))}",
            f"es_medicamento = {1 if es_med else 0}",
            f"score_calidad = {score}",
            f"estado_ciclo = '{estado_ciclo}'",
            f"observaciones_ia = {obs}",
            f"origen_dato = 'IA_COMPARATIVA_G3.1_PRO'",
            f"principio_activo = {fmt(id_pa, False)}",
            f"concentracion = {fmt(id_con, False)}",
            f"forma_farmaceutica = {fmt(id_ff, False)}",
            f"fabricante = {fmt(id_fab, False)}",
            f"marca = {fmt(id_mar, False)}",
            f"origen = {fmt(id_ori, False)}",
            f"codigo_atc = {fmt(id_atc, False)}",
            f"contenido_neto_unidad = {fmt(id_cnu, False)}",
            f"clasificacion_insumo = {fmt(id_cla, False)}"
        ]

        sql_update = f"""
        DECLARE @id_taxonomia INT;
        SELECT @id_taxonomia = id_taxonomia FROM Procurement.Taxonomia 
        WHERE dominio = {fmt(dominio)} AND ISNULL(categoria, 'SINEVAL') = {fmt(categoria)} AND ISNULL(subcategoria, 'SINEVAL') = {fmt(subcategoria)};
          
        UPDATE Procurement.por_aprobacion_equivalencias 
        SET {', '.join(set_clauses)}, id_taxonomia = @id_taxonomia, procesado_fase2 = 1
        WHERE codbarras = '{codbarras}';
        """

        try:
            cursor.execute(sql_update)
            # También marcar como procesado_fase3 en raw
            cursor.execute("UPDATE Procurement.scraping_farmacias_raw SET procesado_fase3 = 1 WHERE codbarras = ?", (codbarras,))
            print(f"  -> EAN {codbarras} guardado exitosamente (Estado: {estado_ciclo}).")
        except Exception as e:
            print(f"  -> [Error EAN {codbarras}]: {e}")

    conn.close()
    print("Base de Datos actualizada con éxito.")

if __name__ == "__main__":
    main()
