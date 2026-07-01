USE [NameOfDatabase] -- Reemplazar con el nombre real de la base de datos si es necesario
GO

ALTER TABLE Procurement.por_aprobacion_equivalencias
ADD modelo_ia_Des VARCHAR(100) NULL;
GO
