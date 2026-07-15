#!/usr/bin/env python3
"""
Comparativa entre GLM-4.7 (datos simulados) y DeepSeek V4 Flash (datos reales)
"""

import json
import pandas as pd
from pathlib import Path

# Load data
glm_file = Path("scratch/comparativa_batch1.json")
deepseek_file = Path("scratch/resultados_20_hard.json")

with open(glm_file) as f:
    glm_data = json.load(f)

with open(deepseek_file) as f:
    deepseek_data = json.load(f)

# Products to compare
products_to_compare = ["900000000001", "900000000014", "900000000018"]

# Extract comparison data
comparison_data = []

for ean in products_to_compare:
    if ean in glm_data["resultados_por_producto"] and ean in deepseek_data:
        glm_product = glm_data["resultados_por_producto"][ean]
        deepseek_product = deepseek_data[ean]

        # Get DeepSeek attributes (they're nested under deepseek_v4_flash.atrib)
        ds_attrib = deepseek_product["deepseek_v4_flash"]["atrib"]

        comparison = {
            "EAN": ean,
            "Descripción GLM": glm_product["descripcion"],
            "Descripción DeepSeek": deepseek_product["descripcion"],
            # GLM Data
            "GLM_Score": glm_product["score"],
            "GLM_Confianza_Nivel": glm_product["atributos"]["confianza_nivel"],
            "GLM_Dominio": glm_product["atributos"]["dominio"],
            "GLM_Categoria": glm_product["atributos"]["categoria"],
            "GLM_Subcategoria": glm_product["atributos"]["subcategoria"],
            "GLM_Principio_Activo": glm_product["atributos"]["principio_activo"],
            "GLM_Concentracion": glm_product["atributos"]["concentracion"],
            "GLM_Forma_Farmaceutica": glm_product["atributos"]["forma_farmaceutica"],
            "GLM_Fabricante": glm_product["atributos"]["fabricante"],
            "GLM_Marca": glm_product["atributos"]["marca"],
            "GLM_Codigo_ATC": glm_product["atributos"]["codigo_atc"],
            "GLM_Codigo_ATC_Profundo": glm_product["atributos"]["codigo_atc_profundo"],
            "GLM_Cantidad_Presentacion": glm_product["atributos"]["cantidad_presentacion"],
            "GLM_Generico": glm_product["atributos"]["generico"],
            "GLM_Requiere_Recipe": glm_product["atributos"]["requiere_recipe"],
            "GLM_Razonamiento": glm_product["atributos"]["razonamiento"],
            # DeepSeek Data
            "DS_Score": deepseek_product["deepseek_v4_flash"]["score"],
            "DS_Confianza_Nivel": ds_attrib["confianza_nivel"],
            "DS_Dominio": ds_attrib["dominio"],
            "DS_Categoria": ds_attrib["categoria"],
            "DS_Subcategoria": ds_attrib["subcategoria"],
            "DS_Principio_Activo": ds_attrib["principio_activo"],
            "DS_Concentracion": ds_attrib["concentracion"],
            "DS_Forma_Farmaceutica": ds_attrib["forma_farmaceutica"],
            "DS_Fabricante": ds_attrib["fabricante"],
            "DS_Marca": ds_attrib["marca"],
            "DS_Codigo_ATC": ds_attrib["codigo_atc"],
            "DS_Codigo_ATC_Profundo": ds_attrib["codigo_atc_profundo"],
            "DS_Cantidad_Presentacion": ds_attrib["cantidad_presentacion"],
            "DS_Generico": ds_attrib["generico"],
            "DS_Requiere_Recipe": ds_attrib["requiere_recipe"],
            "DS_Razonamiento": ds_attrib["razonamiento"],
            # DeepSeek Additional Metrics
            "DS_Tokens_In": deepseek_product["deepseek_v4_flash"]["tokens_in"],
            "DS_Tokens_Out": deepseek_product["deepseek_v4_flash"]["tokens_out"],
            "DS_Costo_Total": deepseek_product["deepseek_v4_flash"]["costo_total"],
            "DS_Atributos_Baja_Confianza": ", ".join(ds_attrib["atributos_baja_confianza"]) if ds_attrib["atributos_baja_confianza"] else "Ninguno",
            "DS_Alertas_Auditoria": ds_attrib["alertas_auditoria"] or "Ninguna",
        }

        comparison_data.append(comparison)

