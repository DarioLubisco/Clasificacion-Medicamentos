# Análisis Comparativo de Atributos Extraídos
En esta tabla detallamos qué extrajo cada modelo para cada uno de los 10 productos.

## Producto: YONALIN 4MG/ML X15ML SOL GOTAS BIOTECH (EAN: 7591243856743)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | [] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | R05D | R05D |
| **codigo_atc_profundo** | R05DA09 | R05DA09 |
| **concentracion** | 4 mg/ml | 4 mg/ml |
| **confianza_nivel** | 5 | 5 |
| **confianza_razonamiento** | dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5. Todas las fuentes coinciden sin contradicciones. Nivel global = 5. | dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5. Todas las fuentes coinciden sin discrepancias. Nivel global = 5. |
| **contenido_neto** | 15 | 15 |
| **contenido_neto_unidad_Des** | ml | ml |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | Biotech |
| **forma_farmaceutica** | Solución Oral | Solución Oral Gotas |
| **generico** | 0 | 0 |
| **marca** | Yonalin | Yonalin |
| **origen** | None | None |
| **principio_activo** | Dextrometorfano | Dextrometorfano |
| **razonamiento** | Producto identificado como Yonalin, un antitusivo pediátrico en solución oral gotas. El principio activo es Dextrometorfano (bromhidrato) a concentración de 4 mg/mL, en frasco de 15 mL. La información de las fuentes web (Farmadon, Farmacia Santa Bárbara) y la imagen OCR coinciden plenamente: nombre, laboratorio Biotech, concentración, presentación y uso pediátrico. No hay discrepancias. Se clasifica en el catálogo como MEDICAMENTO_ALOPATICO > R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO > [R05D] ANTITUSIVOS, EXCL. COMBINACIONES CON EXPECTORANTES. Aplica Regla B (frasco único): cantidad_presentacion=1, contenido_neto=15 ml, volumen_unidad=15 ml. | Producto identificado como Dextrometorfano (Bromhidrato) en solución oral gotas. Las tres fuentes (descripción original, texto web de Farmadon y Santa Bárbara, y OCR de la imagen 1) coinciden en todos los datos clave: principio activo, concentración (4 mg/mL), contenido neto (15 mL), fabricante (Biotech) y uso pediátrico. La imagen 2 corresponde a un producto diferente (Yonalat Jarabe) y fue descartada. Aplica Regla B (frasco único). |
| **segmento_etario** | PEDIATRICO | PEDIATRICO |
| **subcategoria** | [R05D] ANTITUSIVOS, EXCL. COMBINACIONES CON EXPECTORANTES | [R05D] ANTITUSIVOS, EXCL. COMBINACIONES CON EXPECTORANTES |
| **volumen_unidad** | 15 | 15 |
| **volumen_unidad_medida** | ml | ml |

