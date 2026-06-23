BEGIN TRAN;

-- 1. 000000000130 | ONDANSETRON 4 MG / 2ML X 10 AMP ( I.V )  ( BIOSANO )
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BIOSANO' WHERE codbarras = '000000000130' AND fabricante_Des IS NULL;

-- 2. 0000000030373 | DISCOLAYTE POLVO 69.7 G X 10 SOBRES DISTRILAB
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DISTRILAB', marca_Des = 'DISCOLAYTE' WHERE codbarras = '0000000030373' AND fabricante_Des IS NULL;

-- 3. 0000000072410 | AMOXICILINA - ACIDO CLAVULANICO 875 MG - 125 MG X 10 TABLETAS ARTE MEDICO
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ARTE MEDICO' WHERE codbarras = '0000000072410' AND fabricante_Des IS NULL;

-- 4. 0000000093491 | SERTRALINA 50 MG X 10 TABLETAS ARTE MEDICO
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ARTE MEDICO' WHERE codbarras = '0000000093491' AND fabricante_Des IS NULL;

-- 5. 0000000104098 | DIOSMINA + HESPERIDINA 450 MG / 50 MG X 10 TABLETAS DROTAFARMA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DROTAFARMA' WHERE codbarras = '0000000104098' AND fabricante_Des IS NULL;

-- 6. 0000000107839 | VANCOMICINA 1 G POLVO PARA SOLUCION INYECTABLE I.V X 10 AMPOLLA ZAKIMED
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ZAKIMED' WHERE codbarras = '0000000107839' AND fabricante_Des IS NULL;

-- 7. 0000000154697 | SALES DE REHIDRATACION ORAL HIDROLIT FRESA 21.5G X 10 SOBRES DROTAFARMA
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'HIDROLIT', fabricante_Des = 'DROTAFARMA' WHERE codbarras = '0000000154697' AND marca_Des IS NULL;

-- 8. 0000000163750 | METRONIDAZOL 500 MG X 10 TABLETAS ZAKIMED
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ZAKIMED' WHERE codbarras = '0000000163750' AND fabricante_Des IS NULL;

-- 9. 0000000163774 | OXACILINA 1G POLVO PARA SOLUCION INYECTABLE I.M/ I.V X 10 VIALES ZAKIMED
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ZAKIMED' WHERE codbarras = '0000000163774' AND fabricante_Des IS NULL;

-- 10. 0000000180528 | HIDROLIT 21.5G X 10 SOBRES SABOR COCO DROTAFARMA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DROTAFARMA' WHERE codbarras = '0000000180528' AND fabricante_Des IS NULL;

-- 11. 0000000184885 | ISOSPRAY PLUS 0.15% - 0.25% X 120ML
-- Nada claro en fabricante, marca ya capturada. No se altera.

-- 12. 0000000193009 | LIDOCARE CREMA 5% X 30GR MEDPHARMA
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'LIDOCARE' WHERE codbarras = '0000000193009' AND marca_Des IS NULL;

-- 13. 0000000195911 | LOSARTAN POTASICO 100 MG X 30 TAB ALFA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'ALFA' WHERE codbarras = '0000000195911' AND fabricante_Des IS NULL;

-- 14. 0000000201629 | TREXOL SOL INY 50 MG / 2 ML I.V-I.M (METOTREXATO) X 1 AMP VENUS
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'TREXOL', fabricante_Des = 'VENUS' WHERE codbarras = '0000000201629' AND marca_Des IS NULL;

-- 15. 0000000206815 | GEMCITABINE 1 GR POLVO SOL INY X 1 AMP RTM
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'RTM' WHERE codbarras = '0000000206815' AND fabricante_Des IS NULL;

-- 16-23 Farmagenik (Múltiples)
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'FARMAGENIK' WHERE codbarras IN ('0000001100181', '0000001100198', '0000025525748', '0000025525755', '0000025525762', '0000025526479', '01100181', '01100198', '0112266402235') AND fabricante_Des IS NULL;

-- 18. 0000007603815 | SAL DE FRUTAS MAKENO ... BIUMAK
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BIUMAK', marca_Des = 'MAKENO' WHERE codbarras = '0000007603815' AND fabricante_Des IS NULL;

-- 19. 0000020000264 | NIFEDIPINA LP 20 MG X 30 TABLETAS  LATTAN MEDIC
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'LATTAN MEDIC' WHERE codbarras = '0000020000264' AND fabricante_Des IS NULL;