# Create DataFrame
df_comparacion = pd.DataFrame(comparison_data)

# Create Excel file with multiple sheets
excel_file = Path("scratch/comparativa_glm_vs_deepseek.xlsx")

with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    # Sheet 1: Productos Coincidentes (Side-by-side comparison)
    df_comparacion.to_excel(writer, sheet_name='Productos Coincidentes', index=False)

    # Sheet 2: Resumen de Métricas
    resumen_data = {
        "Métrica": [
            "Total Productos Comparados",
            "Promedio Score GLM-4.7",
            "Promedio Score DeepSeek",
            "Diferencia Promedio Scores",
            "Promedio Confianza GLM-4.7",
            "Promedio Confianza DeepSeek",
            "Total Costo DeepSeek",
            "Promedio Tokens In DeepSeek",
            "Promedio Tokens Out DeepSeek",
            "Productos con baja confianza DeepSeek",
        ],
        "Valor": [
            len(products_to_compare),
            df_comparacion["GLM_Score"].mean(),
            df_comparacion["DS_Score"].mean(),
            df_comparacion["GLM_Score"].mean() - df_comparacion["DS_Score"].mean(),
            df_comparacion["GLM_Confianza_Nivel"].mean(),
            df_comparacion["DS_Confianza_Nivel"].mean(),
            df_comparacion["DS_Costo_Total"].sum(),
            df_comparacion["DS_Tokens_In"].mean(),
            df_comparacion["DS_Tokens_Out"].mean(),
            len([c for c in df_comparacion["DS_Atributos_Baja_Confianza"] if c != "Ninguno"]),
        ]
    }
    df_resumen = pd.DataFrame(resumen_data)
    df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

    # Sheet 3: Diferencias por Producto
    diferencias_data = []
    for _, row in df_comparacion.iterrows():
        diffs = {
            "EAN": row["EAN"],
            "Descripción": row["Descripción DeepSeek"],
            "Diferencia Score": row["GLM_Score"] - row["DS_Score"],
            "Diferencia Confianza": row["GLM_Confianza_Nivel"] - row["DS_Confianza_Nivel"],
            "Dominio Coincide": "Sí" if row["GLM_Dominio"] == row["DS_Dominio"] else "No",
            "Categoria Coincide": "Sí" if row["GLM_Categoria"] == row["DS_Categoria"] else "No",
            "Principio Activo Coincide": "Sí" if row["GLM_Principio_Activo"] == row["DS_Principio_Activo"] else "No",
            "Concentración Coincide": "Sí" if row["GLM_Concentracion"] == row["DS_Concentracion"] else "No",
            "Forma Farmacéutica Coincide": "Sí" if row["GLM_Forma_Farmaceutica"] == row["DS_Forma_Farmaceutica"] else "No",
            "ATC Coincide": "Sí" if row["GLM_Codigo_ATC"] == row["DS_Codigo_ATC"] else "No",
            "ATC Profundo Coincide": "Sí" if row["GLM_Codigo_ATC_Profundo"] == row["DS_Codigo_ATC_Profundo"] else "No",
        }
        diferencias_data.append(diffs)

    df_diferencias = pd.DataFrame(diferencias_data)
    df_diferencias.to_excel(writer, sheet_name='Diferencias', index=False)

    # Sheet 4: Análisis Detallado de Razonamiento
    razonamiento_data = []
    for _, row in df_comparacion.iterrows():
        razonamiento = {
            "EAN": row["EAN"],
            "Descripción": row["Descripción DeepSeek"],
            "GLM_Razonamiento": row["GLM_Razonamiento"],
            "DS_Razonamiento": row["DS_Razonamiento"],
            "DS_Atributos_Baja_Confianza": row["DS_Atributos_Baja_Confianza"],
            "DS_Alertas_Auditoria": row["DS_Alertas_Auditoria"],
        }
        razonamiento_data.append(razonamiento)

    df_razonamiento = pd.DataFrame(razonamiento_data)
    df_razonamiento.to_excel(writer, sheet_name='Análisis Razonamiento', index=False)

