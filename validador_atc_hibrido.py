import csv
import json
import re
import os
import time
import unicodedata
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def normalize_text(text):
    if not text: return set()
    # Eliminar acentos y pasar a minusculas
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
    # Reemplazos foneticos basicos ingles/español
    text = text.replace('ph', 'f').replace('th', 't').replace('y', 'i')
    # Quitar sufijos comunes que no aportan (ide, ida, in, ina)
    text = re.sub(r'(ide|ida|in|ina|um|o|a)$', '', text)
    # Limpiar caracteres no alfanumericos
    text = re.sub(r'[^a-z0-9]', ' ', text)
    return set(w for w in text.split() if len(w) > 3)

def verificar_llm(pa, atc_name):
    prompt = f"""Eres un farmacólogo experto.
¿Es el principio activo o compuesto "{pa}" farmacológicamente equivalente, sinónimo o perteneciente a la categoría "{atc_name}"?
Considera diferencias de idioma (inglés/español) y formulaciones compuestas.
Responde ÚNICAMENTE con la palabra TRUE o FALSE."""

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        ans = response.choices[0].message.content.strip().upper()
        return "TRUE" in ans
    except Exception as e:
        print(f"Error LLM: {e}")
        return False

def main():
    atc_map = {}
    try:
        with open("atc_dataset_completo.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                atc_map[row["atc_code"]] = row["atc_name"]
    except Exception as e:
        print("Error loading ATC CSV:", e)
        return

    input_file = "scratch/10_random_resultados_DS_FLASH.json"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Error loading JSON:", e)
        return

    print("=== INICIANDO VALIDACIÓN HÍBRIDA ATC ===\\n")
    
    for ean, item in data.items():
        desc = item.get("descripcion", ean)
        flash_data = item.get("deepseek_v4_flash", {})
        if not flash_data or not flash_data.get("atrib"):
            continue
            
        atrib = flash_data["atrib"]
        pa = atrib.get("principio_activo")
        atc = atrib.get("codigo_atc_profundo")
        
        if not atc or not pa:
            continue
            
        atc_name = atc_map.get(atc)
        if not atc_name:
            print(f"[-] {desc} | ATC '{atc}' NO ENCONTRADO.")
            atrib["confianza_atc"] = 0
            continue
            
        # 1. Pase Rápido Python (Fuzzy / Intersection)
        pa_words = normalize_text(pa)
        atc_words = normalize_text(atc_name)
        
        overlap = pa_words.intersection(atc_words)
        
        if overlap:
            print(f"[PY-OK] {desc} -> Match: {overlap}")
            # Asumimos que si no tenia confianza asiganda por el prompt, le ponemos 5
            if atrib.get("confianza_atc") is None:
                atrib["confianza_atc"] = 5
        else:
            print(f"[PY-FAIL] {desc} -> PA: '{pa}' | ATC: '{atc_name}'. Validando con LLM...")
            
            # 2. Pase Lento LLM
            es_valido = verificar_llm(pa, atc_name)
            if es_valido:
                print(f"   -> [LLM-OK] Validado por DeepSeek.")
                if atrib.get("confianza_atc") is None:
                    atrib["confianza_atc"] = 4 # 4 por haber requerido LLM
            else:
                print(f"   -> [LLM-FAIL] 🚨 ALUCINACIÓN CONFIRMADA.")
                atrib["confianza_atc"] = 0
                atrib["error_atc_alucinacion"] = True
        
        time.sleep(0.5)

    # Save output
    output_file = "scratch/10_random_resultados_DS_FLASH_VALIDADO.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"\\nValidación completada. Guardado en {output_file}")

if __name__ == "__main__":
    main()
