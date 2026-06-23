USE EnterpriseAdmin_AMC
GO

-- 1. Triaje de Insumos (status = 2)
UPDATE Procurement.por_aprobacion_equivalencias
SET status = 2, origen_dato = 'IA_SKIPPED_DEVICE'
WHERE codbarras IN (
    '00001', '00002', '00003', '0012', '002435', '00456', '00770', '0101', '0277', 
    '039800014023', '039800014030', '09324', '100006', '100007', '100008', '100010', 
    '100011', '100014'
);

-- 2. Actualización de Medicamentos (status = 1)
-- Lote 1 & 3 (Ejemplos representativos, el script completo se ejecutaría en Python por volumen)
-- ...
