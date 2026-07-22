"""
Orquestador del pipeline farmacéutico (scraper + evaluate_local).

Recibe el payload de Config.AutomationTriggers (mismo contrato que el antiguo
synapse-api /api/orquestador/start), procesa un lote incremental y escribe los
resultados DIRECTO a SQL Server (UPDATE sobre Procurement.por_aprobacion_equivalencias).
Sin intermediario n8n: la escritura la hace este proceso con pyodbc + commit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pyodbc

from synapse_cred import load_synapse_credentials

load_synapse_credentials()

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import evaluate_local as ev
import orquestador_scraper as scrap
from normalizador_farmaceutico import procesar_farmacos
from MDM_Unified_Mapper import MasterCatalog
from alertas import log_evento
from n8n_error_reporter import report_valueserp_access_failure, report_external_error, report_scraper_critical

REPO_DIR = Path(__file__).resolve().parent
BATCH_SIZE = int(os.getenv("ORQUESTADOR_BATCH_SIZE", "5"))
MAX_REINTENTOS = int(os.getenv("ORQUESTADOR_MAX_REINTENTOS", "3"))
SCORE_CIERRE = int(os.getenv("ORQUESTADOR_SCORE_CIERRE", "88"))
SCORE_CIERRE_NO_MED = int(os.getenv("ORQUESTADOR_SCORE_CIERRE_NO_MED", "70"))
MAX_FUENTES_WEB = int(os.getenv("MAX_FUENTES_WEB", "10"))
MAX_FOTOS_TOTALES = int(os.getenv("MAX_FOTOS_TOTALES", "10"))
SCRAPING_DELAY = float(os.getenv("SCRAPING_DELAY", "0.5"))


def _conn_str() -> str:
    server = os.getenv("DB_SERVER", "100.94.5.108,49751")
    # Si el server tiene instance name pero sin puerto, forzar puerto 49751
    if "\\\\" in server and "," not in server:
        port = os.getenv("DB_PORT", "49751")
        server = f"{server},{port}"
    database = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "")
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={user};PWD={password};"
        "TrustServerCertificate=yes;Encrypt=yes;"
    )


def get_db_connection() -> pyodbc.Connection:
    timeout_red = int(os.getenv("TIMEOUT_RED", "20"))
    return pyodbc.connect(_conn_str(), timeout=timeout_red)


def check_threshold(trigger: dict[str, Any]) -> bool:
    query = trigger.get("CheckQuery")
    threshold = int(trigger.get("ThresholdValue") or 1)
    if not query:
        return True
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        count = int(row[0]) if row else 0
        return count >= threshold
    finally:
        conn.close()


def fetch_productos_abiertos(limit: int) -> list[dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT TOP ({limit})
                codbarras, descrip1art,
                ISNULL(ciclos_reproceso, 0) AS ciclos_reproceso,
                principio_activo_Des, concentracion_Des, forma_farmaceutica_Des,
                fabricante_Des, marca_Des, codigo_atc_Des, clasificacion_insumo_Des,
                generico, cantidad_presentacion,
                contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
            FROM Procurement.por_aprobacion_equivalencias
            WHERE estado_ciclo = 'ABIERTO'
            ORDER BY
                -- Prioridad 1: productos nunca procesados (0 ciclos) primero
                ISNULL(ciclos_reproceso, 0) ASC,
                -- Prioridad 2: EAN-13 primero (scrapeables), códigos internos al final
                CASE WHEN LEN(codbarras) = 13 AND codbarras NOT LIKE 'BLI_%' THEN 0 ELSE 1 END,
                -- Prioridad 3: más antiguos primero
                ISNULL(LastUpdated, '1900-01-01') ASC
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    productos = []
    keys = [
        "principio_activo", "concentracion", "forma_farmaceutica", "fabricante", "marca",
        "codigo_atc", "clasificacion_insumo_Des", "generico",
        "cantidad_presentacion", "contenido_neto", "contenido_neto_unidad_Des",
        "segmento_etario", "origen",
    ]
    for row in rows:
        ya = {}
        for idx, key in enumerate(keys):
            val = row[3 + idx]
            if val is not None and str(val).strip() != "":
                ya[key] = val
        productos.append({
            "codbarras": row[0],
            "descripcion": row[1],
            "ciclos_reproceso": int(row[2]),
            "atributos_ya_encontrados": ya,
        })
    return productos


def scrape_producto(codbarras: str, descripcion: str, trigger_id: int | None = None) -> tuple[list, list, list]:
    """Scrapea un producto. Devuelve (fuentes_extraidas, imagenes_aprobadas, urls_encontradas).

    Flujo optimizado (2026-07-20):
      1. Busca solo con el EAN (no descripción) — más URLs de farmacias, menos ruido.
      2. Para cada fuente, extrae 1 imagen → pre-filtro inline → cuenta si pasa.
      3. Para cuando tenga 4 aprobadas o agote 10 fuentes.
      4. Si tras 10 fuentes no llega a 4, devuelve lo que tenga.
    """
    fuentes_extraidas: list = []
    urls_aprobadas_para_ocr: list = []
    urls_encontradas: list = []
    is_internal = codbarras.startswith("BLI_") or len(codbarras) != 13
    umbral = int(os.getenv("VISION_UMBRAL", "3"))
    target_aprobadas = int(os.getenv("VISION_MAX_OCR", "4"))
    imgs_por_fuente = 1  # 1 imagen por fuente (mejor score de proximidad)

    if is_internal:
        log_evento(
            "WARN", "SCRAPER",
            f"Scraping saltado: código interno (len={len(codbarras)}). "
            f"El pipeline correrá sin imágenes ni fuentes web.",
            codbarras=codbarras, trigger_id=trigger_id,
            detalle={"motivo": "codigo_interno", "len": len(codbarras)},
        )
        return [], [], []

    # Query SOLO con EAN — no descripción. ValueSERP devuelve más URLs de farmacias.
    query = f'"{codbarras}"'
    urls = scrap.buscar_en_internet(query, max_fuentes=MAX_FUENTES_WEB)

    for idx, url in enumerate(urls, 1):
        if len(urls_aprobadas_para_ocr) >= target_aprobadas:
            break

        fuente = scrap.extraer_fuente_web(url, idx, descripcion)
        if fuente:
            fuentes_extraidas.append(fuente)
            urls_encontradas.append(url)

            # Pre-filtro inline: evaluar cada imagen extraída de inmediato.
            # Si pasa el umbral (≥3), se cuenta para OCR. Si no, se descarta.
            # Esto permite parar al llegar a 4 aprobadas sin evaluar todas las fuentes.
            for img_url in fuente.get("imagenes_encontradas", [])[:imgs_por_fuente]:
                try:
                    _, fotos_a_guardar, _ = ev.filtrar_imagenes_legibles([img_url], descripcion)
                    if fotos_a_guardar and fotos_a_guardar[0]["score"] >= umbral:
                        urls_aprobadas_para_ocr.append(img_url)
                        print(f"    [Pre-Filtro] Foto #{len(urls_aprobadas_para_ocr)}/{target_aprobadas} "
                              f"aprobada (Puntaje: {fotos_a_guardar[0]['score']})")
                        if len(urls_aprobadas_para_ocr) >= target_aprobadas:
                            print(f"    [Pre-Filtro] Target alcanzado: {target_aprobadas} fotos aprobadas")
                            break
                    elif fotos_a_guardar:
                        print(f"    [Pre-Filtro] Foto descartada (Puntaje: {fotos_a_guardar[0]['score']})")
                except Exception as e:
                    print(f"    [Pre-Filtro] Error evaluando imagen: {e}")
        time.sleep(SCRAPING_DELAY)

    # Diagnóstico fino del resultado del scraping. Antes todo se reportaba como
    # "scraper no trajo fuentes ni imágenes" (WARN), lo cual era un falso positivo:
    # cuando ValueSERP sí devolvía URLs pero la extracción HTML fallaba (SSL, 403, etc.),
    # el producto igual clasificaba bien con score 80+. Eso llenaba el log de alertas
    # ruidosas que no indicaban problemas reales.
    if not urls:
        log_evento(
            "WARN", "SCRAPER",
            f"ValueSERP no devolvió URLs para {codbarras}. Posible caída de API o red.",
            codbarras=codbarras, trigger_id=trigger_id,
            detalle={"motivo": "valueserp_vacio", "query": query[:200]},
        )
    elif urls and not fuentes_extraidas:
        log_evento(
            "INFO", "SCRAPER",
            f"{codbarras}: {len(urls)} URLs halladas pero 0 extrajeron contenido "
            f"(SSL/403/timeout en descarga HTML). El pipeline continúa con solo descripción.",
            codbarras=codbarras, trigger_id=trigger_id,
            detalle={"motivo": "html_descarga_fallo", "urls": urls[:5]},
            alerta_telegram=False,  # INFO no Telegram; común cuando farmacias caen
        )

    return (
        fuentes_extraidas,
        urls_aprobadas_para_ocr,
        urls_encontradas,
    )


def _buscar_id_taxonomia(
    conn_str: str,
    dominio: str | None,
    categoria: str | None,
    subcategoria: str | None,
) -> int | None:
    """Lookup del id_taxonomia en Procurement.Taxonomia por match exacto de
    dominio + categoria + subcategoria (todas activas, activo=1).
    Devuelve None si falta algún campo, no hay match, o hay error de conexión.
    """
    if not (dominio and categoria and subcategoria):
        return None
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT TOP 1 id_taxonomia FROM Procurement.Taxonomia "
                "WHERE dominio = ? AND categoria = ? AND subcategoria = ? "
                "AND activo = 1",
                dominio, categoria, subcategoria,
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except Exception:
        # Lookup es best-effort: si falla no rompe el batch (la taxonomía
        # queda en las columnas VARCHAR como respaldo).
        return None


def _sql_lit(val: Any, is_string: bool = True) -> str:
    """Format a Python value as a SQL literal (NULL if empty). Mirrors fmt() in the boss script."""
    if val is None or val == "None" or str(val).strip() == "":
        return "NULL"
    val_str = str(val).strip()
    if val_str.lower() == "true":
        return "1"
    if val_str.lower() == "false":
        return "0"
    if is_string:
        return "'" + val_str.replace("'", "''") + "'"
    return val_str


def build_update_clauses(
    atrib: dict[str, Any],
    ciclos_reproceso: int,
    descripcion: str = "",
    catalog: Any = None,
) -> tuple[list[str], int, str, int]:
    """Build SET clauses for the UPDATE, aligned to the real table schema
    (same columns as tests/test_ciclo_completo_100.py). No invented _Des columns,
    no requiere_recipe. Returns (clauses, score, estado_ciclo, ciclos_final)."""
    limpieza = procesar_farmacos(atrib.get("principio_activo"), atrib.get("concentracion"))
    if limpieza["exito"]:
        atrib["principio_activo"] = limpieza["principio_activo"]
        atrib["concentracion"] = limpieza["concentracion"]
        observaciones = limpieza.get("observaciones") or ""
    else:
        atrib["principio_activo"] = None
        atrib["concentracion"] = None
        observaciones = limpieza.get("observaciones") or ""

    # Deducir segmento_etario desde ATC profundo (no viene del LLM)
    atrib["segmento_etario"] = ev.deducir_segmento_etario(atrib.get("codigo_atc_profundo"))

    # Post-proceso: extraer marca del nombre si el LLM no la extrajo
    if not atrib.get("marca"):
        _desc = (descripcion or atrib.get("descripcion_original") or atrib.get("descripcion") or "").upper()
        _pa = (atrib.get("principio_activo") or "").upper()
        _ff = (atrib.get("forma_farmaceutica") or "").upper()
        _conc = (atrib.get("concentracion") or "").upper()
        _genericos = {"MG", "ML", "G", "GR", "KG", "TAB", "TABLETA", "TABLETAS", "CAP",
                      "CÁPSULA", "CÁPSULAS", "CAPSULA", "CAPSULAS", "SUSPENSIÓN", "SUSPENSION",
                      "JARABE", "CREMA", "GEL", "SOLUCIÓN", "SOLUCION", "POLVO", "AMP",
                      "AMPOLLA", "AMPOLLAS", "X", "UNO", "UNIDAD", "UNIDADES", "FRASCO",
                      "CAJA", "BLISTER", "SOBRE", "SOBRES", "OVULO", "ÓVULO", "OVULOS",
                      "ÓVULOS", "SUP", "ORAL", "TOPICO", "TÓPICO", "OFTÁLMICO", "OFTALMICO",
                      "INHALADOR", "INYECTABLE", "INTRAMUSCULAR", "INTRAVENOSA", "PEDIÁTRICA",
                      "PEDIATRICA", "ADULTO", "PEDIÁTRICO", "PEDIATRICO", "JARABE"}
        _desc_words = _desc.replace(",", " ").replace(".", " ").split()
        for w in reversed(_desc_words):
            w_clean = w.strip()
            if not w_clean or w_clean in _genericos or w_clean.replace("/", "").replace("-", "").isdigit():
                continue
            if len(w_clean) < 3:
                continue
            if w_clean in _pa or w_clean in _ff or w_clean in _conc:
                continue
            atrib["marca"] = w_clean.title()
            break
    score = ev.calcular_score_calidad(atrib)
    dominio = atrib.get('dominio') or 'MEDICAMENTO_ALOPATICO'

    # Umbrales de cierre por dominio
    UMBRAL_CIERRE = {
        'MEDICAMENTO_ALOPATICO': 88,
        'SUPLEMENTO_VITAMINICO': 75,
        'PRODUCTO_NATURAL_HOMEOPATICO': 75,
        'COSMETICO_CUIDADO_PERSONAL': 80,
        'MATERIAL_MEDICO_INSUMO': 75,
        'MISCELANEO': 70,
    }
    umbral = UMBRAL_CIERRE.get(dominio, SCORE_CIERRE)

    if score >= umbral:
        estado_ciclo = "CERRADO"
        ciclos_final = ciclos_reproceso
    elif ciclos_reproceso >= MAX_REINTENTOS:
        estado_ciclo = "AGOTADO"
        ciclos_final = ciclos_reproceso
    else:
        estado_ciclo = "ABIERTO"
        ciclos_final = ciclos_reproceso + 1

    clauses = [
        f"principio_activo_Des = {_sql_lit(atrib.get('principio_activo'))}",
        f"concentracion_Des = {_sql_lit(atrib.get('concentracion'))}",
        f"forma_farmaceutica_Des = {_sql_lit(atrib.get('forma_farmaceutica'))}",
        f"fabricante_Des = {_sql_lit(atrib.get('fabricante'))}",
        f"marca_Des = {_sql_lit(atrib.get('marca'))}",
        f"codigo_atc_Des = {_sql_lit(atrib.get('codigo_atc'))}",
        f"clasificacion_insumo_Des = {_sql_lit(atrib.get('clasificacion_insumo_Des'))}",
        # Campos nuevos sincronizados con prompt V3 (antes se descartaban).
        f"codigo_atc_profundo_Des = {_sql_lit(atrib.get('codigo_atc_profundo'))}",
        f"confianza_atc = {_sql_lit(atrib.get('confianza_atc'), False)}",
        f"dominio = {_sql_lit(atrib.get('dominio'))}",
        f"categoria = {_sql_lit(atrib.get('categoria'))}",
        f"subcategoria = {_sql_lit(atrib.get('subcategoria'))}",
        f"registro_sanitario = {_sql_lit(atrib.get('registro_sanitario'))}",
        f"especificacion_tecnica = {_sql_lit(atrib.get('especificacion_tecnica'))}",
        f"volumen_unidad = {_sql_lit(atrib.get('volumen_unidad'), False)}",
        f"volumen_unidad_medida = {_sql_lit(atrib.get('volumen_unidad_medida'))}",
        f"generico = {_sql_lit(atrib.get('generico'), False)}",
        f"cantidad_presentacion = {_sql_lit(atrib.get('cantidad_presentacion'), False)}",
        f"contenido_neto = {_sql_lit(atrib.get('contenido_neto'), False)}",
        f"contenido_neto_unidad_Des = {_sql_lit(atrib.get('contenido_neto_unidad_Des'))}",
        f"segmento_etario = {_sql_lit(atrib.get('segmento_etario'))}",
        f"origen_Des = {_sql_lit(atrib.get('origen'))}",
        f"score_calidad = {score}",
        f"estado_ciclo = '{estado_ciclo}'",
        f"ciclos_reproceso = {ciclos_final}",
        f"observaciones_ia = {_sql_lit(observaciones[:500] if observaciones else None)}",
        "origen_dato = 'IA_INVESTIGATED_V11_ORCHESTRATOR'",
        f"es_medicamento = {1 if (atrib.get('dominio') or '') in ('MEDICAMENTO_ALOPATICO','PRODUCTO_NATURAL_HOMEOPATICO','SUPLEMENTO_VITAMINICO') else 0}",
        "LastUpdated = GETDATE()",
    ]

    # MDM catalog mapping (numeric IDs), mirrors boss script
    if catalog:
        clauses.extend([
            f"principio_activo = {_sql_lit(catalog.find_id('principio_activo', atrib.get('principio_activo')), False)}",
            f"concentracion = {_sql_lit(catalog.find_id('concentracion', atrib.get('concentracion')), False)}",
            f"forma_farmaceutica = {_sql_lit(catalog.find_id('forma_farmaceutica', atrib.get('forma_farmaceutica')), False)}",
            f"fabricante = {_sql_lit(catalog.find_id('fabricante', atrib.get('fabricante')), False)}",
            f"marca = {_sql_lit(catalog.find_id('marca', atrib.get('marca')), False)}",
            f"codigo_atc = {_sql_lit(catalog.find_id('codigo_atc', atrib.get('codigo_atc')), False)}",
            f"clasificacion_insumo = {_sql_lit(catalog.find_id('clasificacion_insumo', atrib.get('clasificacion_insumo_Des')), False)}",
            f"origen = {_sql_lit(catalog.find_id('origen', atrib.get('origen')), False)}",
            f"contenido_neto_unidad = {_sql_lit(catalog.find_id('contenido_neto_unidad', atrib.get('contenido_neto_unidad_Des')), False)}",
        ])

    # id_taxonomia: lookup en Procurement.Taxonomia por (dominio, categoria, subcategoria).
    # Best-effort: si no hay match exacto o falla, queda NULL (las columnas
    # VARCHAR dominio/categoria/subcategoria sirven como respaldo textual).
    id_tax = _buscar_id_taxonomia(
        _conn_str(),
        atrib.get("dominio"), atrib.get("categoria"), atrib.get("subcategoria"),
    )
    if id_tax:
        clauses.append(f"id_taxonomia = {id_tax}")

    return clauses, score, estado_ciclo, ciclos_final


def write_rows_to_db(rows: list[dict[str, Any]], trigger_id: int | None = None) -> int:
    """Write UPDATE rows directly to SQL Server. Each row has 'codbarras' + 'clauses'.
    Returns number of rows written. Alerta si una fila afecta 0 (EAN no hallado)
    o si el UPDATE falla con excepción."""
    if not rows:
        return 0
    conn = get_db_connection()
    written = 0
    ceros = []   # codbarras cuyo UPDATE afectó 0 filas
    try:
        cur = conn.cursor()
        for row in rows:
            set_sql = ", ".join(row["clauses"])
            ean = row["codbarras"].replace("'", "''")
            update = f"UPDATE Procurement.por_aprobacion_equivalencias SET {set_sql} WHERE codbarras = '{ean}';"
            try:
                cur.execute(update)
                afectadas = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
                if afectadas == 0:
                    ceros.append(row["codbarras"])
                written += afectadas
            except Exception as exc_row:
                # Error de SQL en UNA fila: registrar y continuar con las demás (no abortar el lote).
                log_evento(
                    "ERROR", "WRITER",
                    f"UPDATE falló para {row['codbarras']}: {exc_row}",
                    codbarras=row["codbarras"], trigger_id=trigger_id,
                    detalle={"sql": update[:500]},
                )
        conn.commit()
    except Exception as exc_batch:
        # Error de conexión/transacción: alertar y propagar para que el lote se sepa caído.
        log_evento(
            "ERROR", "WRITER",
            f"Error de escritura en bloque (commit/conn): {exc_batch}",
            trigger_id=trigger_id,
            detalle={"rows_esperadas": len(rows)},
        )
        raise
    finally:
        conn.close()

    if ceros:
        log_evento(
            "WARN", "WRITER",
            f"{len(ceros)} producto(s) no encontrados en la tabla (UPDATE afectó 0 filas): "
            f"{', '.join(ceros[:10])}{'…' if len(ceros) > 10 else ''}",
            trigger_id=trigger_id,
            detalle={"codbarras_no_encontrados": ceros},
        )
    return written


def _persistir_trazabilidad(
    codbarras: str,
    trigger_id: int | None,
    metricas: dict,
    raw_content: str,
    fotos: list[dict],
    fuentes: list[dict],
    urls_encontradas: list[str],
    atrib: dict,
    score: int | None,
    estado: str | None,
) -> None:
    """Persiste TODO lo que el pipeline calcula pero antes descartaba:
      - LLM: prompt final, respuesta cruda, chain-of-thought, tokens, costo,
        confianza, alertas (tabla nueva OrquestadorLLMLog).
      - Imágenes: URL + score legibilidad + LogID (Imagenes_Productos_Crudas).
      - Scraping crudo: URL origen + texto extraído (scraping_farmacias_raw).

    Best-effort: si falla algún INSERT, se loguea a OrquestadorLog y se continúa.
    La persistencia de trazabilidad NUNCA debe romper el batch principal.
    """
    try:
        conn = pyodbc.connect(_conn_str(), timeout=15)
    except Exception as exc:
        log_evento("WARN", "TRAZABILIDAD",
                   f"No se pudo conectar para persistir trazabilidad de {codbarras}: {exc}",
                   codbarras=codbarras, trigger_id=trigger_id,
                   alerta_telegram=False)
        return

    try:
        cur = conn.cursor()

        # 1) Fila principal en OrquestadorLLMLog
        costo_vision = float(metricas.get("costo_gemini") or 0)
        costo_texto = float(metricas.get("costo_glm") or 0)
        # Serializar listas/dicts a JSON string
        errores = metricas.get("errores_api") or []
        errores_str = json.dumps(errores, ensure_ascii=False)[:2000] if errores else None
        baja_conf = atrib.get("atributos_baja_confianza") if atrib else None
        baja_conf_str = json.dumps(list(baja_conf), ensure_ascii=False)[:500] if baja_conf else None
        alertas = (atrib.get("alertas_auditoria") if atrib else None) or None
        confianza = atrib.get("confianza_nivel") if atrib else None

        cur.execute(
            """INSERT INTO Procurement.OrquestadorLLMLog
               (TriggerID, Codbarras, ModeloTexto, ModeloVision, Temperatura,
                PromptArchivo, PromptEnviado, RespuestaCruda, ReasoningContent,
                PromptTokens, CompletionTokens, ReasoningTokens,
                CostoVisionUSD, CostoTextoUSD, CostoTotalUSD,
                ConfianzaNivel, AtributosBajaConf, AlertasAuditoria,
                TiempoTotalSeg, NumFuentes, NumImagenes, NumImagenesAprob,
                Errores, ScoreFinal, EstadoCiclo)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            trigger_id, codbarras,
            metricas.get("modelo_texto"),
            metricas.get("modelo_vision") or os.getenv("VISION_MODELO"),
            metricas.get("temperatura"),
            metricas.get("prompt_archivo"),
            metricas.get("prompt_enviado"),
            raw_content or None,
            metricas.get("reasoning_content") or None,
            int(metricas.get("prompt_tokens") or 0) or None,
            int(metricas.get("completion_tokens") or 0) or None,
            int(metricas.get("reasoning_tokens") or 0) or None,
            costo_vision or None,
            costo_texto or None,
            (costo_vision + costo_texto) or None,
            int(confianza) if confianza is not None else None,
            baja_conf_str,
            (alertas[:1000] if isinstance(alertas, str) else None),
            float(metricas.get("tiempo_total") or 0) or None,
            len(fuentes),                           # fuentes que SÍ extrajeron HTML
            int(metricas.get("num_imagenes") or 0),
            int(metricas.get("num_imagenes_aprob") or 0),
            errores_str,
            score,
            estado,
        )
        # Recuperar el LogID autogenerado (para FK suave en las tablas hijas)
        cur.execute("SELECT CAST(@@IDENTITY AS BIGINT)")
        row = cur.fetchone()
        log_id = int(row[0]) if row else None

        # 2) Una fila por imagen aprobada en Imagenes_Productos_Crudas
        if log_id and fotos:
            for foto in fotos:
                url = (foto.get("url_imagen") or "")[:5000]
                score_leg = foto.get("score")
                if url:
                    cur.execute(
                        """INSERT INTO Procurement.Imagenes_Productos_Crudas
                           (codbarras, url_imagen, score_legibilidad, LogID)
                           VALUES (?,?,?,?)""",
                        codbarras, url,
                        int(score_leg) if score_leg is not None else None,
                        log_id,
                    )

        # 3) Una fila por fuente extraída en scraping_farmacias_raw
        if log_id and fuentes:
            from urllib.parse import urlparse
            for fuente in fuentes:
                url_origen = (fuente.get("url") or "")[:1000]
                farmacia = urlparse(url_origen).netloc.replace("www.", "")[:100] if url_origen else None
                texto = (fuente.get("texto_extraido") or "")
                imagenes_fuente = fuente.get("imagenes_encontradas") or []
                url_img_principal = (imagenes_fuente[0] if imagenes_fuente else "")[:1000]
                if url_origen:
                    cur.execute(
                        """INSERT INTO Procurement.scraping_farmacias_raw
                           (codbarras, farmacia_origen, url_origen, url_imagen,
                            texto_extraido, LogID)
                           VALUES (?,?,?,?,?,?)""",
                        codbarras, farmacia, url_origen,
                        url_img_principal or None,
                        texto[:50000] or None,
                        log_id,
                    )

        conn.commit()
    except Exception as exc:
        # Trazabilidad falló → no romper el batch. Loguear y seguir.
        log_evento("WARN", "TRAZABILIDAD",
                   f"Fallo persistiendo trazabilidad de {codbarras}: {exc}",
                   codbarras=codbarras, trigger_id=trigger_id,
                   alerta_telegram=False)
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _update_llm_log_score(codbarras: str, score: int, estado: str) -> None:
    """Backfill del ScoreFinal/EstadoCiclo en la última fila de OrquestadorLLMLog
    del codbarras dado. Se llama después de calcular el score final (post-validación),
    ya que la persistencia inicial se hace antes de tener ese dato.
    Best-effort: si falla, no afecta al batch."""
    try:
        conn = pyodbc.connect(_conn_str(), timeout=10)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE Procurement.OrquestadorLLMLog SET ScoreFinal = ?, EstadoCiclo = ? "
                "WHERE LogID = (SELECT MAX(LogID) FROM Procurement.OrquestadorLLMLog WHERE Codbarras = ?)",
                score, estado, codbarras,
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # best-effort