-- 24. 00000451 | HEPAROID ( HEPARINA ) 250 UI / G X 30 G GEL ( TIARES )
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'HEPAROID', fabricante_Des = 'TIARES' WHERE codbarras = '00000451' AND marca_Des IS NULL;

-- 25. 0000075970543 | CREMA SULFUROCIS 40GR AZUFRE 10% + IVERMECTINA 1% + VITAMINA A-D-E  BOOZ
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'SULFUROCIS', fabricante_Des = 'BOOZ' WHERE codbarras = '0000075970543' AND marca_Des IS NULL;

-- 26. 001004002941515 | HIDROCORTISONA 500MG X 1 AMP I.V-I.M DROTAFARMA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'DROTAFARMA' WHERE codbarras = '001004002941515' AND fabricante_Des IS NULL;

-- 27-28. Pepto Bismol
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PEPTO-BISMOL', fabricante_Des = 'PROCTER & GAMBLE' WHERE codbarras IN ('0020800753050', '0020800753067', '020800753067') AND marca_Des IS NULL;

-- 29. 0021241259262 | TEOFILINA 100 MG X 10 TABLETAS BUKA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BUKA' WHERE codbarras = '0021241259262' AND fabricante_Des IS NULL;

-- 30-31. EMPAGLIF BUKA
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'EMPAGLIF', fabricante_Des = 'BUKA' WHERE codbarras IN ('0021281086200', '0021281086217') AND marca_Des IS NULL;

-- 32. 0021281086293 | TESTOMIX (MEZCLA DE TESTOSTERONA) 1ML X 10AMP EMINENCE LABS
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'TESTOMIX', fabricante_Des = 'EMINENCE LABS' WHERE codbarras = '0021281086293' AND marca_Des IS NULL;

-- LOTE MEDICAL CARE & H&M (Líneas 38-60)
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'MEDICAL CARE' WHERE codbarras = '0614143659027' AND fabricante_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'H&M' WHERE codbarras IN (
  '0632627843366', '0632627843380', '0632627843397', '0632627843403', '0632627843410', '0632627843427', '0632627843441', '0632627843458', '0632627843465', '0632627843472', '0632627843496', '0632627843502', '0632627843519', '0632627843526', '0632627843533', '0632627843557', '0632627843564', '0632627843571', '0632627843588', '0632627843595', '0632627843601'
) AND fabricante_Des IS NULL;

-- 62. EL MORRO
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'EL MORRO' WHERE codbarras = '0652931975645' AND fabricante_Des IS NULL;

-- 63-80. LOTE BUKA
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'BUKA' WHERE codbarras IN (
  '0675696259942', '0675696259973', '0675696260023', '0675696260030', '0675696260054', '0675696260061', '0675696260078', '0675696260085', '0675696260115', '0675696260122', '0675696260139', '0675696260146', '0675696260153', '0675696260184', '0675696260191', '0675696260207', '0675696260214', '0675696260597'
) AND fabricante_Des IS NULL;

-- 81-100. LOTE PHARMALAB & Marcas (PHARMAVAL, CLAVAMOX, PHARMABAC, PHARMATROP, etc.)
UPDATE Procurement.por_aprobacion_equivalencias SET fabricante_Des = 'PHARMALAB' WHERE codbarras IN (
  '0677144727157', '0677144727164', '0677144727171', '0677144727188', '0677144727195', '0677144727201', '0677144727218', '0677144727225', '0677144727232', '0677144727249', '0677144727256', '0677144727263', '0677144727270', '0677144727287', '0677144727294', '0677144727300', '0677144727317', '0677144727324', '0677144727331', '0677144727348'
) AND fabricante_Des IS NULL;

UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMAFOLIC' WHERE codbarras = '0677144727157' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMAVAL' WHERE codbarras IN ('0677144727164', '0677144727171') AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'CLAVAMOX DUO' WHERE codbarras IN ('0677144727188', '0677144727195') AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMABAC' WHERE codbarras = '0677144727201' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMATROP' WHERE codbarras = '0677144727218' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARXINATO RELAX' WHERE codbarras = '0677144727249' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMAMONT PLUS' WHERE codbarras = '0677144727256' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMACALM' WHERE codbarras = '0677144727300' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMANIFE' WHERE codbarras = '0677144727324' AND marca_Des IS NULL;
UPDATE Procurement.por_aprobacion_equivalencias SET marca_Des = 'PHARMACORT' WHERE codbarras = '0677144727348' AND marca_Des IS NULL;

COMMIT;
