import json
import pandas as pd
import sys
import os

# Agregamos el path raíz para poder importar mega_orquestador_autonomo
sys.path.append('/home/synapse/source/repos/Clasificacion Medicamentos')
from mega_orquestador_autonomo import calcular_score_calidad

with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/benchmark_definitivo_30.json', 'r', encoding='utf-8') as f:
    bench_data = json.load(f)

lote_original = bench_data['lote_original']
resultados = bench_data['resultados']

# Añadir resultados del subagente
with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/subagent_30_complex.json', 'r', encoding='utf-8') as f:
    subagent_data = json.load(f)
resultados["gemini-3.5-flash-high (Subagent)"] = subagent_data

# Añadir resultados de DeepSeek Chat (V3)
try:
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/deepseek_30_complex.json', 'r', encoding='utf-8') as f:
        deepseek_data = json.load(f)
    resultados["deepseek/deepseek-chat"] = deepseek_data
except FileNotFoundError:
    pass

# Añadir resultados de DeepSeek V4 Pro
try:
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/deepseek_v4_pro_30_complex.json', 'r', encoding='utf-8') as f:
        deepseek_v4_data = json.load(f)
    resultados["deepseek/deepseek-v4-pro"] = deepseek_v4_data
except FileNotFoundError:
    pass

# Añadir resultados de Gemini 3.1 Pro Low (Subagent)
try:
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/gemini_3_1_low_30_complex.json', 'r', encoding='utf-8') as f:
        gemini_31_low_data = json.load(f)
    resultados["gemini-3.1-pro-low (Subagent)"] = gemini_31_low_data
except FileNotFoundError:
    pass

# Añadir resultados de GLM 5.2
try:
    with open('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/glm_5_2_30_complex.json', 'r', encoding='utf-8') as f:
        glm_data = json.load(f)
    resultados["z-ai/glm-5.2"] = glm_data
except FileNotFoundError:
    pass

records = []
for idx, original in enumerate(lote_original):
    codbarras = original['registro']['codbarras']
    desc = original['registro']['descripcion_original']
    
    for mod, data in resultados.items():
        if data is None:
            # Modelo falló totalmente
            records.append({
                "codbarras": codbarras,
                "descripcion": desc,
                "modelo": mod,
                "dominio": None, "PA": None, "Conc": None, "FF": None,
                "Cant": None, "Neto": None, "UndNeto": None, "Fabricante": None, "Marca": None,
                "ATC": None, "Blister": None, "Generico": None,
                "Razonamiento": "FALLO JSON",
                "Score": 0
            })
            continue
            
        try:
            item = data[idx]
        except IndexError:
            # En caso de truncamiento parcial
             records.append({
                "codbarras": codbarras,
                "descripcion": desc,
                "modelo": mod,
                "Razonamiento": "TRUNCADO",
                "Score": 0
            })
             continue
        
        atr = item.get('atributos_nuevos_consolidados', {})
        score = calcular_score_calidad(atr)
        
        records.append({
            "codbarras": codbarras,
            "descripcion": desc,
            "modelo": mod,
            "dominio": atr.get("dominio"),
            "PA": atr.get("principio_activo"),
            "Conc": atr.get("concentracion"),
            "FF": atr.get("forma_farmaceutica"),
            "Cant": atr.get("cantidad_presentacion"),
            "Neto": atr.get("contenido_neto"),
            "UndNeto": atr.get("contenido_neto_unidad_Des"),
            "Fabricante": atr.get("fabricante"),
            "Marca": atr.get("marca"),
            "ATC": atr.get("codigo_atc"),
            "Blister": atr.get("blister"),
            "Generico": atr.get("generico"),
            "Razonamiento": atr.get("razonamiento"),
            "Score": score
        })

df = pd.DataFrame(records)

precios_map = {
    "gemini-3.1-pro-low (Subagent)": ("$2.00", "$12.00"),
    "gemini-3.5-flash-high (Subagent)": ("$1.50", "$9.00"),
    "z-ai/glm-5.2": ("$1.40", "$4.40"),
    "deepseek/deepseek-v4-pro": ("$0.435", "$0.87"),
    "deepseek/deepseek-chat": ("$0.20", "$0.80"),
    "qwen/qwen-2.5-72b-instruct": ("$0.36", "$0.40"),
    "mistralai/mixtral-8x22b-instruct": ("$2.00", "$6.00"),
    "google/gemini-2.5-pro": ("$1.25", "$10.00"),
    "google/gemini-flash-1.5-8b": ("$0.075", "$0.30"),
    "minimax/minimax-m3": ("$1.25", "$10.00")
}

df['Precio Entrada (1M)'] = df['modelo'].map(lambda x: precios_map.get(x, ("-", "-"))[0])
df['Precio Salida (1M)'] = df['modelo'].map(lambda x: precios_map.get(x, ("-", "-"))[1])

# Reordenar columnas
cols = ["codbarras", "descripcion", "modelo", "Score", "Precio Entrada (1M)", "Precio Salida (1M)", "dominio", "PA", "Conc", "FF", "Cant", "Neto", "UndNeto", "Fabricante", "Marca", "ATC", "Blister", "Generico", "Razonamiento"]
cols = [c for c in cols if c in df.columns]
df = df[cols]

# Calcular el score promedio por modelo
scores_promedio = df.groupby('modelo')['Score'].mean().reset_index()
scores_promedio['Precio Entrada (1M)'] = scores_promedio['modelo'].map(lambda x: precios_map.get(x, ("-", "-"))[0])
scores_promedio['Precio Salida (1M)'] = scores_promedio['modelo'].map(lambda x: precios_map.get(x, ("-", "-"))[1])
scores_promedio = scores_promedio.sort_values(by='Score', ascending=False)

print("=== SCORES PROMEDIO Y PRECIOS (30 COMPUESTOS) ===")
print(scores_promedio.to_string(index=False))

df.to_excel('/home/synapse/source/repos/Clasificacion Medicamentos/scratch/comparativa_modelos_30_complejos.xlsx', index=False)
print("\nExportado exitosamente a: /home/synapse/source/repos/Clasificacion Medicamentos/scratch/comparativa_modelos_30_complejos.xlsx")