def procesar_trigger_farmaceutico(trigger: dict[str, Any]) -> dict[str, Any]:
    if not check_threshold(trigger):
        return {"status": "skipped", "reason": "threshold_not_met", "TriggerID": trigger.get("TriggerID")}

    productos = fetch_productos_abiertos(BATCH_SIZE)
    if not productos:
        return {"status": "skipped", "reason": "no_products", "TriggerID": trigger.get("TriggerID")}

    os.chdir(REPO_DIR)
    os.environ.setdefault("PROMPT_ARCHIVO", "prompt_agente_v3_solidificado_final.txt")
    os.environ.setdefault("VISION_ACTIVA", "1")
    taxonomias = ev.obtener_taxonomias_estrictas()

    # MDM catalog mapper (numeric IDs against master catalogs)
    catalog = None
    try:
        catalog = MasterCatalog(_conn_str())
    except Exception as exc:
        print(f"[MDM] MasterCatalog no disponible, se escriben solo columnas _Des: {exc}")

    filas: list[dict[str, Any]] = []
    for item in productos:
        codbarras = item["codbarras"]
        desc = item["descripcion"]
        print(f"[MDM] Procesando {codbarras} — {desc[:60]}")

        fuentes, imagenes, urls_encontradas = scrape_producto(codbarras, desc, trigger_id=trigger.get("TriggerID"))
        context_block = [{
            "registro": {
                "codigo": codbarras,
                "codbarras": codbarras,
                "descripcion_original": desc,
                "ciclos_reproceso": item["ciclos_reproceso"],
            },
            "atributos_ya_encontrados": item["atributos_ya_encontrados"],
            "fuentes_web": fuentes,
        }]

        parsed, metricas, raw_content, fotos_guardar = ev.procesar_producto_batch1(
            json.dumps(context_block, ensure_ascii=False),
            taxonomias,
            imagenes,
            desc,
        )
        # Persistir trazabilidad ANTES del early-continue: incluso si el parse
        # falla, queremos registrar el intento (prompt, costo, raw, errores).
        _persistir_trazabilidad(
            codbarras=codbarras,
            trigger_id=trigger.get("TriggerID"),
            metricas=metricas,
            raw_content=raw_content or "",
            fotos=fotos_guardar,
            fuentes=fuentes,
            urls_encontradas=urls_encontradas,
            atrib=(parsed[0].get("atributos_nuevos_consolidados", {}) if isinstance(parsed, list) and parsed
                   else parsed.get("atributos_nuevos_consolidados", {}) if isinstance(parsed, dict)
                   else {}),
            score=None,  # se actualizará abajo cuando tengamos el score final
            estado=None,
        )

        if not parsed:
            print(f"  [MDM] Sin atributos para {codbarras}")
            continue

        if isinstance(parsed, list) and parsed:
            atrib = parsed[0].get("atributos_nuevos_consolidados", {})
        elif isinstance(parsed, dict):
            atrib = parsed.get("atributos_nuevos_consolidados", {})
        else:
            atrib = {}

        if not atrib:
            continue

        clauses, score, estado, ciclos = build_update_clauses(atrib, item["ciclos_reproceso"], item.get("descripcion", ""), catalog)
        costo = (metricas.get("costo_gemini") or 0) + (metricas.get("costo_glm") or 0)
        print(f"  [MDM] OK score={score} estado={estado} costo=${costo:.4f}")
        filas.append({"codbarras": codbarras, "clauses": clauses})

        # Backfill del score/estado en OrquestadorLLMLog: la persistencia se hace
        # antes de calcular el score (para registrar incluso parseos fallidos).
        # Acá ya tenemos el resultado final → actualizamos la última fila del codbarras.
        _update_llm_log_score(codbarras, score, estado)

    escritos = write_rows_to_db(filas, trigger_id=trigger.get("TriggerID"))
    print(f"[MDM] {escritos} filas escritas directo a SQL (sin n8n)")

    log_evento(
        "INFO", "GENERAL",
        f"Batch completado: {len(filas)} procesados, {escritos} escritos, "
        f"{len(productos)} intentados.",
        trigger_id=trigger.get("TriggerID"),
        detalle={"procesados": len(filas), "escritos": escritos, "intentados": len(productos)},
        alerta_telegram=False,  # INFO no flood Telegram; queda en tabla para auditoría
    )

    return {
        "status": "ok",
        "TriggerID": trigger.get("TriggerID"),
        "procesados": len(filas),
        "escritos": escritos,
        "intentados": len(productos),
    }


