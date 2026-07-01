# Reporte de Comparación: Texto vs Visión Activa (OCR)
Este reporte analiza el impacto de introducir imágenes y OCR con Gemini Flash en la clasificación de los 20 productos complejos.

| EAN | Descripción | Score Sin Visión | Score Con Visión | Confianza Sin Visión | Confianza Con Visión | Fotos Aprobadas | Cambios Clave |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| 900000000000 | Amoxicilina/Ácido Clavulánico 875 mg/125... | 70 | 70 | 5 | 5 | 0 | Principio Activo: 'Amoxicilina; Ácido Clavulánico' ➔ 'Amoxicilina + Ácido Clavulánico', Forma Farmacéutica: 'Tableta' ➔ 'Comprimido recubierto' |
| 900000000001 | Diosmina 450 mg y Hesperidina 50 mg en 1... | 75 | 75 | 5 | 5 | 3 | Forma Farmacéutica: 'Tableta' ➔ 'Tableta recubierta' |
| 900000000002 | Isospray Plus 0.15%-0.25% solución tópic... | 40 | 90 | 1 | 5 | 3 | **+Principio Activo** (Bencidamina; Cloruro de Cetilpiridinio), **+Concentración** (0.15%-0.25%), **+Laboratorio/Fabricante** (Biotech) |
| 900000000003 | ITRASEC ITRACONAZOL + SECNIDAZOL 12 CÁPS... | 0 | 90 | 1 | 4 | 0 | **+Concentración** (33.33 mg; 166.66 mg), **+Laboratorio/Fabricante** (Kwality Pharmaceuticals Ltd), Marca: 'ITRASEC' ➔ 'Itrasec', **+Reg. Sanitario** (PSI #00001700) |
| 900000000004 | SIGLIPMET 50/500 mg 30 tabletas... | 75 | 90 | 5 | 4 | 2 | Forma Farmacéutica: 'Tableta' ➔ 'Comprimido recubierto' |
| 900000000005 | GABABRIX-B 75 mg/750 mcg 10 cápsulas... | 75 | 80 | 3 | 5 | 2 | Principio Activo: 'Gabapentina; Cianocobalamina' ➔ 'Pregabalina; Metilcobalamina', Forma Farmacéutica: 'Cápsula' ➔ 'Cápsula dura', **+Laboratorio/Fabricante** (Brixmedic) |
| 900000000006 | Media de compresión 15-20 mmHg, talla S/... | 35 | 35 | 2 | 5 | 0 | **+Marca** (No-Varix) |
| 900000000007 | Tensiómetro digital de brazo Skymedical ... | 40 | 45 | 5 | 5 | 2 | **+Laboratorio/Fabricante** (Skymedical) |
| 900000000008 | Drenaje quirúrgico Portovac con resorte ... | 45 | 40 | 2 | 5 | 0 | Ningún cambio en campos críticos |
| 900000000009 | Tubo Penrose estéril 1/4 x 1 unidad Brix... | 45 | 40 | 5 | 4 | 1 | Ningún cambio en campos críticos |
| 900000000010 | Sistema de drenaje quirúrgico Portovac c... | 30 | 45 | 3 | 5 | 0 | **+Forma Farmacéutica** (Sistema de drenaje) |
| 900000000011 | Apósito Euroderm Plus (Tegaderm + Pad - ... | 40 | 45 | 5 | 5 | 3 | Forma Farmacéutica: 'Apósito' ➔ 'Apósito adhesivo', **+Laboratorio/Fabricante** (BSN Medical), Marca: 'Euroderm Plus' ➔ 'Leukomed T Plus' |
| 900000000012 | Ondansetrón 4 mg/2 ml solución inyectabl... | 70 | 75 | 5 | 2 | 1 | **+Laboratorio/Fabricante** (Laboratorio Biosano S.A.), **+Reg. Sanitario** (F-15.338) |
| 900000000013 | Metotrexato 50 mg/2 ml solución inyectab... | 70 | 70 | 4 | 4 | 1 | **+Reg. Sanitario** (F-19444/22) |
| 900000000014 | Heparina 250 UI/g gel 30g... | 70 | 80 | 4 | 5 | 2 | Principio Activo: 'Heparina sódica' ➔ 'Heparina Sódica', Forma Farmacéutica: 'Gel' ➔ 'Gel tópico', **+Laboratorio/Fabricante** (Tiares), **+Marca** (Heparoid), **+Reg. Sanitario** (CPE0723541890) |
| 900000000015 | KOLNASI 500 mg 30 comprimidos SNC PHARMA... | 45 | 90 | 1 | 5 | 3 | **+Principio Activo** (Citicolina), **+Concentración** (500 mg), Forma Farmacéutica: 'Comprimido' ➔ 'Comprimido recubierto', **+Reg. Sanitario** (2008M-0008623) |
| 900000000016 | PENASTIM 500 mg solución inyectable... | 0 | 80 | 2 | 5 | 3 | **+Principio Activo** (Imipenem, Cilastatina), **+Concentración** (500 mg; 500 mg), Forma Farmacéutica: 'Solución inyectable' ➔ 'Polvo para solución para infusión IV', **+Laboratorio/Fabricante** (Aless Pharmaceuticals), **+Marca** (PENASTIM), **+Reg. Sanitario** (2008M-0008623) |
| 900000000017 | KETOPROFENO 100MG/2ML SOLUCIÓN INYECTABL... | 0 | 0 | 2 | 1 | 0 | **+Laboratorio/Fabricante** (LABORATORIO BIOSANO S.A.), **+Reg. Sanitario** (F-7663/21) |
| 900000000018 | Testo-Mix 250mg/ml, 10 ampollas de 1ml, ... | 75 | 100 | 3 | 3 | 3 | **+Laboratorio/Fabricante** (Cooper Pharma Limited), Marca: 'Testo-Mix' ➔ 'Susobolic', **+Reg. Sanitario** (2008M-0008623) |
| 900000000019 | Ena Prime 250 mg/ml solución inyectable,... | 35 | 90 | 1 | 5 | 0 | **+Principio Activo** (Testosterona), **+Concentración** (250 mg/ml), **+Laboratorio/Fabricante** (ETHON PHARMACEUTICALS S.P.A.), **+Marca** (Ena Prime), **+Reg. Sanitario** (F-18996/21) |

## Resumen de Impacto
- **Total productos evaluados**: 20
- **Productos que mejoraron su score de precisión**: 13 de 20
- **Total de imágenes procesadas y aprobadas**: 29