print(f"✅ Excel file created: {excel_file}")
print(f"   - Hoja 'Productos Coincidentes': Comparación lado a lado")
print(f"   - Hoja 'Resumen': Métricas clave")
print(f"   - Hoja 'Diferencias': Análisis de discrepancias")
print(f"   - Hoja 'Análisis Razonamiento': Razonamiento detallado")

# Create markdown report
markdown_file = Path("informe_comparativa_glm_vs_deepseek.md")

md_content = f"""# Comparativa: GLM-4.7 (Simulado) vs DeepSeek V4 Flash (Real)

**Fecha:** 2026-07-01  
**Productos comparados:** {len(products_to_compare)}

## ⚠️ ADVERTENCIA IMPORTANTE

**Los resultados de GLM-4.7 son DATOS SIMULADOS.** El sandbox de Cursor bloqueó las conexiones a la API de GLM-4.7, por lo que los datos en `comparativa_batch1.json` son genéricos y no representan el verdadero rendimiento de GLM-4.7.

**Los resultados de DeepSeek V4 Flash son DATOS REALES** obtenidos mediante API real con análisis detallado, conteo de tokens y costos.

**Esta comparación es entre DeepSeek V4 Flash (real) vs DeepSeek V4 Flash (simulado como GLM-4.7).**

---

## Productos Comparados

Los siguientes 3 productos coinciden por EAN en ambos archivos:

1. **900000000001** - Diosmina 450 mg y Hesperidina 50 mg
2. **900000000014** - Heparina 250 UI/g gel 30g
3. **900000000018** - Testo-Mix 250mg/ml 10 ampollas

---

## Resumen de Métricas

| Métrica | Valor |
|---------|-------|
| Total Productos Comparados | {len(products_to_compare)} |
| Promedio Score GLM-4.7 (Simulado) | {df_comparacion['GLM_Score'].mean():.1f} |
| Promedio Score DeepSeek (Real) | {df_comparacion['DS_Score'].mean():.1f} |
| Diferencia Promedio Scores | {df_comparacion['GLM_Score'].mean() - df_comparacion['DS_Score'].mean():.1f} |
| Promedio Confianza GLM-4.7 (Simulado) | {df_comparacion['GLM_Confianza_Nivel'].mean():.1f}/5 |
| Promedio Confianza DeepSeek (Real) | {df_comparacion['DS_Confianza_Nivel'].mean():.1f}/5 |
| Total Costo DeepSeek | ${df_comparacion['DS_Costo_Total'].sum():.6f} |
| Promedio Tokens In DeepSeek | {df_comparacion['DS_Tokens_In'].mean():.0f} |
| Promedio Tokens Out DeepSeek | {df_comparacion['DS_Tokens_Out'].mean():.0f} |
| Productos con baja confianza DeepSeek | {len([c for c in df_comparacion['DS_Atributos_Baja_Confianza'] if c != 'Ninguno'])} |

---

## Análisis Detallado por Producto

"""

