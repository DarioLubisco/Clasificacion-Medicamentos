import re

def normalizar_espacios(texto):
    if not texto:
        return ""
    return " ".join(str(texto).split()).strip().upper()

def limpiar_concentracion(conc):
    if not conc: return ""
    # Quitar todos los espacios
    conc = conc.replace(" ", "")
    return conc.upper()

def dividir_compuestos(texto, es_concentracion=False):
    if not texto:
        return []
    
    texto = normalizar_espacios(texto)
    
    if es_concentracion:
        # En concentraciones, los separadores suelen ser +, ,, ;, -, o ' Y '.
        # NO se usa / porque es para dilucion (ej 15MG/5ML).
        # EXCEPCIÓN: A veces el LLM usa / para separar ingredientes de pastillas (ej 875MG/125MG).
        # Reemplazaremos '/' por '-' SI lo que le sigue es una unidad de masa (MG, G, GR, MCG, UI).
        # Si lo que le sigue es ML, L, CC, es una dilución y se queda.
        
        # Unidades de masa: MG, G, GR, MCG, UI
        # Regex: reemplaza '/' seguido de números y (MG|G|GR|MCG|UI) por '-'
        texto_mod = re.sub(r'/(?=\s*\d*\.?\d+\s*(MG|G|GR|MCG|UI)\b)', '-', texto, flags=re.IGNORECASE)
        
        separadores = r'[\+;,]|\s+Y\s+|-'
        partes = re.split(separadores, texto_mod)
    else:
        # Principios activos. Evitar dividir por el guion si es parte de una palabra química
        # como N-BUTILBROMURO, ALFA-LIPOICO, BETA-CAROTENO, OMEGA-3.
        # Una regla segura: +, ,, ;, ' Y '
        # Y para el guion, solo dividir si está rodeado de espacios o separa nombres claros,
        # pero es arriesgado. Asumimos que si hay ',' o '+', el LLM usó eso.
        # Si no hay ',' o '+' pero hay '-', y NO empieza por 'N-' o 'ALFA-', es complejo.
        # Mejores separadores:
        separadores = r'[\+;,/]|\sY\s'
        partes = re.split(separadores, texto)
        
        # Si todavia hay un guion que parece separador de ingredientes
        if len(partes) == 1 and '-' in texto:
            raw_parts = texto.split('-')
            reconstructed = []
            skip = False
            for idx, part in enumerate(raw_parts):
                part = part.strip()
                if not part: continue
                if skip:
                    skip = False
                    continue
                
                # Prefijos químicos protegidos
                if part in ['N', 'ALFA', 'BETA', 'L', 'D', 'OMEGA'] and idx + 1 < len(raw_parts):
                    reconstructed.append(f"{part}-{raw_parts[idx+1].strip()}")
                    skip = True
                elif part.isdigit() and reconstructed:
                    # Mezclas como Omega-3-6-9
                    reconstructed[-1] = f"{reconstructed[-1]}-{part}"
                else:
                    reconstructed.append(part)
            partes = [p for p in reconstructed if p]
            
    # Limpiar cada parte
    partes = [p.strip() for p in partes if p.strip()]
    return partes

def procesar_farmacos(pa_raw, conc_raw):
    """
    Toma las cadenas crudas de la IA y devuelve un diccionario con el estado, 
    y los campos corregidos o el error.
    """
    pa_raw = str(pa_raw) if pa_raw else ""
    conc_raw = str(conc_raw) if conc_raw else ""
    
    # Validar nulos directos
    if pa_raw.upper() in ["NULL", "NONE", ""] and conc_raw.upper() in ["NULL", "NONE", ""]:
        return {
            "exito": True,
            "principio_activo": None,
            "concentracion": None,
            "observaciones": None
        }

    pas = dividir_compuestos(pa_raw, es_concentracion=False)
    concs = dividir_compuestos(conc_raw, es_concentracion=True)
    
    # Limpiar concentraciones de espacios
    concs = [limpiar_concentracion(c) for c in concs]
    
    # Caso 1: Un solo ingrediente
    if len(pas) == 1 and len(concs) <= 1:
        return {
            "exito": True,
            "principio_activo": pas[0],
            "concentracion": concs[0] if concs else None,
            "observaciones": None
        }
        
    # Caso 2: Multiples ingredientes pero longitudes distintas (incluyendo concentraciones vacias)
    if len(pas) != len(concs) and len(concs) > 0:
        # Retornar error de mismatch
        obs = f"ERR_MISMATCH_PA_CONC: IA extrajo {len(pas)} PAs ('{pa_raw}') y {len(concs)} CONCs ('{conc_raw}')."
        return {
            "exito": False,
            "principio_activo": None,
            "concentracion": None,
            "observaciones": obs,
            "crudos": {
                "pa_raw": pa_raw,
                "conc_raw": conc_raw
            }
        }
        
    # Caso 3: Igual longitud (o multiples PAs sin ninguna concentracion)
    # Emparejar, ordenar alfabeticamente por PA
    if len(concs) == 0:
        pares = [(p, "") for p in pas]
    else:
        pares = list(zip(pas, concs))
        
    # Ordenar estrictamente por principio activo
    pares.sort(key=lambda x: x[0])
    
    pa_final = "-".join([p[0] for p in pares])
    conc_final = "-".join([p[1] for p in pares if p[1]])
    
    if not conc_final:
        conc_final = None
        
    return {
        "exito": True,
        "principio_activo": pa_final,
        "concentracion": conc_final,
        "observaciones": "MULTIPLE_COMPUESTO_NORMALIZADO"
    }

# --- Pruebas de Desarrollo ---
if __name__ == "__main__":
    tests = [
        ("METFORMINA;SITAGLIPTINA", "1GR/50MG"),
        ("AMOXICILINA+ACIDO CLAVULANICO", "875MG/125MG"),
        ("N-BUTILBROMURO DE HIOSCINA, DIPIRONA", "20mg/5ml+2500mg/5ml"),
        ("amoxicilina, ácido clavulánico", "250mg-62.5mg/5ml"),
        ("Amoxicilina; Ácido clavulánico", "600mg/5ml"), # Mismatch intencional
    ]
    
    for pa, conc in tests:
        res = procesar_farmacos(pa, conc)
        print(f"RAW: {pa} | {conc}")
        print(f"RES: {res}\n")