## Producto: DIGLET 200UI GOTAS X20ML BANANA LETI (EAN: 7591585119100)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | [] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | VITAMINAS | VITAMINAS |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | None | None |
| **codigo_atc_profundo** | A11CC05 | A11CC05 |
| **concentracion** | 200 UI | 200 UI |
| **confianza_nivel** | 5 | 5 |
| **confianza_razonamiento** | Todas las fuentes coinciden sin discrepancias. dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5. Nivel global = 5. | dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5, contenido_neto=5. Todas las fuentes coinciden. Nivel global = 5. |
| **contenido_neto** | 20 | 20 |
| **contenido_neto_unidad_Des** | ml | ml |
| **dominio** | SUPLEMENTO_VITAMINICO | SUPLEMENTO_VITAMINICO |
| **fabricante** | LETI | LETI |
| **forma_farmaceutica** | Solución Oral Gotas | Solución Oral Gotas |
| **generico** | 0 | 0 |
| **marca** | Diglet | Diglet |
| **origen** | None | None |
| **principio_activo** | Vitamina D3 | Colecalciferol (Vitamina D3) |
| **razonamiento** | Vitamina D3 (Colecalciferol) en solución oral gotas. La evidencia de la imagen OCR ('DIGLET Vitamina D3 200UI Solución Oral Gotas 20mL LETI'), la descripción original y las fuentes web (Farmadon, Santa Bárbara) es unánime. No hay discrepancias. Se clasifica como SUPLEMENTO_VITAMINICO en la subcategoría VITAMINA D del catálogo. No existe [código ATC] en esta subcategoría, pero se infiere el ATC profundo (A11CC05). Al ser un frasco único, aplica Regla B (cantidad_presentacion=1, contenido_neto=20). | Producto identificado como suplemento de Vitamina D3 (Colecalciferol) en solución oral (gotas). La concentración es de 200 UI por unidad de dosificación, y el contenido neto del frasco es de 20 ml. Aplica Regla B (frasco único). Fabricante LETI confirmado por OCR de imagen y fuentes web. No se encontró evidencia explícita del país de origen ni del segmento etario. Todas las fuentes (descripción, web, OCR) son consistentes sin discrepancias. |
| **segmento_etario** | NO_DEFINIDO | NO_DEFINIDO |
| **subcategoria** | VITAMINA D | VITAMINA D |
| **volumen_unidad** | 20 | 20 |
| **volumen_unidad_medida** | ml | ml |

## Producto: LITONATE CREMA X15 GR BIOTECH (EAN: 7591243830705)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | ['dominio'] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | D03 - PREPARADOS PARA EL TRATAMIENTO DE HERIDAS Y ÚLCERAS | D03 - PREPARADOS PARA EL TRATAMIENTO DE HERIDAS Y ÚLCERAS |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | D03A | D03A |
| **codigo_atc_profundo** | D03AX13 | D03AX03 |
| **concentracion** | 1 % | 1% |
| **confianza_nivel** | 5 | 4 |
| **confianza_razonamiento** | dominio=5, principio_activo=5, concentracion=5, contenido_neto=5. Sin discrepancias. Nivel global = 5. | dominio=4 (No es un medicamento alopático en sentido estricto, pero es la categoría del catálogo que mejor se ajusta a su presentación y uso, al no existir una subcategoría fitoterapéutica tópica), principio_activo=5, concentracion=5, cantidad_presentacion=5. Nivel global calculado como el mínimo = 4. |
| **contenido_neto** | 15 | 15 |
| **contenido_neto_unidad_Des** | g | g |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | BIOTECH |
| **forma_farmaceutica** | Crema | Crema |
| **generico** | 0 | 0 |
| **marca** | Litonate | LITONATE |
| **origen** | None | None |
| **principio_activo** | Centella Asiática | Centella Asiática (extracto) |
| **razonamiento** | Producto identificado como Litonate crema de Centella Asiática al 1%, fabricado por Biotech. Presentación en tubo de 15g. Clasificado como MEDICAMENTO_ALOPATICO dentro de CICATRIZANTES según taxonomía activa, corroborado por ser comercializado como tratamientos para cicatrices y heridas. No se reportan discrepancias entre fuentes: la imagen OCR y los contextos web coinciden plenamente en principio activo, concentración, fabricante y presentación. | Producto a base de Centella Asiática (extracto fitoterapéutico) en crema al 1%, presentación de 15g. Se clasifica como MEDICAMENTO_ALOPATICO en la subcategoría [D03A] CICATRIZANTES, ya que es la opción más precisa del catálogo para una crema cicatrizante de uso tópico con una concentración definida. La fuente web 1 confirma la composición 'Centella Asiática 1% Crema X 15Gr'. La imagen OCR confirma el laboratorio Biotech. El código ATC se extrae de los corchetes de la subcategoría. El ATC profundo D03AX03 corresponde a los triterpenos de Centella Asiática utilizados como cicatrizantes. No se reporta país de origen ni segmento etario. |
| **segmento_etario** | NO_DEFINIDO | NO_DEFINIDO |
| **subcategoria** | [D03A] CICATRIZANTES | [D03A] CICATRIZANTES |
| **volumen_unidad** | 15 | 15 |
| **volumen_unidad_medida** | g | g |

