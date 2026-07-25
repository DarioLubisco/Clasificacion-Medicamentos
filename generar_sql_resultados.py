import json
import sys

def t(val, length):
    if val is None or val == '': return 'NULL'
    s = str(val).replace("'", "''")
    return f"'{s[:length]}'"

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'scratch/resultados_triple.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'scratch/actualizacion_resultados.sql'
    model_priority = ['deepseek_v4_flash', 'deepseek_v4_pro']

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            resultados = json.load(f)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        sys.exit(1)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('BEGIN TRANSACTION;\n\n')
        
        for ean, item in resultados.items():
            # Find the first available model result
            attr = None
            modelo_usado = None
            for model in model_priority:
                if model in item and item[model] and item[model].get('atrib'):
                    attr = item[model]['atrib']
                    modelo_usado = model
                    break
            
            if not attr:
                print(f"Skipping {ean}, no valid attributes found from any model.")
                continue

            f.write('UPDATE Procurement.por_aprobacion_equivalencias SET ')
            f.write(f"principio_activo_Des = {t(attr.get('principio_activo'), 255)}, ")
            f.write(f"concentracion_Des = {t(attr.get('concentracion'), 255)}, ")
            f.write(f"forma_farmaceutica_Des = {t(attr.get('forma_farmaceutica'), 255)}, ")
            f.write(f"codigo_atc_Des = {t(attr.get('codigo_atc'), 50)}, ")
            f.write(f"codigo_atc_profundo_Des = {t(attr.get('codigo_atc_profundo'), 50)}, ")
            f.write(f"modelo_ia_Des = {t(modelo_usado, 100)}, ")

            gen = attr.get('generico')
            f.write(f"generico_Des = {1 if gen else 0}, ")
            
            f.write(f"segmento_etario_Des = {t(attr.get('segmento_etario'), 100)}, ")
            f.write(f"origen_Des = {t(attr.get('origen'), 100)}, ")
            f.write(f"fabricante_Des = {t(attr.get('fabricante'), 255)}, ")
            f.write(f"marca_Des = {t(attr.get('marca'), 255)}, ")
            f.write(f"contenido_neto_Des = {t(attr.get('contenido_neto'), 100)}, ")
            
            cp = attr.get('cantidad_presentacion')
            f.write(f"cantidad_presentacion_Des = {int(cp) if cp is not None and str(cp).isdigit() else 'NULL'}, ")
            
            f.write("origen_dato = 'IA_INVESTIGATED_V11_ORCHESTRATOR' ")
            
            f.write(f"WHERE codbarras = '{ean}';\n")
            
            fotos_satelite = item.get('fotos_a_guardar', [])
            for fimg in fotos_satelite:
                url_img = fimg.get('url_imagen') if isinstance(fimg, dict) else fimg
                score_img = fimg.get('score', 1) if isinstance(fimg, dict) else 1
                if url_img:
                    f.write(f"INSERT INTO Procurement.Imagenes_Productos_Crudas (codbarras, url_imagen, score_legibilidad) VALUES ('{ean}', {t(url_img, 4000)}, {score_img});\n")
            
        f.write('\nCOMMIT;\n')
        
    print(f'SQL regenerado exitosamente en: {output_file}')

if __name__ == '__main__':
    main()
