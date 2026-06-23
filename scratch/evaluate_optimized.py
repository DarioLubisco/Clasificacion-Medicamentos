import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
import urllib.request
import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def obtener_taxonomias_estrictas():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dominio, categoria, subcategoria FROM Procurement.Taxonomia WHERE activo=1")
        tax = [f"- Dominio: {r[0]} | Categoria: {r[1]} | Subcategoria: {r[2]}" for r in cursor.fetchall()]
        conn.close()
        return "\n".join(tax)
    except Exception as e:
        return ""

def calcular_score_calidad(atrib):
    score = 0
    dominio = atrib.get('dominio', 'MEDICAMENTO_ALOPATICO') if atrib else 'MEDICAMENTO_ALOPATICO'
    es_med = dominio in ['MEDICAMENTO_ALOPATICO', 'PRODUCTO_NATURAL_HOMEOPATICO', 'SUPLEMENTO_VITAMINICO']
    
    if not atrib:
        return 0
        
    tiene_cant = atrib.get('cantidad_presentacion') is not None
    
    if es_med:
        if not atrib.get('principio_activo') or not atrib.get('concentracion') or not atrib.get('forma_farmaceutica'):
            return 0 
        if not tiene_cant:
            return 0
            
    if atrib.get('principio_activo'): score += 15
    if atrib.get('concentracion'): score += 15
    if atrib.get('forma_farmaceutica'): score += 15
    if tiene_cant: score += 10
    if atrib.get('contenido_neto'): score += 5
    if atrib.get('origen'): score += 10
    if atrib.get('segmento_etario'): score += 10
    if atrib.get('fabricante'): score += 5
    if atrib.get('marca'): score += 5
    if atrib.get('codigo_atc'): score += 5
    if atrib.get('generico') in [1, 0]: score += 5
    
    return min(100, score)

def normalizar_segmento_etario(val):
    if not val: return "NO_DEFINIDO"
    v = str(val).upper().strip()
    if "ADULTO" in v: return "ADULTO"
    if "PEDIATRICO" in v or "INFANTIL" in v or "NIÑO" in v: return "PEDIATRICO"
    if "NEONATAL" in v or "BEBE" in v: return "NEONATAL"
    if "MIXTO" in v: return "MIXTO"
    if "GENERAL" in v or "TODO" in v: return "GENERAL"
    return "NO_DEFINIDO"

def extract_json_from_content(content):
    content = content.strip()
    for prefix in ["```json", "```"]:
        if prefix in content:
            parts = content.split(prefix)
            for part in parts[1:]:
                subpart = part.split("```")[0].strip()
                try:
                    return json.loads(subpart)
                except Exception:
                    pass
    start_idx = content.find('[')
    if start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(content[start_idx:])
            return obj
        except Exception:
            pass
    try:
        return json.loads(content)
    except Exception:
        pass
    raise ValueError("No valid JSON found in response content")

def llamar_openrouter_multimodal(context_json_str, taxonomias_existentes, model, imagenes_b64):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Actúa como el Agente Investigador Farmacéutico. Tu tarea es analizar un lote de productos utilizando tres fuentes de información: su descripción original, los contextos de búsqueda web adjuntos y las IMÁGENES de referencia provistas.

Tu objetivo principal es la PRECISIÓN ABSOLUTA (Zero-Tolerance para alucinaciones). Extraer un dato que no esté explícita o científicamente respaldado por los elementos proporcionados se considera un ERROR CRÍTICO. Si la información no es concluyente o tienes la menor duda, debes asignar `null` al atributo correspondiente.

---

### 1. JERARQUÍA DE FUENTES Y REGLAS MULTIMODALES
- **Prioridad Visual**: Si existe contradicción entre los datos de texto (contexto web de farmacias) y el empaque físico visible en la IMAGEN (ej: la descripción web dice 20 tabletas pero la foto de la caja muestra claramente "10 tabletas"), prevalece la información de la IMAGEN.
- **Validación de Contexto (Anti-Basura)**: Si la imagen provista claramente NO es un producto de farmacia o está corrompida (ej. una herramienta, ropa, o imagen genérica de error), ignora la imagen, usa solo el texto, reduce el `confianza_nivel` a 1 o 2, y documéntalo en el razonamiento.
- **Resolución de Discrepancias**: Si hay contradicciones entre las fuentes, documenta el conflicto en `confianza_razonamiento` y reduce el `confianza_nivel` a 4 o 3 según corresponda.
- **Evidencia Visual**: Si el nombre del laboratorio o fabricante es visible en el empaque de la imagen, extráelo aunque no aparezca en el texto del contexto web.