## Producto: GYNOMET CREMA VAGx40g (EAN: 7591585119131)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | ['fabricante'] |
| **cantidad_presentacion** | 7 | 1 |
| **categoria** | G01 - ANTIINFECCIOSOS Y ANTISÉPTICOS GINECOLÓGICOS | G01 - ANTIINFECCIOSOS Y ANTISÉPTICOS GINECOLÓGICOS |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | G01A | G01A |
| **codigo_atc_profundo** | G01AF20 | G01AF20 |
| **concentracion** | 15% - 4% | 15 %; 4 % |
| **confianza_nivel** | 5 | 4 |
| **confianza_razonamiento** | dominio=5, principio_activo=5 (Metronidazol + Miconazol confirmado en web 1, web 3, OCR 2), concentración=5 (15% - 4% confirmado en web 3 y OCR 2), cantidad_presentacion=5 (7 aplicadores confirmado en web 1, web 3 y OCR 2). Todas las fuentes relevantes coinciden. Nivel global = 5. | dominio=5 (medicamento alopático claro), principio_activo=5 (explícito en web e imagen), concentracion=5 (explícito en imagen OCR), cantidad_presentacion=5 (1 tubo), fabricante=4 (solo una fuente web lo menciona, no en imagen). Nivel global = min(5,5,5,5,4) = 4. |
| **contenido_neto** | 1 | 40 |
| **contenido_neto_unidad_Des** | Caja | g |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Letifem | Letifem |
| **forma_farmaceutica** | Crema Vaginal | Crema Vaginal |
| **generico** | 0 | 0 |
| **marca** | Gynomet | Gynomet |
| **origen** | None | None |
| **principio_activo** | Metronidazol; Miconazol | Metronidazol; Miconazol |
| **razonamiento** | Producto identificado como Gynomet, una crema vaginal de combinación (Metronidazol + Miconazol). La descripción original (EAN) indica 'GYNOMET CREMA VAGx40g'. La fuente web 1 (Farmadon) confirma el nombre, principios activos, concentración (15% Miconazol / 4% Metronidazol según fuente 3 y OCR), presentación (40g crema + 7 aplicadores/cánulas) y fabricante (Letifem). La fuente web 3 (FarmaBien) y la imagen OCR 2 confirman la concentración '15%-4%' y el contenido de 'Tubo de 40 g + 7 cánulas vaginales'. La imagen 1 (OCR) corresponde a otro producto (VAGILEN R) y se descarta para este EAN. No hay discrepancias entre las fuentes relevantes (texto web, OCR imagen 2 y descripción original). Al ser un medicamento tópico vaginal con aplicadores, aplica la Regla A: el empaque principal es una caja que contiene 1 tubo (40g) y 7 aplicadores. La concentración se reporta como '15% - 4%' (porcentaje de cada principio activo en la crema). La taxonomía corresponde a MEDICAMENTO_ALOPATICO, categoría G01 (Antiinfecciosos y antisépticos ginecológicos), subcategoría [G01A] (excluyendo combinaciones con corticosteroides). | Producto identificado como Gynomet, una crema vaginal combinada de Metronidazol y Miconazol. La concentración es 15% Metronidazol y 4% Miconazol, confirmada por OCR de imagen. El contenido neto es un tubo de 40g. Incluye 7 cánulas vaginales desechables como accesorios. El fabricante Letifem se extrajo de la fuente web Farmadon. Se clasifica en la categoría ginecológica de antiinfecciosos tópicos. Aplica Regla B (tubo único). |
| **segmento_etario** | ADULTO | ADULTO |
| **subcategoria** | [G01A] ANTIINFECCIOSOS Y ANTISÉPTICOS, EXCL. COMBINACIONES CON CORTICOSTEROIDES | [G01A] ANTIINFECCIOSOS Y ANTISÉPTICOS, EXCL. COMBINACIONES CON CORTICOSTEROIDES |
| **volumen_unidad** | 40 | 40 |
| **volumen_unidad_medida** | g | g |

