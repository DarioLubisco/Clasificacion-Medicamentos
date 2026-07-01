import pyodbc
import json
import os
import glob
from mega_orquestador_autonomo_v2 import llamar_openrouter, obtener_taxonomias_existentes, generar_sql_updates, ejecutar_sql, CONN_STR
from MDM_Unified_Mapper import MasterCatalog

def limpiar_logs():
    print("Depurando logs antiguos...")
    archivos_json = glob.glob("debug_resultados_*.json")
    for f in archivos_json:
        os.remove(f)
        print(f" - Eliminado: {f}")
    
    archivos_sql = glob.glob("actualizacion_investigacion_*.sql")
    for f in archivos_sql:
        os.remove(f)
        print(f" - Eliminado: {f}")

def run_test():
    limpiar_logs()
    
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    
    # Extraer los 2 productos liquidos con multiples ingredientes
    barcodes = ['2260000046134', '0793969044405'] # SINUTIL y Acido Folico
    in_clause = ",".join([f"'{b}'" for b in barcodes])
    
    query = f"""
    SELECT codbarras, descrip1art, ISNULL(ciclos_reproceso, 0) as ciclos_reproceso,
        principio_activo_Des, concentracion_Des, forma_farmaceutica_Des, fabricante_Des, marca_Des,
        codigo_atc_Des, clasificacion_insumo_Des, requiere_recipe, blister, generico, 
        cantidad_presentacion, contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
    FROM Procurement.por_aprobacion_equivalencias 
    WHERE codbarras IN ({in_clause})
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    lote = []
    for r in rows:
        ya_encontrados = {}
        keys = ['principio_activo', 'concentracion', 'forma_farmaceutica', 'fabricante', 'marca',
                'codigo_atc', 'clasificacion_insumo_Des', 'requiere_recipe', 'blister', 'generico',
                'cantidad_presentacion', 'contenido_neto', 'contenido_neto_unidad_Des', 'segmento_etario', 'origen']
        
        for idx, k in enumerate(keys):
            val = r[3+idx]
            if val is not None and str(val).strip() != '':
                ya_encontrados[k] = val
                
        lote.append({
            "registro": {"codbarras": r[0], "descripcion_original": r[1], "ciclos_reproceso": r[2]},
            "atributos_ya_encontrados": ya_encontrados
        })
    conn.close()

    print(f"Lote preparado con {len(lote)} productos.")
    taxonomias_str = obtener_taxonomias_existentes()
    
    import sys
    modelo = sys.argv[1] if len(sys.argv) > 1 else "deepseek/deepseek-v4-flash"
    print(f"Enviando a la IA ({modelo} - Fase 1)...")
    resultados = llamar_openrouter(json.dumps(lote, indent=2), taxonomias_str, model=modelo)
    
    if resultados:
        debug_file = 'debug_resultados_liquidos.json'
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2)
        print(f"\nResultados guardados en {debug_file}")
        
        print("\nGenerando SQL...")
        catalog = MasterCatalog(CONN_STR)
        sql_stmts = generar_sql_updates(resultados, catalog)
        
        sql_file = 'actualizacion_investigacion_liquidos.sql'
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write('\nGO\n'.join(sql_stmts))
            
        print(f"SQL generado y guardado en {sql_file}")
        
        # Ejecutar SQL (Opcional, pero util para ver el resultado completo)
        ejecutar_sql(sql_stmts)
    else:
        print("La IA no devolvió resultados.")

if __name__ == "__main__":
    run_test()
