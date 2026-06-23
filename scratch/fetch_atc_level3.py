import os
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import csv
import json
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CSV_URL = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202026-04-25.csv"

def descargar_atc():
    req = urllib.request.Request(CSV_URL)
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
        return list(csv.DictReader(content.splitlines()))

def traducir_lote(textos):
    print(f"Traduciendo lote de {len(textos)} términos...")
    prompt = "Traduce la siguiente lista de términos farmacológicos ATC del inglés al español médico profesional. Mantén el formato de array JSON estricto. Ejemplo de entrada: [\"Antidepressants\", \"Beta blocking agents\"]. Ejemplo de salida: [\"Antidepresivos\", \"Betabloqueantes\"].\n\nEntrada:\n" + json.dumps(textos)
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "google/gemini-2.5-flash", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req, timeout=120) as response:
        res = json.loads(response.read().decode())
        content = res['choices'][0]['message']['content']
        # Extract JSON array
        try:
            return json.loads(content)
        except:
            start = content.find('[')
            end = content.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(content[start:end])
            print("Error parsing JSON:", content)
            return textos

def main():
    print("Descargando ATC...")
    filas = descargar_atc()
    
    nivel1 = {}
    nivel2 = {}
    nivel3 = {}
    
    # Filtrar y agrupar
    for row in filas:
        code = row['atc_code']
        name = row['atc_name']
        if len(code) == 1:
            nivel1[code] = name
        elif len(code) == 3:
            nivel2[code] = name
        elif len(code) == 4:
            nivel3[code] = name

    print(f"Encontrados: {len(nivel1)} L1, {len(nivel2)} L2, {len(nivel3)} L3")
    
    # Traducir Nivel 1 y 2 para armar las Categorias
    print("Traduciendo Niveles 1 y 2...")
    textos_cat = list(nivel1.values()) + list(nivel2.values())
    textos_cat_es = traducir_lote(textos_cat)
    
    # Mapeo de traducciones
    trans_map = dict(zip(textos_cat, textos_cat_es))
    
    print("Traduciendo Nivel 3...")
    textos_sub = list(nivel3.values())
    textos_sub_es = []
    
    # Dividir en lotes de 100 para no reventar el LLM
    for i in range(0, len(textos_sub), 100):
        lote = textos_sub[i:i+100]
        textos_sub_es.extend(traducir_lote(lote))
        
    trans_map.update(dict(zip(textos_sub, textos_sub_es)))
    
    print("Generando SQL...")
    sql_lines = [
        "USE EnterpriseAdmin_AMC;",
        "GO",
        "-- Precaucion: Solo desactivamos los alopaticos actuales para no romper id referenciales",
        "UPDATE Procurement.Taxonomia SET activo = 0 WHERE dominio = 'MEDICAMENTO_ALOPATICO';",
        "GO",
        "INSERT INTO Procurement.Taxonomia (dominio, categoria, subcategoria, activo) VALUES"
    ]
    
    values = []
    for code3, name3 in nivel3.items():
        code2 = code3[:3]
        code1 = code3[0]
        
        if code2 not in nivel2: continue
        
        # Categoria = Nivel 2. Ej: N06 - PSICOANALEPTICOS
        cat_es = f"{code2} - {trans_map.get(nivel2[code2], nivel2[code2]).upper()}"
        # Subcategoria = Nivel 3. Ej: [N06A] ANTIDEPRESIVOS
        sub_es = f"[{code3}] {trans_map.get(name3, name3).upper()}"
        
        val = f"('MEDICAMENTO_ALOPATICO', '{cat_es.replace(chr(39), '')}', '{sub_es.replace(chr(39), '')}', 1)"
        values.append(val)
        
    sql_lines.append(",\n".join(values) + ";")
    sql_lines.append("GO")
    
    with open("scratch/actualizacion_taxonomia_atc3.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))
        
    print("Completado. Guardado en scratch/actualizacion_taxonomia_atc3.sql")

if __name__ == "__main__":
    main()
