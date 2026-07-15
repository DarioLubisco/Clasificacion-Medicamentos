"""
Orquestador n8n → pipeline local (scraper + evaluate_local).

Recibe el payload de Config.AutomationTriggers (mismo contrato que el antiguo
synapse-api /api/orquestador/start), procesa un lote incremental y devuelve
resultados al webhook n8n `osint-resultados`.
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
import requests

from synapse_cred import load_synapse_credentials

load_synapse_credentials()

import evaluate_local as ev
import orquestador_scraper as scrap
from limpiador_farmaceutico_regex import procesar_farmacos

REPO_DIR = Path(__file__).resolve().parent
BATCH_SIZE = int(os.getenv("ORQUESTADOR_BATCH_SIZE", "5"))
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://n8n.farmaciaamericana.es/webhook/osint-resultados",
)
MAX_REINTENTOS = int(os.getenv("ORQUESTADOR_MAX_REINTENTOS", "3"))
SCORE_CIERRE = int(os.getenv("ORQUESTADOR_SCORE_CIERRE", "88"))


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
    return pyodbc.connect(_conn_str(), timeout=20)


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
                codigo, codbarras, descrip1art,
                ISNULL(ciclos_reproceso, 0) AS ciclos_reproceso,
                principio_activo_Des, concentracion_Des, forma_farmaceutica_Des,
                fabricante_Des, marca_Des, codigo_atc_Des, clasificacion_insumo_Des,
                requiere_recipe, blister, generico, cantidad_presentacion,
                contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
            FROM Procurement.por_aprobacion_equivalencias
            WHERE estado_ciclo = 'ABIERTO'
            ORDER BY ISNULL(LastUpdated, '1900-01-01') ASC
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    productos = []
    keys = [
        "principio_activo", "concentracion", "forma_farmaceutica", "fabricante", "marca",
        "codigo_atc", "clasificacion_insumo_Des", "requiere_recipe", "blister", "generico",
        "cantidad_presentacion", "contenido_neto", "contenido_neto_unidad_Des",
        "segmento_etario", "origen",
    ]
    for row in rows:
        ya = {}
        for idx, key in enumerate(keys):
            val = row[4 + idx]
            if val is not None and str(val).strip() != "":
                ya[key] = val
        productos.append({
            "codigo": row[0],
            "codbarras": row[1],
            "descripcion": row[2],
            "ciclos_reproceso": int(row[3]),
            "atributos_ya_encontrados": ya,
        })
    return productos


def scrape_producto(codbarras: str, descripcion: str) -> tuple[list, list]:
    fuentes_extraidas: list = []
    todas_imagenes: list = []
    is_internal = codbarras.startswith("BLI_") or len(codbarras) != 13
    is_med = scrap.pre_clasificar_medicamento(descripcion)

    if not is_med:
        return fuentes_extraidas, todas_imagenes

    if not is_internal:
        urls = scrap.buscar_en_internet(f'"{codbarras}" {descripcion}', max_fuentes=10)
        for idx, url in enumerate(urls, 1):
            fuente = scrap.extraer_fuente_web(url, idx, descripcion)
            if fuente:
                fuentes_extraidas.append(fuente)
                todas_imagenes.extend(fuente.get("imagenes_encontradas", []))
                if len(set(todas_imagenes)) >= 10:
                    break
            time.sleep(0.5)

    return fuentes_extraidas, list(dict.fromkeys(todas_imagenes))[:10]


def _sql_val(val: Any) -> Any:
    if val is None or str(val).strip() in ("", "None"):
        return None
    return val


def atributos_a_fila_sql(
    codbarras: str,
    codigo: str,
    atrib: dict[str, Any],
    ciclos_reproceso: int,
    modelo: str,
) -> dict[str, Any]:
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

    if score >= SCORE_CIERRE or (not es_med and score >= 70):
        estado_ciclo = "CERRADO"
        ciclos_final = ciclos_reproceso
    elif ciclos_reproceso >= MAX_REINTENTOS:
        estado_ciclo = "AGOTADO"
        ciclos_final = ciclos_reproceso
    else:
        estado_ciclo = "ABIERTO"
        ciclos_final = ciclos_reproceso + 1

    return {
        "codigo": codigo or codbarras,
        "codbarras": codbarras,
        "principio_activo_Des": _sql_val(atrib.get("principio_activo")),
        "concentracion_Des": _sql_val(atrib.get("concentracion")),
        "forma_farmaceutica_Des": _sql_val(atrib.get("forma_farmaceutica")),
        "codigo_atc_Des": _sql_val(atrib.get("codigo_atc")),
        "codigo_atc_profundo_Des": _sql_val(atrib.get("codigo_atc_profundo")),
        "modelo_ia_Des": modelo,
        "requiere_recipe_Des": 1 if atrib.get("requiere_recipe") else 0,
        "generico_Des": 1 if atrib.get("generico") else 0,
        "segmento_etario_Des": atrib.get("segmento_etario"),
        "origen_Des": _sql_val(atrib.get("origen")),
        "fabricante_Des": _sql_val(atrib.get("fabricante")),
        "marca_Des": _sql_val(atrib.get("marca")),
        "contenido_neto_Des": _sql_val(atrib.get("contenido_neto")),
        "cantidad_presentacion_Des": atrib.get("cantidad_presentacion"),
        "score_calidad": score,
        "estado_ciclo": estado_ciclo,
        "ciclos_reproceso": ciclos_final,
        "observaciones_ia": observaciones[:500] if observaciones else None,
        "origen_dato": "IA_INVESTIGATED_V11_ORCHESTRATOR",
        "es_medicamento": 0 if atrib.get("clasificacion_insumo_Des") else 1,
    }


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
    modelo = ev.GLM_MODEL

    filas: list[dict[str, Any]] = []
    for item in productos:
        codbarras = item["codbarras"]
        desc = item["descripcion"]
        print(f"[MDM] Procesando {codbarras} — {desc[:60]}")

        fuentes, imagenes = scrape_producto(codbarras, desc)
        context_block = [{
            "registro": {
                "codigo": item["codigo"],
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

        filas.append(atributos_a_fila_sql(
            codbarras, item["codigo"], atrib, item["ciclos_reproceso"], modelo,
        ))
        costo = (metricas.get("costo_gemini") or 0) + (metricas.get("costo_glm") or 0)
        print(f"  [MDM] OK score={filas[-1]['score_calidad']} costo=${costo:.4f}")

    if filas:
        post_webhook(trigger.get("TriggerID"), filas)

    return {
        "status": "ok",
        "TriggerID": trigger.get("TriggerID"),
        "procesados": len(filas),
        "intentados": len(productos),
    }


def procesar_trigger_mercado_vivo(trigger: dict[str, Any]) -> dict[str, Any]:
    if not check_threshold(trigger):
        return {"status": "skipped", "reason": "threshold_not_met", "TriggerID": trigger.get("TriggerID")}

    from etl_mercado_vivo_incremental import main as etl_main

    os.chdir(REPO_DIR)
    etl_main()
    return {"status": "ok", "TriggerID": trigger.get("TriggerID"), "procesados": "etl"}


def post_webhook(trigger_id: int | None, filas: list[dict[str, Any]]) -> None:
    payload = {"TriggerID": trigger_id, "data": filas}
    resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
    resp.raise_for_status()
    print(f"[MDM] Webhook enviado ({len(filas)} filas) → {resp.status_code}")


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
