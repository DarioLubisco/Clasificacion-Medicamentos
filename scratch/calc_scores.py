import json

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO')
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    tiene_cont = atrib.get('contenido_neto') is not None
    
    # 1. Filtro Sine qua non
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
            
    # 2. Asignación de puntos
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

with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/subagent_25.json') as f:
    data = json.load(f)

print("| Producto | Dominio | Score Final | PA | Conc | FF | Cant | ContN | Marca | Fab | Edad | Generico |")
print("|----------|---------|-------------|----|------|----|------|-------|-------|-----|------|----------|")

best_score = -1
best_product = ""

for item in data:
    desc = item['registro']['descripcion_original']
    if len(desc) > 35:
        desc = desc[:32] + "..."
    atrib = item['atributos_nuevos_consolidados']
    score = calcular_score_calidad(atrib)
    
    if score > best_score:
        best_score = score
        best_product = item['registro']['descripcion_original']
    
    dom = atrib.get('dominio', '')[:12]
    pa = "✓" if atrib.get('principio_activo') else "x"
    conc = "✓" if atrib.get('concentracion') else "x"
    ff = "✓" if atrib.get('forma_farmaceutica') else "x"
    cant = "✓" if atrib.get('cantidad_presentacion') is not None else "x"
    cont = "✓" if atrib.get('contenido_neto') is not None else "x"
    mar = "✓" if atrib.get('marca') else "x"
    fab = "✓" if atrib.get('fabricante') else "x"
    edad = "✓" if atrib.get('segmento_etario') else "x"
    gen = "✓" if atrib.get('generico') in [1, True] else "x"
    
    print(f"| {desc} | {dom} | **{score}** | {pa} | {conc} | {ff} | {cant} | {cont} | {mar} | {fab} | {edad} | {gen} |")
    
print(f"\nMejor producto: {best_product} (Score: {best_score})")