def procesar_trigger_mercado_vivo(trigger: dict[str, Any]) -> dict[str, Any]:
    if not check_threshold(trigger):
        return {"status": "skipped", "reason": "threshold_not_met", "TriggerID": trigger.get("TriggerID")}

    from etl_mercado_vivo_incremental import main as etl_main

    os.chdir(REPO_DIR)
    etl_main()
    return {"status": "ok", "TriggerID": trigger.get("TriggerID"), "procesados": "etl"}


def handle_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    trigger_id = int(trigger.get("TriggerID") or 0)
    process = (trigger.get("ProcessName") or "").upper()

    if trigger_id == 2 or "MERCADOVIVO" in process:
        return procesar_trigger_mercado_vivo(trigger)
    return procesar_trigger_farmaceutico(trigger)


def run_trigger_async(trigger: dict[str, Any]) -> None:
    def _worker() -> None:
        try:
            result = handle_trigger(trigger)
            print(f"[MDM] Trigger {trigger.get('TriggerID')} finalizado: {result}")
        except Exception as exc:
            print(f"[MDM] Error en trigger {trigger.get('TriggerID')}: {exc}", file=sys.stderr)

    threading.Thread(target=_worker, daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestador local n8n")
    parser.add_argument("--trigger-json", help="JSON del trigger (AutomationTriggers)")
    parser.add_argument("--sync", action="store_true", help="Ejecutar en foreground")
    args = parser.parse_args()

    if args.trigger_json:
        trigger = json.loads(args.trigger_json)
    else:
        trigger = json.load(sys.stdin)

    if args.sync:
        result = handle_trigger(trigger)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    run_trigger_async(trigger)
    print(json.dumps({"status": "accepted", "TriggerID": trigger.get("TriggerID")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
