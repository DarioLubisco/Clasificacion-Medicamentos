# Comparativa: GLM-4.7 (Simulado) vs DeepSeek V4 Flash (Real)

**Fecha:** 2026-07-01  
**Productos comparados:** 3

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
| Total Productos Comparados | 3 |
| Promedio Score GLM-4.7 (Simulado) | 85.0 |
| Promedio Score DeepSeek (Real) | 73.3 |
| Diferencia Promedio Scores | 11.7 |
| Promedio Confianza GLM-4.7 (Simulado) | 4.7/5 |
| Promedio Confianza DeepSeek (Real) | 4.0/5 |
| Total Costo DeepSeek | $0.013429 |
| Promedio Tokens In DeepSeek | 29663 |
| Promedio Tokens Out DeepSeek | 2311 |
| Productos con baja confianza DeepSeek | 1 |

---

## Análisis Detallado por Producto


### EAN: 900000000001 - Diosmina 450 mg y Hesperidina 50 mg en 10 tabletas de Drotafarma.

#### Comparación de Scores
- **GLM-4.7 (Simulado):** 90/100
- **DeepSeek (Real):** 75/100
- **Diferencia:** 15 puntos

#### Nivel de Confianza
- **GLM-4.7:** 4/5
- **DeepSeek:** 5/5

#### Atributos Clave

| Atributo | GLM-4.7 (Simulado) | DeepSeek (Real) | ¿Coinciden? |
|----------|-------------------|-----------------|-------------|
| Dominio | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO | ✅ |
| Categoría | FLEBOLOGICOS | C05 - VASOPROTECTORES | ❌ |
| Subcategoría | DIOSMINA | [C05C] AGENTES ESTABILIZADORES CAPILARES | ❌ |
| Principio Activo | Diosmina; Hesperidina | Diosmina; Hesperidina | ✅ |
| Concentración | 450 mg; 50 mg | 450 mg; 50 mg | ✅ |
| Forma Farmacéutica | Tableta | Tableta | ✅ |
| Código ATC | C05C | C05C | ✅ |
| ATC Profundo | C05CA53 | C05CA53 | ✅ |

#### Razonamiento

**GLM-4.7 (Simulado):**
> Análisis basado en descripción: Diosmina 450 mg y Hesperidina 50 mg en 10 tabletas. Clasificación según características farmacológicas.

**DeepSeek (Real):**
> Producto medicamentoso alopático (flavonoides venotónicos). Descripción única indica 'Diosmina 450 mg y Hesperidina 50 mg en 10 tabletas'. Se interpreta como 10 tabletas, cada una con 450 mg de diosmina y 50 mg de hesperidina. Empaque en caja (Regla A). Fabricante Drotafarma en la descripción....

#### Análisis de DeepSeek

- **Atributos con Baja Confianza:** Ninguno
- **Alertas de Auditoría:** Ninguna
- **Tokens In:** 29,667
- **Tokens Out:** 2,311
- **Costo:** $0.004477

---


### EAN: 900000000014 - Heparina 250 UI/g gel 30g

#### Comparación de Scores
- **GLM-4.7 (Simulado):** 80/100
- **DeepSeek (Real):** 70/100
- **Diferencia:** 10 puntos

#### Nivel de Confianza
- **GLM-4.7:** 5/5
- **DeepSeek:** 4/5

#### Atributos Clave

| Atributo | GLM-4.7 (Simulado) | DeepSeek (Real) | ¿Coinciden? |
|----------|-------------------|-----------------|-------------|
| Dominio | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO | ✅ |
| Categoría | ANTITROMBOTICOS | C05 - VASOPROTECTORES | ❌ |
| Subcategoría | HEPARINAS_TOPICAS | [C05B] TERAPIA ANTIVARICOSA | ❌ |
| Principio Activo | Heparina | Heparina sódica | ❌ |
| Concentración | 250 UI/g | 250 UI/g | ✅ |
| Forma Farmacéutica | Gel | Gel | ✅ |
| Código ATC | C05B | C05B | ✅ |
| ATC Profundo | C05BA53 | C05BA03 | ❌ |

#### Razonamiento

**GLM-4.7 (Simulado):**
> Análisis basado en descripción: Heparina 250 UI/g gel 30g. Clasificación según características farmacológicas.

**DeepSeek (Real):**
> Medicamento alopático tópico. Única fuente: descripción EAN. Sin imágenes ni contexto web para corroborar. Se asume que los datos son correctos. Concentración 250 UI/g por gramo de gel. Tubo único de 30g (Regla B). Taxonomía asignada a C05B (Terapia Antivaricosa) por ser la más cercana para heparina tópica en el catálogo. Confianza global reducida a 4 por falta de fuentes de verificación multimodal....

#### Análisis de DeepSeek

- **Atributos con Baja Confianza:** Ninguno
- **Alertas de Auditoría:** Ninguna
- **Tokens In:** 29,654
- **Tokens Out:** 1,859
- **Costo:** $0.004412

---


### EAN: 900000000018 - Testo-Mix 250mg/ml, 10 ampollas de 1ml, inyectable intramuscular.

#### Comparación de Scores
- **GLM-4.7 (Simulado):** 85/100
- **DeepSeek (Real):** 75/100
- **Diferencia:** 10 puntos

#### Nivel de Confianza
- **GLM-4.7:** 5/5
- **DeepSeek:** 3/5

#### Atributos Clave

| Atributo | GLM-4.7 (Simulado) | DeepSeek (Real) | ¿Coinciden? |
|----------|-------------------|-----------------|-------------|
| Dominio | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO | ✅ |
| Categoría | HORMONALES | A14 - AGENTES ANABÓLICOS PARA USO SISTÉMICO | ❌ |
| Subcategoría | TESTOSTERONA | [A14A] ESTEROIDES ANABÓLICOS | ❌ |
| Principio Activo | Testosterona | Testosterona | ✅ |
| Concentración | 250 mg/ml | 250 mg/ml | ✅ |
| Forma Farmacéutica | Solución inyectable | Solución inyectable | ✅ |
| Código ATC | G03B | A14A | ❌ |
| ATC Profundo | G03BA03 | A14AA01 | ❌ |

#### Razonamiento

**GLM-4.7 (Simulado):**
> Análisis basado en descripción: Testo-Mix 250mg/ml, 10 ampollas de 1ml. Clasificación según características farmacológicas.

**DeepSeek (Real):**
> Medicamento alopático inyectable. Descripción indica 'Testo-Mix', interpretado como testosterona o éster. Concentración 250mg/ml, 10 ampollas de 1ml. Empaque: caja con 10 ampollas (Regla A). Sin fuentes web ni imágenes válidas; todos los datos provienen de la descripción original. Taxonomía: A14A - Esteroides anabólicos. ATC profundo inferido A14AA01 (testosterona). Confianza reducida por falta de verificación de principio activo....

#### Análisis de DeepSeek

- **Atributos con Baja Confianza:** principio_activo, codigo_atc_profundo
- **Alertas de Auditoría:** Principio activo no confirmado explícitamente; se asume testosterona. Producto de uso restringido (esteroide anabólico) pero no clasificado como psicotrópico/estupefaciente.
- **Tokens In:** 29,668
- **Tokens Out:** 2,762
- **Costo:** $0.004540

---


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
