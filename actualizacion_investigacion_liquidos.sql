
        BEGIN
            DECLARE @id_taxonomia INT;
            
            SELECT @id_taxonomia = id_taxonomia 
            FROM Procurement.Taxonomia 
            WHERE dominio = 'MEDICAMENTO_ALOPATICO' 
              AND ISNULL(categoria, 'SINEVAL') = 'B03 - PREPARADOS ANTIANÉMICOS' 
              AND ISNULL(subcategoria, 'SINEVAL') = 'B03AD - Ácido fólico y hierro';
              
            IF @id_taxonomia IS NULL
            BEGIN
                INSERT INTO Procurement.Taxonomia (dominio, categoria, subcategoria) 
                VALUES ('MEDICAMENTO_ALOPATICO', NULLIF('B03 - PREPARADOS ANTIANÉMICOS', 'SINEVAL'), NULLIF('B03AD - Ácido fólico y hierro', 'SINEVAL'));
                SET @id_taxonomia = SCOPE_IDENTITY();
            END
            
            UPDATE Procurement.por_aprobacion_equivalencias 
            SET principio_activo_Des = 'HIERRO-ÁCIDO FÓLICO', concentracion_Des = '40MG/15ML-360MCG', forma_farmaceutica_Des = 'Jarabe', fabricante_Des = 'H&M', marca_Des = 'H&M', codigo_atc_Des = 'B03AD', clasificacion_insumo_Des = NULL, requiere_recipe = 0, blister = 0, generico = 1, cantidad_presentacion = 1, contenido_neto = 120.0, contenido_neto_unidad_Des = 'ml', segmento_etario = 'PEDIATRICO', origen_Des = 'IA', score_calidad = 97, estado_ciclo = 'CERRADO', ciclos_reproceso = 0, observaciones_ia = '[MEDICAMENTO_ALOPATICO] MULTIPLE_COMPUESTO_NORMALIZADO', origen_dato = 'IA_INVESTIGATED_V10_AUTO', principio_activo = NULL, concentracion = 1161, forma_farmaceutica = 15, fabricante = 1277, marca = NULL, codigo_atc = 1365, clasificacion_insumo = NULL, origen = 2, contenido_neto_unidad = 32, es_medicamento = 1,
                id_taxonomia = @id_taxonomia
            WHERE codbarras = '0793969044405';
        END
        
GO

        BEGIN
            DECLARE @id_taxonomia INT;
            
            SELECT @id_taxonomia = id_taxonomia 
            FROM Procurement.Taxonomia 
            WHERE dominio = 'MEDICAMENTO_ALOPATICO' 
              AND ISNULL(categoria, 'SINEVAL') = 'R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO' 
              AND ISNULL(subcategoria, 'SINEVAL') = 'R05X - OTRAS PREPARACIONES PARA EL RESFRIADO';
              
            IF @id_taxonomia IS NULL
            BEGIN
                INSERT INTO Procurement.Taxonomia (dominio, categoria, subcategoria) 
                VALUES ('MEDICAMENTO_ALOPATICO', NULLIF('R05 - PREPARADOS PARA LA TOS Y EL RESFRIADO', 'SINEVAL'), NULLIF('R05X - OTRAS PREPARACIONES PARA EL RESFRIADO', 'SINEVAL'));
                SET @id_taxonomia = SCOPE_IDENTITY();
            END
            
            UPDATE Procurement.por_aprobacion_equivalencias 
            SET principio_activo_Des = NULL, concentracion_Des = NULL, forma_farmaceutica_Des = 'Jarabe', fabricante_Des = NULL, marca_Des = 'SINUTIL', codigo_atc_Des = 'R05X', clasificacion_insumo_Des = NULL, requiere_recipe = 0, blister = 0, generico = 0, cantidad_presentacion = 1, contenido_neto = 90.0, contenido_neto_unidad_Des = 'ml', segmento_etario = 'PEDIATRICO', origen_Des = 'IA', score_calidad = 0, estado_ciclo = 'AGOTADO', ciclos_reproceso = 4, observaciones_ia = '[MEDICAMENTO_ALOPATICO] ERR_MISMATCH_PA_CONC: IA extrajo 0 PAs ('''') y 2 CONCs (''325/32/4 mg'').', origen_dato = 'IA_INVESTIGATED_V10_AUTO', principio_activo = NULL, concentracion = NULL, forma_farmaceutica = 15, fabricante = NULL, marca = 10773, codigo_atc = 1313, clasificacion_insumo = NULL, origen = 2, contenido_neto_unidad = 32, es_medicamento = 0,
                id_taxonomia = @id_taxonomia
            WHERE codbarras = '2260000046134';
        END
        