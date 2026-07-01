-- Migración para añadir el campo de código ATC de nivel profundo (Nivel 4 o 5)
ALTER TABLE Procurement.por_aprobacion_equivalencias 
ADD codigo_atc_profundo_Des VARCHAR(50) NULL;
