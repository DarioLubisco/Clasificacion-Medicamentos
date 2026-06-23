import json

with open('investigacion_limpieza_v10.json', 'r', encoding='utf-8') as f:
    resultados = json.load(f)

with open('actualizacion_limpieza_v10.sql', 'w', encoding='utf-8') as f:
    f.write('BEGIN TRANSACTION;\n\n')
    for res in resultados:
        cod = res['registro']['codigo']
        codbarras = res['registro']['codbarras']
        attr = res['atributos']
        
        # If attr is a list or invalid, just skip or use empty dict
        if not isinstance(attr, dict):
            print(f"Skipping invalid attr for {codbarras}: {attr}")
            continue
            
        def t(val, length):
            if val is None or val == '': return 'NULL'
            s = str(val).replace("'", "''")
            return f"'{s[:length]}'"
            
        f.write('UPDATE Procurement.por_aprobacion_equivalencias SET ')
        f.write(f"principio_activo_Des = {t(attr.get('principio_activo'), 255)}, ")
        f.write(f"concentracion_Des = {t(attr.get('concentracion'), 255)}, ")
        f.write(f"forma_farmaceutica_Des = {t(attr.get('forma_farmaceutica'), 255)}, ")
        f.write(f"codigo_atc_Des = {t(attr.get('codigo_atc'), 50)}, ")
        
        rec = attr.get('requiere_recipe')
        f.write(f"requiere_recipe_Des = {1 if rec else 0}, ")
        
        gen = attr.get('generico')
        f.write(f"generico_Des = {1 if gen else 0}, ")
        
        f.write(f"segmento_etario_Des = {t(attr.get('segmento_etario'), 100)}, ")
        f.write(f"origen_Des = {t(attr.get('origen'), 100)}, ")
        f.write(f"fabricante_Des = {t(attr.get('fabricante'), 255)}, ")
        f.write(f"marca_Des = {t(attr.get('marca'), 255)}, ")
        f.write(f"contenido_neto_Des = {t(attr.get('contenido_neto'), 100)}, ")
        
        bl = attr.get('blister')
        f.write(f"blister_Des = {1 if bl else 0}, ")
        
        cp = attr.get('cantidad_presentacion')
        f.write(f"cantidad_presentacion_Des = {int(cp) if cp is not None and str(cp).isdigit() else 'NULL'}, ")
        
        f.write(f"url_imagen = {t(attr.get('url_imagen'), 500)}, ")
        f.write("origen_dato = 'IA_INVESTIGATED_V10_CLEANSE' ")
        
        if cod != 'NULL':
            f.write(f"WHERE codigo = '{cod}';\n")
        else:
            f.write(f"WHERE codbarras = '{codbarras}' AND codigo IS NULL;\n")
            
    f.write('\nCOMMIT;\n')
print('SQL regenerado!')