## Producto: NEUROMIX 30 TAB LETI (EAN: 7591585213365)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | [] |
| **cantidad_presentacion** | 30 | 30 |
| **categoria** | A11 - VITAMINAS | VITAMINAS |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | A11E | None |
| **codigo_atc_profundo** | A11EA | None |
| **concentracion** | 100 mg; 100 mg; 5 mg | 100 mg; 100 mg; 5 mg |
| **confianza_nivel** | 5 | 5 |
| **confianza_razonamiento** | dominio=5, principio_activo=5, concentracion=5 (extraída de OCR del empaque), cantidad_presentacion=5 (confirmada en múltiples fuentes), taxonomía=5. Sin discrepancias. Nivel global = 5. | dominio=5 (evidencia contundente en texto e imagen), principio_activo=5 (Complejo B con componentes específicos detallados en OCR), concentracion=5 (explícito en imagen: 100 mg B1; 100 mg B6; 5 mg B12 por comprimido), cantidad_presentacion=5 (30 comprimidos consistente en todas las fuentes). Sin discrepancias. Nivel global = 5. |
| **contenido_neto** | 1 | 1 |
| **contenido_neto_unidad_Des** | Caja | Caja |
| **dominio** | MEDICAMENTO_ALOPATICO | SUPLEMENTO_VITAMINICO |
| **fabricante** | Leti | LETI |
| **forma_farmaceutica** | Comprimido recubierto | Comprimido recubierto |
| **generico** | 0 | 0 |
| **marca** | Neuromix | NEUROMIX |
| **origen** | None | None |
| **principio_activo** | Complejo B (Tiamina clorhidrato, Piridoxina clorhidrato, Cianocobalamina) | Tiamina; Piridoxina; Cianocobalamina |
| **razonamiento** | Producto vitamínico que contiene combinación de vitaminas B1, B6 y B12, presentado como comprimidos recubiertos. La descripción original indica '30 TAB', y los contextos web de farmacias venezolanas (Farmadon, Farmacia Santa Barbara) confirman presentación de 30 comprimidos, fabricante Leti. La imagen del empaque (OCR) detalla concentraciones exactas: B1 100 mg, B6 100 mg, B12 5 mg. Posee registro sanitario venezolano (E.F.42.160/19), lo que lo clasifica como medicamento alopático dentro del grupo A11 (Vitaminas), específicamente complejo B. Aplica Regla A: caja con 30 comprimidos, contenido neto = 1, cantidad = 30. No se declara país de origen ni segmento etario explícito. Todas las fuentes son consistentes, sin discrepancias. | Producto identificado como Neuromix Complejo B de Leti en presentación de 30 comprimidos recubiertos. Es un suplemento vitamínico que contiene Vitamina B1 (100 mg), B6 (100 mg) y B12 (5 mg) por comprimido, según OCR de la imagen del empaque. Las fuentes web (Farmadon, Gran Feria PZO, Farmacia Santa Bárbara) confirman la descripción y el fabricante Leti. Aplica Regla A (caja con 30 unidades). El catálogo activo tiene la combinación exacta SUPLEMENTO_VITAMINICO > VITAMINAS > COMPLEJO B. No hay código ATC en corchetes para esta subcategoría, por lo que codigo_atc es null. codigo_atc_profundo se asigna como null por ser una combinación no estandarizada en nivel 5. Segmento etario no especificado explícitamente; se deja null. Origen no indicado. Sin discrepancias entre fuentes. |
| **segmento_etario** | NO_DEFINIDO | NO_DEFINIDO |
| **subcategoria** | [A11E] COMPLEJO VITAMÍNICO B, INCL. COMBINACIONES | COMPLEJO B |
| **volumen_unidad** | None | None |
| **volumen_unidad_medida** | None | None |

