import json
import csv

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    tiene_cont = atrib.get('contenido_neto') is not None
    
    if dominio == 'MEDICAMENTO_ALOPATICO':
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
    elif dominio in ['PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']:
        if not atrib.get('principio_activo') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
            
    if atrib.get('principio_activo'): score += 15
    if atrib.get('concentracion'): score += 15
    if atrib.get('forma_farmaceutica'): score += 15
    if tiene_cant: score += 10
    if tiene_cont: score += 5
    if atrib.get('origen'): score += 10
    if atrib.get('segmento_etario'): score += 10
    if atrib.get('fabricante'): score += 5
    if atrib.get('marca'): score += 5
    if atrib.get('codigo_atc'): score += 5
    if atrib.get('generico') in [1, 0, True, False]: score += 5
    
    return min(100, score)

with open('benchmark_zero_tolerance_25.json') as f:
    bench = json.load(f)

with open('subagent_25.json') as f:
    subagent = json.load(f)

modelos_data = {
    'Qwen-2.5-72B': bench['resultados'].get('qwen/qwen-2.5-72b-instruct'),
    'Gemini-3.1-Flash-High': subagent
}

# The other models failed with None, let's include their names but empty
modelos_data['Gemini-2.5-Pro'] = None
modelos_data['Mixtral-8x22B'] = None
modelos_data['MiniMax-M3'] = None

lote_original = bench['lote_original']

with open('comparativa_modelos.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    header = ['Codigo', 'Descripcion Original', 'Modelo', 'Score Total', 'Estado JSON', 'Dominio', 'Principio Activo', 'Concentracion', 'Forma Farmaceutica', 'Cantidad', 'Contenido Neto', 'Und Neto', 'Marca', 'Fabricante', 'Edad', 'Origen', 'ATC', 'Generico', 'Blister', 'Razonamiento']
    writer.writerow(header)
    
    for i, item in enumerate(lote_original):
        codigo = item['registro']['codigo']
        desc = item['registro']['descripcion_original']
        
        for modelo_nombre, datos_modelo in modelos_data.items():
            if not datos_modelo:
                writer.writerow([codigo, desc, modelo_nombre, 0, 'FALLO SINTAXIS JSON', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'El modelo truncó el JSON o devolvió un formato inválido y falló.'])
                continue
            
            # Find the corresponding item in the model's data
            # Assuming they are in the same order
            res = datos_modelo[i]['atributos_nuevos_consolidados']
            score = calcular_score_calidad(res)
            
            row = [
                codigo,
                desc,
                modelo_nombre,
                score,
                'EXITO',
                res.get('dominio'),
                res.get('principio_activo'),
                res.get('concentracion'),
                res.get('forma_farmaceutica'),
                res.get('cantidad_presentacion'),
                res.get('contenido_neto'),
                res.get('contenido_neto_unidad_Des'),
                res.get('marca'),
                res.get('fabricante'),
                res.get('segmento_etario'),
                res.get('origen'),
                res.get('codigo_atc'),
                res.get('generico'),
                res.get('blister'),
                res.get('razonamiento')
            ]
            writer.writerow(row)

print("Archivo comparativa_modelos.csv generado con exito.")