---

### 2. DICCIONARIO DE ATRIBUTOS Y ESPECIFICACIÓN DE TIPOS
Para cada registro, debes extraer y validar exactamente los siguientes campos:

*   **razonamiento** (String): Justificación breve del análisis general del producto y cómo se llegó a las deducciones.
*   **confianza_nivel** (Integer, 1 al 5): Grado de certeza de la clasificación (ver escala de confianza abajo).
*   **confianza_razonamiento** (String): Explicación técnica de por qué se asignó ese nivel de confianza.
*   **dominio** (String, OBLIGATORIO): Dominio taxonómico exacto según el catálogo activo.
*   **categoria** (String, OBLIGATORIO): Categoría exacta según el catálogo activo.
*   **subcategoria** (String, OBLIGATORIO): Subcategoría exacta según el catálogo activo.
*   **principio_activo** (String o Null): Nombre científico del principio activo en formato estándar. Usa `null` si el producto es un insumo o dispositivo médico.
*   **concentracion** (String o Null): Concentración del principio activo (ej: "500 mg", "10 mg/ml").
*   **forma_farmaceutica** (String o Null): Presentación física simplificada a su familia base (ej: "Comprimido", "Jarabe"). MANTÉN la vía de administración si es crítica para la subcategoría (ej: "Solución Oftálmica").
*   **requiere_recipe** (Integer, 0 o 1): `1` si el medicamento requiere receta/récipe médico para su venta, `0` si es de venta libre (OTC). Usa `null` si no hay certeza o es un insumo.
*   **segmento_etario** (String o Null): Público objetivo explícito (ej: "Adulto", "Pediátrico", "Infantil"). NO deducir si no hay evidencia explícita en texto o imagen.
*   **fabricante** (String o Null): Razón social del laboratorio que fabrica el producto.
*   **marca** (String o Null): Marca comercial del producto. NO asumas la palabra "Genérico" como marca.
*   **origen** (String o Null): País de fabricación del producto (solo si se menciona explícitamente).
*   **codigo_atc** (String o Null): Código ATC. Extrae el código alfanumérico que aparece entre corchetes [ ] en la subcategoría que seleccionaste del catálogo activo (ej: si eliges "[N06A] ANTIDEPRESIVOS", el código es "N06A"). No uses los corchetes en el JSON.
*   **cantidad_presentacion** (Integer o Null): Total de unidades o envases según las reglas de negocio (ver abajo).
*   **contenido_neto** (Float o Null): Valor numérico del peso/volumen o dosis por unidad. Formato entero si no tiene decimales (ej: 500 en lugar de 500.0).
*   **contenido_neto_unidad_Des** (String o Null): Unidad de medida asociada (ej: "Caja", "Blister", "ml", "g", "sobres").
*   **blister** (Integer, 0 o 1): `1` si el producto viene en presentación de blíster(s), `0` si no.
*   **generico** (Integer, 0 o 1): `1` si es un medicamento genérico (denominación común internacional), `0` si es de marca/patente.
*   **clasificacion_insumo_Des** (String o Null): Tipo de insumo si aplica (ej: "Inyectadora", "Pañal", "Gasa"). Usa `null` si el producto es un medicamento.

---

### 3. REGLAS DE NEGOCIO Y FORMULACIÓN DE PRESENTACIONES
El cálculo de cantidades debe basarse estrictamente en el EMPAQUE EXTERNO PRINCIPAL, no en el estado de la materia del medicamento:

- **Regla A (Empaque Principal = CAJA con múltiples unidades)**:
  * Si el producto es una CAJA que agrupa múltiples unidades individuales idénticas en su interior (blísteres con tabletas, múltiples sobres de polvo, o múltiples ampollas/viales líquidos), el `contenido_neto` es invariablemente `1`, la unidad `contenido_neto_unidad_Des` es `'Caja'`, y el total general de unidades (la suma de todas las pastillas, todos los sobres o todas las ampollas de la caja) se extrae en `cantidad_presentacion`. 
  * *Ejemplo*: Una caja con 5 sobres de suero oral de 27.9g cada uno -> `cantidad_presentacion`: 5, `contenido_neto`: 1, `contenido_neto_unidad_Des`: "Caja".

- **Regla B (Empaque Principal = FRASCO, TUBO o LATA único)**:
  * Si el producto se vende como un envase individual o frasco único (Jarabes, Cremas, Gotas Oftálmicas, Suspensión, Fórmulas en Lata), la `cantidad_presentacion` es la cantidad de envases (casi siempre `1`), y el `contenido_neto` es la capacidad de dicho envase (volumen o peso).
  * *Ejemplo*: Un frasco de jarabe para la tos de 120ml -> `cantidad_presentacion`: 1, `contenido_neto`: 120, `contenido_neto_unidad_Des`: "ml". Evita decimales si es entero (120 y no 120.0).

---

### 4. REGLA INQUEBRANTABLE DE TAXONOMÍA
El producto DEBE encajar en alguna de las combinaciones activas provistas a continuación. **Bajo ninguna circunstancia inventes o infieras nuevas categorías**. Si el producto no encaja exactamente en ninguna opción del catálogo activo provisto, asigna `null` a dominio, categoria y subcategoria, reporta un nivel de confianza bajo y documenta el motivo en el razonamiento.

[TAXONOMÍA ACTIVA DISPONIBLE]
{taxonomias_existentes}
[FIN DE TAXONOMÍA ACTIVA]

---

### 5. ESCALA DE NIVELES DE CONFIANZA
*   **5 - TOTAL**: Evidencia explícita, inequívoca y sin contradicciones en texto o imagen.
*   **4 - ALTA**: Deducible científicamente con absoluta certeza (ej: deducir el principio activo a partir del nombre comercial si está plenamente estandarizado en la taxonomía), con discrepancias mínimas no críticas.
*   **3 - MEDIA**: Información suficiente pero con discrepancias leves o ambigüedad entre las fuentes que no impiden clasificar con razonable certeza.
*   **2 - BAJA**: Datos escasos, contradictorios o basados en inferencias débiles.
*   **1 - NULA**: Ausencia de datos críticos para la identificación segura del producto.

---

### 6. EJEMPLOS DE COMPORTAMIENTO (FEW-SHOT)

**Ejemplo 1 (Sólidos en Caja)**:
- Descripción: "IBUPROFENO 400MG X 10 TAB"
- Imagen: Muestra caja de "Ibuprofeno 400mg Calox" con 10 tabletas en blíster.
- Contexto web: "Ibuprofeno 400mg caja con 20 tabletas - Farmacia X"

**Salida JSON Esperada 1**:
```json
[
  {{
    "registro": {{
      "codbarras": "7501234567890",
      "descripcion_original": "IBUPROFENO 400MG X 10 TAB"
    }},
    "atributos_nuevos_consolidados": {{
      "razonamiento": "Se identifica como Ibuprofeno de 400mg. Aunque la web reporta 20 tabletas, la imagen del empaque real y la descripción original confirman la presentación de 10 tabletas del laboratorio Calox.",
      "confianza_nivel": 4,
      "confianza_razonamiento": "Se reduce de 5 a 4 debido a la discrepancia en la cantidad de tabletas reportada en el contexto web frente a la imagen física y descripción, prevaleciendo la imagen física.",
      "dominio": "MEDICAMENTO_ALOPATICO",
      "categoria": "ANALGESICOS_Y_ANTIINFLAMATORIOS",
      "subcategoria": "IBUPROFENO",
      "principio_activo": "Ibuprofeno",
      "concentracion": "400 mg",
      "forma_farmaceutica": "Tableta",
      "requiere_recipe": 0,
      "segmento_etario": null,
      "origen": null,
      "fabricante": "Calox",
      "marca": "Ibuprofeno Calox",
      "codigo_atc": "M01AE01",
      "cantidad_presentacion": 10,
      "contenido_neto": 1,
      "contenido_neto_unidad_Des": "Caja",
      "blister": 1,
      "generico": 1,
      "clasificacion_insumo_Des": null
    }}
  }}
]
```