## Producto: FLENOX JARABE ADU 120ML (EAN: 7591243817829)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | ['concentracion'] | [] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | R05C | R05C |
| **codigo_atc_profundo** | R05CB06 | R05CB06 |
| **concentracion** | 30 mg/5 ml | 30 mg/5 ml |
| **confianza_nivel** | 3 | 4 |
| **confianza_razonamiento** | dominio=5 (medicamento alopático mucolítico, encaja exactamente en el catálogo), principio_activo=5 (Ambroxol confirmado en todas las fuentes), concentracion=3 (Imagen 1 OCR muestra 15 mg/5 ml pediátrico, pero descripción EAN y webs indican 30 mg/5 ml adulto; se prioriza EAN+webs según regla), cantidad_presentacion=5 (frasco único confirmado por webs e imagen). Nivel global = min(5,5,3,5) = 3. | dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5, fabricante=5 (visible en web). La única discrepancia es que la imagen OCR (Imagen 3) no es del producto exacto FLENOX sino de un genérico. Esto no genera conflicto, pero reduce la certeza visual directa. Nivel global = 4. |
| **contenido_neto** | 120 | 120 |
| **contenido_neto_unidad_Des** | ml | ml |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | Biotech |
| **forma_farmaceutica** | Jarabe | Jarabe |
| **generico** | 0 | 0 |
| **marca** | Flenox | FLENOX |
| **origen** | None | None |
| **principio_activo** | Ambroxol | Ambroxol |
| **razonamiento** | El producto se identifica como Flenox, un jarabe mucolítico a base de Ambroxol. La descripción original indica 'ADU' (adulto) y 120 ml. Las fuentes web confirman que Flenox Adulto contiene Ambroxol 30 mg/5 ml en un frasco de 120 ml, fabricado por Biotech. Sin embargo, una de las imágenes OCR procesadas muestra un producto de Ambroxol 15 mg/5 ml pediátrico de Delter, lo cual difiere en concentración y segmento etario. Otra imagen muestra Ambroxol 30 mg/5 ml de Comed International, sin confirmar que sea Flenox. Según la regla de discrepancia de concentración entre imagen y EAN, se toma como verdad de referencia la información de la descripción original junto con las fuentes web (30 mg/5 ml), se documenta el conflicto y se reduce la confianza. La forma farmacéutica es jarabe, presentación en frasco único (Regla B). No se encuentra país de origen explícito. | Se identifica como Ambroxol jarabe 30 mg/5 ml para adultos. La descripción web y el contexto web confirman el principio activo, concentración y segmento etario. La imagen OCR de un producto genérico similar es coherente pero no corresponde exactamente al lote FLENOX de Biotech. Se aplica la Regla B (frasco único) para el cálculo de presentación. El catálogo activo no tiene una subcategoría 'Mucolíticos' explícita, por lo que se elige '[R05C] EXPECTORANTES' como la subcategoría más adecuada dentro de la categoría de preparados para la tos y el resfriado. |
| **segmento_etario** | ADULTO | ADULTO |
| **subcategoria** | [R05C] EXPECTORANTES, EXCL. COMBINACIONES CON ANTITUSIVOS | [R05C] EXPECTORANTES, EXCL. COMBINACIONES CON ANTITUSIVOS |
| **volumen_unidad** | 120 | 120 |
| **volumen_unidad_medida** | ml | ml |

