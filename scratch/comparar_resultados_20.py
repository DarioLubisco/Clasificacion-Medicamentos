import json
import os

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} no existe.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando {filepath}: {e}")
        return None

def main():
    hard_path = "scratch/resultados_20_hard.json"
    vision_path = "scratch/resultados_20_vision.json"
    
    hard_data = load_json(hard_path)
    vision_data = load_json(vision_path)
    
    if not hard_data or not vision_data:
        print("No se pudieron cargar ambos archivos de resultados.")
        return

    # Buscar el modelo usado
    model_key = "deepseek_v4_flash"

    report_lines = []
    report_lines.append("# Reporte de Comparación: Texto vs Visión Activa (OCR)")
    report_lines.append("Este reporte analiza el impacto de introducir imágenes y OCR con Gemini Flash en la clasificación de los 20 productos complejos.")
    report_lines.append("")
    report_lines.append("| EAN | Descripción | Score Sin Visión | Score Con Visión | Confianza Sin Visión | Confianza Con Visión | Fotos Aprobadas | Cambios Clave |")
    report_lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")

    mejoras_score = 0
    total_productos = 0
    total_fotos_aprobadas = 0

    # Iterar sobre los productos que estén en ambos
    for ean in vision_data:
        if ean not in hard_data:
            continue
        
        total_productos += 1
        item_hard = hard_data[ean]
        item_vision = vision_data[ean]
        
        desc = item_vision.get("descripcion", "Sin descripción")
        
        res_hard = item_hard.get(model_key, {})
        res_vision = item_vision.get(model_key, {})
        
        score_hard = res_hard.get("score", 0) if res_hard else 0
        score_vision = res_vision.get("score", 0) if res_vision else 0
        
        atrib_hard = res_hard.get("atrib", {}) if res_hard else {}
        atrib_vision = res_vision.get("atrib", {}) if res_vision else {}
        
        conf_hard = atrib_hard.get("confianza_nivel", "N/A") if atrib_hard else "N/A"
        conf_vision = atrib_vision.get("confianza_nivel", "N/A") if atrib_vision else "N/A"
        
        fotos_guardadas = item_vision.get("fotos_a_guardar", [])
        num_fotos = len(fotos_guardadas)
        total_fotos_aprobadas += num_fotos

        # Detectar cambios clave
        cambios = []
        
        # Verificar atributos que eran NULL o vacíos y ahora tienen valor
        campos_a_verificar = [
            ("principio_activo", "Principio Activo"),
            ("concentracion", "Concentración"),
            ("forma_farmaceutica", "Forma Farmacéutica"),
            ("fabricante", "Laboratorio/Fabricante"),
            ("marca", "Marca"),
            ("registro_sanitario", "Reg. Sanitario")
        ]
        
        for campo, label in campos_a_verificar:
            val_hard = atrib_hard.get(campo) if atrib_hard else None
            val_vision = atrib_vision.get(campo) if atrib_vision else None
            
            # Si antes era nulo/vacío y ahora no
            if (val_hard is None or val_hard == "") and (val_vision is not None and val_vision != ""):
                cambios.append(f"**+{label}** ({val_vision})")
            # Si cambió el valor significativamente
            elif val_hard != val_vision and val_hard and val_vision:
                cambios.append(f"{label}: '{val_hard}' ➔ '{val_vision}'")

        if score_vision > score_hard:
            mejoras_score += 1

        cambios_str = ", ".join(cambios) if cambios else "Ningún cambio en campos críticos"
        report_lines.append(f"| {ean} | {desc[:40]}... | {score_hard} | {score_vision} | {conf_hard} | {conf_vision} | {num_fotos} | {cambios_str} |")

    report_lines.append("")
    report_lines.append("## Resumen de Impacto")
    report_lines.append(f"- **Total productos evaluados**: {total_productos}")
    report_lines.append(f"- **Productos que mejoraron su score de precisión**: {mejoras_score} de {total_productos}")
    report_lines.append(f"- **Total de imágenes procesadas y aprobadas**: {total_fotos_aprobadas}")
    
    report_content = "\n".join(report_lines)
    
    # Guardar reporte en markdown
    report_output_path = "scratch/reporte_comparativo_20.md"
    with open(report_output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Reporte de comparación generado con éxito en: {report_output_path}")

if __name__ == "__main__":
    main()