**Ejemplo 2 (Caja con múltiples polvos/líquidos)**:
- Descripción: "DISCOLAYTE POLVO ORAL CAJA X 5 SOBRES"
- Imagen: Muestra caja de "Discolayte" indicando 5 sobres.
- Contexto web: "Suero oral Discolayte con 5 sobres de 27.9g"

**Salida JSON Esperada 2**:
```json
[
  {{
    "registro": {{
      "codbarras": "7509876543210",
      "descripcion_original": "DISCOLAYTE POLVO ORAL CAJA X 5 SOBRES"
    }},
    "atributos_nuevos_consolidados": {{
      "razonamiento": "Es un suero de rehidratación en polvo contenido en sobres. Al ser una caja que agrupa múltiples sobres (5), aplica la Regla A. La presentación es 5 en cantidad y 1 Caja en contenido neto.",
      "confianza_nivel": 5,
      "confianza_razonamiento": "La imagen y la descripción coinciden plenamente en que son 5 sobres en una caja.",
      "dominio": "MEDICAMENTO_ALOPATICO",
      "categoria": "ELECTROLITOS_ORALES",
      "subcategoria": "SALES_DE_REHIDRATACION_ORAL",
      "principio_activo": "Sales de Rehidratación Oral",
      "concentracion": "27.9 g",
      "forma_farmaceutica": "Polvo para suspensión oral",
      "requiere_recipe": 0,
      "segmento_etario": "GENERAL",
      "origen": null,
      "fabricante": null,
      "marca": "Discolayte",
      "codigo_atc": "A07CA",
      "cantidad_presentacion": 5,
      "contenido_neto": 1,
      "contenido_neto_unidad_Des": "Caja",
      "blister": 0,
      "generico": 0,
      "clasificacion_insumo_Des": null
    }}
  }}
]
```