## Producto: LISIN-BE JARABE 120ML (EAN: 7591243830507)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | Suplemento alimenticio sin composición declarada en las fuentes. No se puede clasificar en el catálogo activo. | N/A |
| **atributos_baja_confianza** | ['dominio', 'categoria', 'subcategoria', 'principio_activo', 'concentracion'] | N/A |
| **cantidad_presentacion** | 1 | N/A |
| **categoria** | None | N/A |
| **clasificacion_insumo_Des** | None | N/A |
| **codigo_atc** | None | N/A |
| **codigo_atc_profundo** | None | N/A |
| **concentracion** | None | N/A |
| **confianza_nivel** | 2 | N/A |
| **confianza_razonamiento** | dominio=1 (no se puede clasificar sin composición), principio_activo=1 (desconocido), concentracion=1 (no reportada), cantidad_presentacion=5 (explícito: 1 frasco). Nivel global = min(1,1,1,5) = 1, pero se ajusta a 2 porque la identidad como suplemento es clara aunque no su subcategoría. Se asigna 2 (BAJA) por datos insuficientes para la taxonomía. | N/A |
| **contenido_neto** | 120 | N/A |
| **contenido_neto_unidad_Des** | ml | N/A |
| **dominio** | None | N/A |
| **fabricante** | Biotech | N/A |
| **forma_farmaceutica** | Jarabe | N/A |
| **generico** | 1 | N/A |
| **marca** | Lisin-Be | N/A |
| **origen** | None | N/A |
| **principio_activo** | None | N/A |
| **razonamiento** | Producto identificado como suplemento alimenticio líquido (jarabe) de 120 ml, fabricado por Biotech. Las fuentes web lo describen como 'Alimento Liquido' o 'Suplem Aliment', sin detallar su composición nutricional. La fuente 4 lo lista en la categoría 'Vitaminas', pero no especifica qué vitaminas o principios activos contiene. Ante la ausencia de información explícita sobre su formulación, no es posible asignar una subcategoría exacta del catálogo activo (que requiere subcategorías como COMPLEJO B, MULTIVITAMINICOS ADULTO, etc.). Por tanto, se asigna null a dominio, categoria y subcategoria. El resto de atributos físicos se extraen de la descripción: jarabe 120 ml, envase único (Regla B). El fabricante Biotech aparece en las fuentes 3 y 4. La presentación se declara como 'Generico', por lo que generico=1. No hay información de país de origen ni segmento etario. | N/A |
| **segmento_etario** | NO_DEFINIDO | N/A |
| **subcategoria** | None | N/A |
| **volumen_unidad** | 120 | N/A |
| **volumen_unidad_medida** | ml | N/A |

## Producto: FLENOX JARABE PED 120ML (EAN: 7591243817782)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | [] | [] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO | R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | R05C | R05C |
| **codigo_atc_profundo** | R05CB06 | R05CB02 |
| **concentracion** | 15 mg/5 ml | 15 mg/5 ml |
| **confianza_nivel** | 5 | 5 |
| **confianza_razonamiento** | Atributo dominio=5 (medicamento alopático, evidencia explícita), principio_activo=5 (Ambroxol confirmado en imagen y web), concentracion=5 (15 mg/5 ml en todas las fuentes), cantidad_presentacion=5 (frasco único, 1). Sin discrepancias entre fuentes relevantes. La única posible inconsistencia (marca 'Genérico' en TantoVital) es un contexto de listado, no aplica al producto real. Confianza global = 5. | Todos los atributos críticos (dominio, principio_activo, concentracion, cantidad_presentacion) obtienen un puntaje individual de 5 (evidencia explícita y consistente en múltiples fuentes). No se detectaron discrepancias. El nivel global es el mínimo, que es 5. |
| **contenido_neto** | 120 | 120 |
| **contenido_neto_unidad_Des** | ml | ml |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | BIOTECH |
| **forma_farmaceutica** | Jarabe | Jarabe |
| **generico** | 0 | 0 |
| **marca** | Flenox | Flenox |
| **origen** | None | None |
| **principio_activo** | Ambroxol | Clorhidrato de Ambroxol |
| **razonamiento** | Producto identificado como Flenox jarabe pediátrico de Ambroxol 15 mg/5 ml, presentación 120 ml, fabricante Biotech. La imagen OCR del empaque y las fuentes web (Farmadon, Gran Feria PZO) corroboran todos los detalles. La fuente TantoVital etiqueta la marca como 'Generico' en su listado, pero es una comparativa de similares genéricos, no afecta la identidad del producto real que es de marca. Taxonomía: expectorante mucolítico, se asigna a R05C. Aplica Regla B de contenido neto por ser envase único. | Producto identificado como Flenox, un jarabe pediátrico a base de Clorhidrato de Ambroxol. La concentración es 15 mg por cada 5 ml (dosis), el contenido total del frasco es de 120 ml. Todas las fuentes web (Farmadon, GranFeria, TantoVital) y la imagen OCR coinciden en principio activo, concentración, forma farmacéutica y laboratorio fabricante (Biotech). No hay discrepancias entre las fuentes. Aplica Regla B (Frasco único). |
| **segmento_etario** | PEDIATRICO | PEDIATRICO |
| **subcategoria** | [R05C] EXPECTORANTES, EXCL. COMBINACIONES CON ANTITUSIVOS | [R05C] EXPECTORANTES, EXCL. COMBINACIONES CON ANTITUSIVOS |
| **volumen_unidad** | 120 | 120 |
| **volumen_unidad_medida** | ml | ml |

