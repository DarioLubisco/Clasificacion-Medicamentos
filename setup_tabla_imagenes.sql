-- Script para crear la tabla satélite de imágenes recolectadas por el scraper
-- Destino: EnterpriseAdmin_AMC.Procurement.Imagenes_Productos_Crudas

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[Procurement].[Imagenes_Productos_Crudas]') AND type in (N'U'))
BEGIN
    CREATE TABLE Procurement.Imagenes_Productos_Crudas (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codbarras VARCHAR(50) NOT NULL,
        url_imagen NVARCHAR(MAX) NOT NULL,
        score_legibilidad INT NOT NULL,
        fecha_registro DATETIME DEFAULT GETDATE()
    );
    PRINT 'Tabla Procurement.Imagenes_Productos_Crudas creada con éxito.';
END
ELSE
BEGIN
    PRINT 'La tabla Procurement.Imagenes_Productos_Crudas ya existe.';
END
GO
