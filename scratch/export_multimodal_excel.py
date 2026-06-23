import json
import pandas as pd
import os

def main():
    json_path = "scratch/resultados_comparativa_multimodal.json"
    excel_path = "scratch/comparativa_modelos_multimodal.xlsx"
    
    if not os.path.exists(json_path):
        print(f"Error: No se encuentra {json_path}")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    rows = []
    
    model_mapping = {
        "gemini_2_5_flash": "Gemini 2.5 Flash",
        "gemini_2_5_pro": "Gemini 2.5 Pro",
        "gemini_3_1_pro": "Gemini 3.1 Pro"
    }
    
    for ean, item in data.items():
        desc = item["descripcion"]
        
        for model_key, model_name in model_mapping.items():
            model_res = item.get(model_key)
            if not model_res or model_res.get("atrib") is None:
                # Caso de error or rechazo
                rows.append({
                    "EAN": ean,
                    "Descripción": desc,
                    "Modelo": model_name,
                    "Score": 0,
                    "Confianza Nivel": "Rechazado/Error",
                    "Confianza Razonamiento": "El modelo se rehusó a clasificar o falló en responder",
                    "Dominio": None,
                    "Principio Activo": None,
                    "Concentración": None,
                    "Forma Farmacéutica": None,
                    "Cantidad Presentación": None,
                    "Contenido Neto": None,
                    "Unidad Neto": None,
                    "Marca": None,
                    "Fabricante": None,
                    "ATC": None,
                    "Genérico": None,
                    "Costo USD": model_res.get("costo", 0.0) if model_res else 0.0,
                    "Razonamiento": None
                })
                continue
                
            at = model_res["atrib"]
            rows.append({
                "EAN": ean,
                "Descripción": desc,
                "Modelo": model_name,
                "Score": model_res.get("score", 0),
                "Confianza Nivel": at.get("confianza_nivel"),
                "Confianza Razonamiento": at.get("confianza_razonamiento"),
                "Dominio": at.get("dominio"),
                "Principio Activo": at.get("principio_activo"),
                "Concentración": at.get("concentracion"),
                "Forma Farmacéutica": at.get("forma_farmaceutica"),
                "Cantidad Presentación": at.get("cantidad_presentacion"),
                "Contenido Neto": at.get("contenido_neto"),
                "Unidad Neto": at.get("contenido_neto_unidad_Des"),
                "Marca": at.get("marca"),
                "Fabricante": at.get("fabricante"),
                "ATC": at.get("codigo_atc"),
                "Genérico": at.get("generico"),
                "Costo USD": model_res.get("costo", 0.0),
                "Razonamiento": at.get("razonamiento")
            })
            
    df = pd.DataFrame(rows)
    
    # Crear archivo de Excel con formato limpio usando pandas
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparativa Multimodal")
        
    print(f"Archivo de Excel generado en: {os.path.abspath(excel_path)}")

if __name__ == "__main__":
    main()