## Producto: ERILON 0.1% CREMA 15G (EAN: 7591243815801)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | None | None |
| **atributos_baja_confianza** | ['marca'] | [] |
| **cantidad_presentacion** | 1 | 1 |
| **categoria** | D07 - CORTICOSTEROIDES, PREPARADOS DERMATOLÓGICOS | D07 - CORTICOSTEROIDES, PREPARADOS DERMATOLÓGICOS |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | D07A | D07A |
| **codigo_atc_profundo** | D07AB08 | D07AB08 |
| **concentracion** | 0.1% | 1 mg/g |
| **confianza_nivel** | 4 | 5 |
| **confianza_razonamiento** | dominio=5, principio_activo=5, concentracion=5, fabricante=5 (Biotech claramente visible y respaldado), marca=4 (una fuente 2 indica 'Generico', pero la imagen (Imagen 2) y las fuentes 1 y 3 confirman 'Erilón'; se descarta 'Generico' como error). Nivel global: mínimo de puntajes = 4. | dominio=5, principio_activo=5, concentracion=5, forma_farmaceutica=5, cantidad_presentacion=5, contenido_neto=5, fabricante=5. No se detectaron discrepancias entre las fuentes (descripción, web e imagen). Todas las fuentes coinciden en todos los atributos críticos. Nivel global = min(5,5,5,5,5,5,5) = 5. |
| **contenido_neto** | 15 | 15 |
| **contenido_neto_unidad_Des** | g | g |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | Biotech |
| **forma_farmaceutica** | Crema | Crema |
| **generico** | 0 | 0 |
| **marca** | Erilón | Erilon |
| **origen** | None | None |
| **principio_activo** | Desonida | Desonida |
| **razonamiento** | Medicamento corticosteroide tópico con Desonida. La imagen del producto (fuente visual) y las Fuentes Web 1 y 3 confirman Desonida 0.1%, crema, 15g, fabricante Biotech. Una de las fuentes web sugiere 'Generico' como marca, lo cual contradice la evidencia visual y las otras fuentes que muestran 'Erilón' como nombre comercial. Se mantiene Erilón como marca y Biotech como fabricante. Al ser un tubo único de 15g, aplica Regla B. | El producto es Erilon, una crema dermatológica que contiene Desonida al 0.1% como corticosteroide tópico. La descripción original, las tres fuentes web (Farmadon, Tantovital, Farmacia Santa Barbara) y la imagen OCR (Imagen 2) confirman unánimemente el principio activo (Desonida), la concentración (0.1%), la forma farmacéutica (Crema), el contenido neto (15g) y el fabricante (Biotech). No existen discrepancias entre las fuentes. Se aplica la Regla B (envase único: tubo de crema). La concentración se expresa como '1 mg/g' (equivalente a 0.1%) para ajustarse a la definición de concentración por unidad de dosificación (gramo de crema). El segmento etario no está especificado en ninguna fuente, por lo que se asigna null. El origen del laboratorio Biotech no está explícito, por lo que se asigna null. 'Erilon' es una marca comercial, no un genérico. |
| **segmento_etario** | NO_DEFINIDO | NO_DEFINIDO |
| **subcategoria** | [D07A] CORTICOSTEROIDES SOLOS | [D07A] CORTICOSTEROIDES SOLOS |
| **volumen_unidad** | 15 | 15 |
| **volumen_unidad_medida** | g | g |

