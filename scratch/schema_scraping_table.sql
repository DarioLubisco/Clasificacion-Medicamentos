USE EnterpriseAdmin_AMC;
GO

-- 1. Create the raw scraping table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[Procurement].[scraping_farmacias_raw]') AND type in (N'U'))
BEGIN
    CREATE TABLE [Procurement].[scraping_farmacias_raw](
        [id_scrap] [int] IDENTITY(1,1) NOT NULL,
        [codbarras] [varchar](100) NOT NULL,
        [farmacia_origen] [varchar](100) NULL,
        [url_origen] [varchar](1000) NULL,
        [url_imagen] [varchar](1000) NULL,
        [texto_extraido] [nvarchar](max) NULL,
        [fecha_extraccion] [datetime] NOT NULL DEFAULT (getdate()),
        [procesado_fase3] [bit] NOT NULL DEFAULT ((0)),
        CONSTRAINT [PK_scraping_farmacias_raw] PRIMARY KEY CLUSTERED 
        (
            [id_scrap] ASC
        )
    )
END
GO

-- 2. Add procesado_fase2 to the master table
IF COL_LENGTH('Procurement.por_aprobacion_equivalencias', 'procesado_fase2') IS NULL
BEGIN
    ALTER TABLE Procurement.por_aprobacion_equivalencias
    ADD procesado_fase2 BIT NOT NULL DEFAULT 0;
END
GO
