-- =====================================================================
-- Añade columnas de tokens cacheados a OrquestadorLLMLog para medir el
-- ahorro del prefix caching (DeepSeek disk cache / Z.ai context cache).
--
-- Relacionado con la optimización de caché de prompts (2026-07-24).
-- El INSERT de orquestador_produccion.py es DEFENSIVO: si estas columnas
-- no existen aún, reintenta sin ellas y no rompe el batch. Por lo tanto
-- este script puede correrse con calma cuando el DBA lo disponga.
--
-- Columnas:
--   PromptCacheHitTokens  : input tokens servidos desde caché (precio rebajado)
--   PromptCacheMissTokens : input tokens procesados en frío (precio pleno)
-- =====================================================================
USE [NameOfDatabase] -- Reemplazar con el nombre real de la base de datos si es necesario
GO

ALTER TABLE Procurement.OrquestadorLLMLog
ADD PromptCacheHitTokens INT NULL,
    PromptCacheMissTokens INT NULL;
GO
