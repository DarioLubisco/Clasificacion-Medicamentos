import json

def cargar_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando {path}: {e}")
        return None

def main():
    lote_30 = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/lote_30.json')
    gemini_low = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/gemini_3_1_low_30_complex.json')
    gemini_high = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/subagent_30_complex.json')
    ds_v4_pro = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/deepseek_v4_pro_30_complex.json')
    ds_chat = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/deepseek_30_complex.json')
    
    # Mixtral y Qwen están en benchmark_definitivo_30.json
    bench_def = cargar_json('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/benchmark_definitivo_30.json')
    
    resultados_otros = {}
    if bench_def and 'resultados' in bench_def:
        resultados_otros = bench_def['resultados']
        
    qwen = resultados_otros.get('qwen/qwen-2.5-72b-instruct')
    mixtral = resultados_otros.get('mistralai/mixtral-8x22b-instruct')
    
    modelos = {
        "Gemini 3.1 Low": gemini_low,
        "Gemini 3.1 High": gemini_high,
        "DeepSeek V4 Pro": ds_v4_pro,
        "DeepSeek Chat": ds_chat,
        "Qwen 2.5 72B": qwen,
        "Mixtral 8x22B": mixtral
    }
    
    # Filtrar solo los que no son None y tienen la misma longitud
    modelos = {k: v for k, v in modelos.items() if v is not None and len(v) == 30}
    
    discrepancias = []
    
    atributos_clave = [
        "dominio", "principio_activo", "concentracion", "forma_farmaceutica",
        "cantidad_presentacion", "contenido_neto", "contenido_neto_unidad_Des",
        "fabricante", "marca", "codigo_atc", "blister", "generico", "segmento_etario"
    ]
    
    for idx in range(30):
        orig = lote_30[idx]['registro']
        desc = orig['descripcion_original']
        cod = orig['codbarras']
        
        # Obtener lo que extrajo Gemini 3.1 Low
        low_item = gemini_low[idx].get('atributos_nuevos_consolidados', {})
        
        for attr in atributos_clave:
            val_low = low_item.get(attr)
            
            # Comparar con otros modelos
            for mod_name, mod_data in modelos.items():
                if mod_name == "Gemini 3.1 Low":
                    continue
                
                other_item = mod_data[idx].get('atributos_nuevos_consolidados', {})
                val_other = other_item.get(attr)
                
                # Normalizar a string minúsculas para comparaciones de texto
                str_low = str(val_low).strip().lower() if val_low is not None else "null"
                str_other = str(val_other).strip().lower() if val_other is not None else "null"
                
                # Detectar discrepancia
                if str_low != str_other:
                    discrepancias.append({
                        "index": idx + 1,
                        "codbarras": cod,
                        "descripcion": desc,
                        "atributo": attr,
                        "valor_low": val_low,
                        "valor_other": val_other,
                        "modelo_other": mod_name
                    })
                    
    # Agrupar discrepancias por producto y atributo
    grouped = {}
    for disc in discrepancias:
        key = (disc["index"], disc["descripcion"], disc["atributo"])
        if key not in grouped:
            grouped[key] = {
                "valor_low": disc["valor_low"],
                "comparaciones": {}
            }
        grouped[key]["comparaciones"][disc["modelo_other"]] = disc["valor_other"]
        
    print(f"Total de discrepancias encontradas: {len(discrepancias)}")
    
    # Escribir reporte detallado
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/analisis_completo.txt', 'w', encoding='utf-8') as f:
        f.write("=== ANÁLISIS DETALLADO DE DISCREPANCIAS CON GEMINI 3.1 LOW ===\n\n")
        
        # 1. Resumen de discrepancias por atributo
        attr_counts = {}
        for disc in discrepancias:
            attr_counts[disc["atributo"]] = attr_counts.get(disc["atributo"], 0) + 1
        
        f.write("Discrepancias por Atributo (Frecuencia):\n")
        for attr, count in sorted(attr_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- {attr}: {count} veces\n")
        f.write("\n" + "="*50 + "\n\n")
        
        # 2. Desglose por producto
        for key, data in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][2])):
            idx, desc, attr = key
            f.write(f"Producto #{idx}: {desc}\n")
            f.write(f"Atributo: {attr}\n")
            f.write(f"  -> Gemini 3.1 Low: {data['valor_low']}\n")
            for mod, val in data["comparaciones"].items():
                f.write(f"  -> {mod}: {val}\n")
            f.write("-" * 40 + "\n")
            
    print("Reporte generado en: /home/synapse/source/repos/Clasificacion Medicamentos/scratch/analisis_completo.txt")

if __name__ == '__main__':
    main()