for _, row in df_comparacion.iterrows():
    md_content += f"""
### EAN: {row['EAN']} - {row['Descripción DeepSeek']}

#### Comparación de Scores
- **GLM-4.7 (Simulado):** {row['GLM_Score']}/100
- **DeepSeek (Real):** {row['DS_Score']}/100
- **Diferencia:** {row['GLM_Score'] - row['DS_Score']} puntos

#### Nivel de Confianza
- **GLM-4.7:** {row['GLM_Confianza_Nivel']}/5
- **DeepSeek:** {row['DS_Confianza_Nivel']}/5

#### Atributos Clave

| Atributo | GLM-4.7 (Simulado) | DeepSeek (Real) | ¿Coinciden? |
|----------|-------------------|-----------------|-------------|
| Dominio | {row['GLM_Dominio'] or 'N/A'} | {row['DS_Dominio'] or 'N/A'} | {'✅' if row['GLM_Dominio'] == row['DS_Dominio'] else '❌'} |
| Categoría | {row['GLM_Categoria'] or 'N/A'} | {row['DS_Categoria'] or 'N/A'} | {'✅' if row['GLM_Categoria'] == row['DS_Categoria'] else '❌'} |
| Subcategoría | {row['GLM_Subcategoria'] or 'N/A'} | {row['DS_Subcategoria'] or 'N/A'} | {'✅' if row['GLM_Subcategoria'] == row['DS_Subcategoria'] else '❌'} |
| Principio Activo | {row['GLM_Principio_Activo'] or 'N/A'} | {row['DS_Principio_Activo'] or 'N/A'} | {'✅' if row['GLM_Principio_Activo'] == row['DS_Principio_Activo'] else '❌'} |
| Concentración | {row['GLM_Concentracion'] or 'N/A'} | {row['DS_Concentracion'] or 'N/A'} | {'✅' if row['GLM_Concentracion'] == row['DS_Concentracion'] else '❌'} |
| Forma Farmacéutica | {row['GLM_Forma_Farmaceutica'] or 'N/A'} | {row['DS_Forma_Farmaceutica'] or 'N/A'} | {'✅' if row['GLM_Forma_Farmaceutica'] == row['DS_Forma_Farmaceutica'] else '❌'} |
| Código ATC | {row['GLM_Codigo_ATC'] or 'N/A'} | {row['DS_Codigo_ATC'] or 'N/A'} | {'✅' if row['GLM_Codigo_ATC'] == row['DS_Codigo_ATC'] else '❌'} |
| ATC Profundo | {row['GLM_Codigo_ATC_Profundo'] or 'N/A'} | {row['DS_Codigo_ATC_Profundo'] or 'N/A'} | {'✅' if row['GLM_Codigo_ATC_Profundo'] == row['DS_Codigo_ATC_Profundo'] else '❌'} |

#### Razonamiento

**GLM-4.7 (Simulado):**
> {row['GLM_Razonamiento']}

**DeepSeek (Real):**
> {row['DS_Razonamiento'][:500]}...

#### Análisis de DeepSeek

- **Atributos con Baja Confianza:** {row['DS_Atributos_Baja_Confianza']}
- **Alertas de Auditoría:** {row['DS_Alertas_Auditoria']}
- **Tokens In:** {row['DS_Tokens_In']:,}
- **Tokens Out:** {row['DS_Tokens_Out']:,}
- **Costo:** ${row['DS_Costo_Total']:.6f}

---

"""

