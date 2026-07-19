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

import evaluate_local as ev
import orquestador_scraper as scrap
from normalizador_farmaceutico import procesar_farmacos
from MDM_Unified_Mapper import MasterCatalog
from alertas import log_evento

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
                -- EAN-13 primero (scrapeables), códigos internos al final (GLM solo).
                -- No se excluyen: el prompt clasifica igual con solo descrip1art.
                CASE WHEN LEN(codbarras) = 13 AND codbarras NOT LIKE 'BLI_%' THEN 0 ELSE 1 END,
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


def scrape_producto(codbarras: str, descripcion: str, trigger_id: int | None = None) -> tuple[list, list]:
    fuentes_extraidas: list = []
    todas_imagenes: list = []
    is_internal = codbarras.startswith("BLI_") or len(codbarras) != 13

    if is_internal:
        # Alerta: scraping saltado silenciosamente era el bug latente.
        # Ahora queda registrado en tabla + Telegram (WARN) para que se vea.
        log_evento(
            "WARN", "SCRAPER",
            f"Scraping saltado: código interno (len={len(codbarras)}). "
            f"El pipeline correrá sin imágenes ni fuentes web.",
            codbarras=codbarras, trigger_id=trigger_id,
            detalle={"motivo": "codigo_interno", "len": len(codbarras)},
        )
        return [], []

    urls = scrap.buscar_en_internet(f'"{codbarras}" {descripcion}', max_fuentes=MAX_FUENTES_WEB)
    for idx, url in enumerate(urls, 1):
        fuente = scrap.extraer_fuente_web(url, idx, descripcion)
        if fuente:
            fuentes_extraidas.append(fuente)
            todas_imagenes.extend(fuente.get("imagenes_encontradas", []))
            if len(set(todas_imagenes)) >= MAX_FOTOS_TOTALES:
                break
        time.sleep(SCRAPING_DELAY)

    # Alerta: EAN-13 válido pero el scraper no trajo NADA (ValueSERP caído, red, etc.).
    # Sin esto, el modo de fallo "0 fuentes" pasaba silencioso y solo se veía como score bajo.
    if not fuentes_extraidas:
        log_evento(
            "WARN", "SCRAPER",
            f"EAN-13 {codbarras} válido pero el scraper no trajo fuentes ni imágenes. "
            f"Posible caída de ValueSERP o red.",
            codbarras=codbarras, trigger_id=trigger_id,
            detalle={"motivo": "scraper_vacio", "query": f'"{codbarras}" {descripcion}'[:200]},
        )

    return fuentes_extraidas, list(dict.fromkeys(todas_imagenes))[:MAX_FOTOS_TOTALES]


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
    catalog: Any,
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

    atrib["segmento_etario"] = ev.normalizar_segmento_etario(atrib.get("segmento_etario"))
    score = ev.calcular_score_calidad(atrib)
    es_med = not bool(atrib.get("clasificacion_insumo_Des"))

    if score >= SCORE_CIERRE or (not es_med and score >= SCORE_CIERRE_NO_MED):
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
        f"es_medicamento = {0 if atrib.get('clasificacion_insumo_Des') else 1}",
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


def procesar_trigger_farmaceutico(trigger: dict[str, Any]) -> dict[str, Any]:
    if not check_threshold(trigger):
        return {"status": "skipped", "reason": "threshold_not_met", "TriggerID": trigger.get("TriggerID")}

    productos = fetch_productos_abiertos(BATCH_SIZE)
    if not productos:
        return {"status": "skipped", "reason": "no_products", "TriggerID": trigger.get("TriggerID")}

    os.chdir(REPO_DIR)
    os.environ.setdefault("EXPERIMENT_PROMPT_FILE", "prompt_agente_v3_solidificado_final.txt")
    os.environ.setdefault("EXPERIMENT_VISION_ACTIVE", "1")
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

        fuentes, imagenes = scrape_producto(codbarras, desc, trigger_id=trigger.get("TriggerID"))
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

        parsed, metricas, _raw, _fotos = ev.procesar_producto_batch1(
            json.dumps(context_block, ensure_ascii=False),
            taxonomias,
            imagenes,
            desc,
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

        clauses, score, estado, ciclos = build_update_clauses(atrib, item["ciclos_reproceso"], catalog)
        costo = (metricas.get("costo_gemini") or 0) + (metricas.get("costo_glm") or 0)
        print(f"  [MDM] OK score={score} estado={estado} costo=${costo:.4f}")
        filas.append({"codbarras": codbarras, "clauses": clauses})

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
