import json
import pandas as pd
import os
def export():
    comp_path = "scratch/resultados_comparativa_combinados.json"
    excel_path = "scratch/comparativa_modelos_combinados_nueva.xlsx"
    with open(comp_path, "r", encoding="utf-8") as f:
        resultados_multimodal = json.load(f)
    rows = []
    model_mapping = {
        "deepseek_v4_flash": "DeepSeek V4 Flash",
        "deepseek_v4_pro": "DeepSeek V4 Pro"
    }
    for ean, item in resultados_multimodal.items():
        desc = item["descripcion"]
        for model_key, model_name in model_mapping.items():
            model_res = item.get(model_key)
            if not model_res or model_res.get("atrib") is None:
                continue
            at = model_res["atrib"]
            rows.append({
                "EAN": ean,
                "Descripción": desc,
                "Modelo": model_name,
                "Score": model_res.get("score", 0),
                "Confianza Nivel": at.get("confianza_nivel"),
                "Confianza Razonamiento": at.get("confianza_razonamiento"),
                "Atributos Baja Confianza": ", ".join(at.get("atributos_baja_confianza", [])) if at.get("atributos_baja_confianza") else "",
                "Alertas Auditoria": at.get("alertas_auditoria"),
                "Dominio": at.get("dominio"),
                "Principio Activo": at.get("principio_activo"),
                "Concentración": at.get("concentracion"),
                "Forma Farmacéutica": at.get("forma_farmaceutica"),
                "Cantidad Presentación": at.get("cantidad_presentacion"),
                "Costo Total USD": model_res.get("costo_total", 0.0),
                "Razonamiento": at.get("razonamiento")
            })
    df = pd.DataFrame(rows)
    df.to_excel(excel_path, index=False, sheet_name="Comparativa Optimizada")
    print(f"Exported to {excel_path}")
export()