md_content += """
## Diferencias Clave Observadas

### Análisis General

1. **Simulación vs Realidad:** Los datos de GLM-4.7 son genéricos y siguen patrones predefinidos, mientras que DeepSeek muestra análisis específicos y detallados.

2. **Profundidad de Razonamiento:**
   - GLM-4.7: Razonamientos genéricos del tipo "Análisis basado en descripción: [nombre]. Clasificación según características farmacológicas."
   - DeepSeek: Razonamientos específicos que explican la lógica de clasificación, identifican fuentes de información, y destacan limitaciones.

3. **Manejo de Incertidumbre:**
   - GLM-4.7: Siempre asigna confianza alta (4-5/5) sin explicar limitaciones.
   - DeepSeek: Ajusta el nivel de confianza según la calidad de la información disponible y lista atributos con baja confianza explícitamente.

4. **Alertas de Auditoría:**
   - GLM-4.7: No genera alertas de auditoría.
   - DeepSeek: Genera alertas específicas cuando falta información crítica.

### Por Producto

#### 1. Diosmina 450 mg y Hesperidina 50 mg (EAN: 900000000001)
- **Scores:** GLM=90, DeepSeek=75 (diferencia: 15)
- **Confianza:** GLM=4/5, DeepSeek=5/5
- **Coincidencias:** Dominio, principio activo, concentración, forma farmacéutica, ATC
- **Diferencias:** Categoría y subcategoría con formatos distintos
- **Observación:** DeepSeek incluye detalles sobre fabricante (Drotafarma) no presentes en GLM

#### 2. Heparina 250 UI/g gel 30g (EAN: 900000000014)
- **Scores:** GLM=80, DeepSeek=70 (diferencia: 10)
- **Confianza:** GLM=5/5, DeepSeek=4/5
- **Coincidencias:** Dominio, principio activo, concentración, forma farmacéutica
- **Diferencias:** ATC profundo diferente, DeepSeek reduce confianza por falta de fuentes multimodales
- **Observación:** DeepSeek justifica explícitamente la reducción de confianza

#### 3. Testo-Mix 250mg/ml 10 ampollas (EAN: 900000000018)
- **Scores:** GLM=85, DeepSeek=75 (diferencia: 10)
- **Confianza:** GLM=5/5, DeepSeek=3/5
- **Coincidencias:** Ninguna en dominio/categoría/subcategoría
- **Diferencias M ayores:**
  - Dominio/Categoría: GLM clasifica como hormonal (G03B), DeepSeek como esteroide anabólico (A14A)
  - ATC: GLM=G03BA03, DeepSeek=A14AA01
  - Genérico: GLM=1, DeepSeek=0
  - Requiere Recipe: GLM=1, DeepSeek=0
- **Observación:** DeepSeek marca principios activo y ATC profundo como baja confianza y genera alerta sobre esteroide anabólico

---

## Conclusiones sobre Calidad de DeepSeek

### Fortalezas

1. **Análisis Detallado y Transparente:**
   - Razonamientos específicos que explican la lógica de clasificación
   - Identifica claramente fuentes de información y limitaciones
   - Documenta atributos con baja confianza

2. **Manejo de Incertidumbre:**
   - Ajusta el nivel de confianza según la calidad de información disponible
   - No asigna confianza alta cuando falta verificación
   - Genera alertas de auditoría para productos problemáticos

3. **Consistencia en Clasificación:**
   - Usa taxonomía ATC consistentemente
   - Mantiene estructura jerárquica dominio→categoría→subcategoría

4. **Transparencia de Costos:**
   - Registra tokens de entrada y salida
   - Calcula costos detallados
   - Permite auditoría de uso de recursos

### Áreas de Mejora

1. **Dependencia de Fuentes Externas:**
   - Varios productos muestran baja confianza por falta de imágenes o contexto web
   - Podría beneficiarse de integración con bases de datos farmacéuticas

2. **Inconsistencias en Categorización:**
   - Algunos productos (Testo-Mix) muestran incertidumbre en clasificación taxonómica
   - Necesidad de mejorar coincidencia con catálogo taxonómico activo

3. **Manejo de Productos con Identidad Incierta:**
   - Productos como KOLNASI y PENASTIM muestran dificultad para identificar principio activo
   - Podría requerir bases de datos adicionales de nombres comerciales

---

## Recomendaciones

1. **Para DeepSeek:**
   - Integrar bases de datos farmacéuticas para mejorar identificación de principios activos
   - Implementar búsqueda web contextual cuando no hay imágenes disponibles
   - Desarrollar módulo de aprendizaje de nombres comerciales comunes

2. **Para el Sistema:**
   - Implementar validación cruzada entre múltiples modelos
   - Crear proceso de enriquecimiento con fuentes externas confiables
   - Establecer protocolos para productos de alta incertidumbre

3. **Para Auditoría:**
   - Priorizar revisión de productos con baja confianza (nivel ≤ 3)
   - Verificar manualmente productos con alertas de auditoría
   - Revisar productos clasificados como genérico cuando podrían ser de marca

---

## Archivos Generados

- **Excel:** `scratch/comparativa_glm_vs_deepseek.xlsx`
  - Hoja "Productos Coincidentes": Tabla comparativa lado a lado
  - Hoja "Resumen": Métricas clave
  - Hoja "Diferencias": Análisis de discrepancias por producto
  - Hoja "Análisis Razonamiento": Razonamiento detallado de ambos modelos

- **Markdown:** `informe_comparativa_glm_vs_deepseek.md` (este archivo)

---

**Nota:** Esta comparación es informativa pero no concluyente sobre la calidad real de GLM-4.7 debido a la naturaleza simulada de sus datos. Para una comparación real, se requeriría acceso a la API de GLM-4.7.
"""

# Write markdown file
with open(markdown_file, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"\n✅ Markdown report created: {markdown_file}")

print("\n📊 Key Insights:")
print(f"   - GLM-4.7 (simulado) siempre asigna alta confianza (4-5/5)")
print(f"   - DeepSeek (real) ajusta confianza según calidad de datos (3-5/5)")
print(f"   - DeepSeek genera alertas de auditoría y lista atributos de baja confianza")
print(f"   - Razonamientos de DeepSeek son más detallados y específicos")
print(f"   - Costo promedio por producto DeepSeek: ${df_comparacion['DS_Costo_Total'].mean():.6f}")