## Producto: ARESAN 40 MG X 10 TAB (EAN: 7591243802108)
| Atributo | DeepSeek Pro | DeepSeek Flash |
|---|---|---|
| **alertas_auditoria** | Origen y segmento_etario no especificados en las fuentes. | None |
| **atributos_baja_confianza** | [] | [] |
| **cantidad_presentacion** | 10 | 10 |
| **categoria** | C09 - AGENTES QUE ACTÚAN SOBRE EL SISTEMA RENINA-ANGIOTENSINA | C09 - AGENTES QUE ACTÚAN SOBRE EL SISTEMA RENINA-ANGIOTENSINA |
| **clasificacion_insumo_Des** | None | None |
| **codigo_atc** | C09C | C09C |
| **codigo_atc_profundo** | C09CA08 | C09CA08 |
| **concentracion** | 40 mg | 40 mg |
| **confianza_nivel** | 5 | 5 |
| **confianza_razonamiento** | Atributos críticos con puntaje perfecto: dominio=5, principio_activo=5 (Todas las fuentes: Olmesartán), concentracion=5 (Todas las fuentes: 40 mg), cantidad_presentacion=5 (Todas las fuentes: 10 tabletas). Sin discrepancias. Nivel global = min(5,5,5,5) = 5. | Todos los atributos críticos (dominio, principio_activo, concentracion, cantidad_presentacion) tienen evidencia explícita y consistente. Puntajes individuales: dominio=5, principio_activo=5, concentracion=5, cantidad_presentacion=5. Nivel global = min(5,5,5,5)=5. |
| **contenido_neto** | 1 | 1 |
| **contenido_neto_unidad_Des** | Caja | Caja |
| **dominio** | MEDICAMENTO_ALOPATICO | MEDICAMENTO_ALOPATICO |
| **fabricante** | Biotech | Biotech |
| **forma_farmaceutica** | Tableta recubierta | Tableta recubierta |
| **generico** | 0 | 0 |
| **marca** | Aresan | Aresan |
| **origen** | None | None |
| **principio_activo** | Olmesartán | Olmesartán |
| **razonamiento** | Se analiza el producto Aresan. La descripción original 'ARESAN 40 MG X 10 TAB', las 3 fuentes web y la imagen del empaque coinciden plenamente. Principio activo: Olmesartán. Concentración: 40 mg por tableta. Cantidad: 10 tabletas. Fabricante: Biotech (visible en imagen y webs 1 y 3). Marca: Aresan. Al ser una caja con 10 comprimidos, aplica la Regla A: contenido_neto = 1 (Caja), cantidad_presentacion = 10. No se menciona el país de origen, por lo que se asigna null. El segmento etario no se indica explícitamente, por lo tanto, es null según las reglas anti-alucinación. Taxonomía: ARA II, clasificado en 'C09 - AGENTES QUE ACTÚAN SOBRE EL SISTEMA RENINA-ANGIOTENSINA'. ATC de catálogo extraído de los corchetes: C09C. ATC profundo inferido: C09CA08. | Producto identificado como Olmesartán 40 mg tabletas recubiertas, caja con 10 unidades. Las tres fuentes (descripción original, web e imagen OCR) coinciden en principio activo, concentración, cantidad y fabricante (Biotech). No hay discrepancias. Se aplica Regla A (caja con múltiples unidades). |
| **segmento_etario** | NO_DEFINIDO | NO_DEFINIDO |
| **subcategoria** | [C09C] BLOQUEADORES DE LOS RECEPTORES DE ANGIOTENSINA II (ARA II), SIMPLES | [C09C] BLOQUEADORES DE LOS RECEPTORES DE ANGIOTENSINA II (ARA II), SIMPLES |
| **volumen_unidad** | None | None |
| **volumen_unidad_medida** | None | None |