LOTE A PROCESAR:
{context_json_str}
"""
    
    content_payload = [{"type": "text", "text": prompt}]
    for b64 in imagenes_b64:
        content_payload.append({"type": "image_url", "image_url": {"url": b64}})
        
    data = {
        "model": model, 
        "messages": [{"role": "user", "content": content_payload}],
        "temperature": 0.0
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode())
            usage = result.get('usage', {})
            content = result['choices'][0]['message']['content']
            if not content:
                refusal = result['choices'][0]['message'].get('refusal')
                reasoning = result['choices'][0]['message'].get('reasoning')
                print(f"    [Aviso] Modelo {model} no retornó content. Refusal: {refusal} | Reasoning: {reasoning}")
                return None, usage, None
                
            try:
                parsed_json = extract_json_from_content(content)
                return parsed_json, usage, content
            except Exception as e:
                print(f"    [Error Parseo] Fallo al extraer JSON de {model}: {e}")
                print(f"    [Contenido Crudo]:\n{content}\n")
                return None, usage, content
    except Exception as e:
        print(f"    Error {model}: {e}")
        return None, {}, None

def main():
    print("INICIANDO EVALUACIÓN MULTIMODAL (PROMPT OPTIMIZADO DEL USUARIO)")
    
    input_path = "scratch/scraping_multimodal_results.json"
    comp_path = "scratch/resultados_comparativa_atc3.json"
    excel_path = "scratch/comparativa_modelos_atc3.xlsx"
    
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra {input_path}")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        lote_scraping = json.load(f)
        
    resultados_multimodal = {}
    if os.path.exists(comp_path):
        try:
            with open(comp_path, "r", encoding="utf-8") as f:
                resultados_multimodal = json.load(f)
        except Exception:
            pass
            
    taxonomias_str = obtener_taxonomias_estrictas()
    
    modelos = {
        "gemma_4_26b": "google/gemma-4-26b-a4b-it",
        "gemma_4_31b": "google/gemma-4-31b-it"
    }
    
    precios = {
        "gemma_4_31b": {"in": 0.12 / 1e6, "out": 0.35 / 1e6},
        "gemma_4_26b": {"in": 0.06 / 1e6, "out": 0.33 / 1e6}
    }
    
    for item in lote_scraping:
        ean = item["ean"]
        desc = item["descripcion"]
        fuentes_web = item["fuentes_web"]
        imagenes_b64 = item["imagenes_b64"]
        
        print(f"\nProcesando EAN {ean} - {desc} (Fuentes: {len(fuentes_web)}, Imágenes: {len(imagenes_b64)})")
        
        context_block = [{
            "registro": {"codbarras": ean, "descripcion_original": desc},
            "fuentes_web": fuentes_web
        }]
        
        if ean not in resultados_multimodal:
            resultados_multimodal[ean] = {"descripcion": desc}
            
        res_ean = resultados_multimodal[ean]
        res_ean["descripcion"] = desc
        
        updated_any = False
        
        keys_to_evaluate = ["gemma_4_26b"]
        
        i = 0
        while i < len(keys_to_evaluate):
            key = keys_to_evaluate[i]
            model_id = modelos[key]
            i += 1
            
            if key in res_ean and not res_ean[key].get("error", False) and res_ean[key].get("atrib") is not None:
                print(f"  {key} ya evaluado con éxito (Score: {res_ean[key]['score']}). Omitiendo.")
                continue
                
            print(f"  Evaluando con {model_id}...")
            res_txt, usage, content = llamar_openrouter_multimodal(json.dumps(context_block, indent=2), taxonomias_str, model_id, imagenes_b64)
            
            p_tokens = usage.get('prompt_tokens', 0)
            c_tokens = usage.get('completion_tokens', 0)
            costo = (p_tokens * precios[key]["in"]) + (c_tokens * precios[key]["out"])
            
            if res_txt and len(res_txt) > 0:
                atrib = res_txt[0].get('atributos_nuevos_consolidados', {})
                score = calcular_score_calidad(atrib)
                atrib['segmento_etario'] = normalizar_segmento_etario(atrib.get('segmento_etario'))
                res_ean[key] = {
                    "atrib": atrib,
                    "score": score,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo": costo
                }
                print(f"    [{key} Éxito] Score: {score} | Confianza: {atrib.get('confianza_nivel')} | Costo: ${costo:.6f}")
            else:
                res_ean[key] = {
                    "atrib": None,
                    "score": 0,
                    "tokens_in": p_tokens,
                    "tokens_out": c_tokens,
                    "costo": costo,
                    "error": True
                }
                print(f"    [{key} Fallo/Rechazo] Costo: ${costo:.6f}")
                
                with open("scratch/ia_errors.log", "a", encoding="utf-8") as f_err:
                    f_err.write(f"--- ERROR EAN {ean} ({model_id}) ---\n{content}\n\n")
                    
                if key == "gemma_4_26b":
                    print(f"  -> {key} falló. Agregando gemma_4_31b como fallback para {ean}.")
                    keys_to_evaluate.append("gemma_4_31b")
            
            updated_any = True
                
        resultados_multimodal[ean] = res_ean
        
        # Guardar reporte consolidado JSON incrementalmente
        if updated_any:
            with open(comp_path, "w", encoding="utf-8") as f:
                json.dump(resultados_multimodal, f, indent=2, ensure_ascii=False)
        
    # Recrear el archivo Excel
    rows = []
    model_mapping = {
        "gemma_4_26b": "Gemma 4 26B-A4B",
        "gemma_4_31b": "Gemma 4 31B"
    }
    
    for ean, item in resultados_multimodal.items():
        desc = item["descripcion"]
        for model_key, model_name in model_mapping.items():
            model_res = item.get(model_key)
            if not model_res or model_res.get("atrib") is None:
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
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparativa Optimizada")
        
    print(f"Archivo de Excel regenerado en: {os.path.abspath(excel_path)}")

if __name__ == "__main__":
    main()
