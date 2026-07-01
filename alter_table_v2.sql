-- ====================================================================
-- Script: alter_table_v2.sql
-- Objetivo: Añadir las columnas necesarias para soportar el Agente V2 
--           de Clasificación de Insumos Médicos (especificaciones técnicas).
-- Ejecutar en: SQL Server (Instancia Saint, Base de Datos principal)
-- ====================================================================

USE [EnterpriseAdmin_AMC]; -- Base de datos principal de producción
GO

ALTER TABLE Procurement.por_aprobacion_equivalencias
ADD 
    especificacion_tecnica VARCHAR(255) NULL,
    dominio VARCHAR(100) NULL,
    categoria VARCHAR(100) NULL,
    subcategoria VARCHAR(100) NULL;
GO

PRINT 'Columnas especificacion_tecnica, dominio, categoria y subcategoria añadidas con éxito.';
GO
