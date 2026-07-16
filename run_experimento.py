#!/usr/bin/env python3
"""
Runner unico controlado por .env

Uso:
  python3 run_experimento.py
  python3 run_experimento.py --dry-run

TODO sale del .env. No hay experimento.conf ni experiment_config.py.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# === CARGAR .ENV Y CREDENCIALES ===
load_dotenv()
from synapse_cred import load_synapse_credentials
load_synapse_credentials()

from pipeline_logger import set_run_id, log, log_evento, log_producto, log_resumen


def _g(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _gbool(key: str, default: bool = False) -> bool:
    return _g(key, "true" if default else "false").lower() in ("true", "1", "yes", "on")


def _gint(key: str, default: int = 0) -> int:
    raw = _g(key, "")
    return int(raw) if raw else default


def _gfloat(key: str, default: float = 0.0) -> float:
    raw = _g(key, "")
    return float(raw) if raw else default


# === PARAMETROS DESDE .ENV ===

# Credenciales
CREDENCIALES_ARCHIVO = _g("CREDENCIALES_ARCHIVO", "../../N8N/synapse.credentials")

# Ejecucion
DRY_RUN = _gbool("DRY_RUN", False)
SALIDA_DIRECTORIO = _g("SALIDA_DIRECTORIO", "scratch")
SALIDA_ARCHIVO = _g("SALIDA_ARCHIVO", "experimento_resultados.json")

# Seleccion de productos
NUM_PRODUCTOS = _gint("NUM_PRODUCTOS", 5)
EANS = [e.strip() for e in _g("EANS").split(",") if e.strip()]
FILTRO_WHERE = _g("FILTRO_WHERE", "estado_ciclo='ABIERTO'")

# Modelo IA
IA_PROVEEDOR = _g("IA_PROVEEDOR", "zai")
IA_MODELO = _g("IA_MODELO", "glm-4.7")
IA_MAX_TOKENS = _gint("IA_MAX_TOKENS", 4000)
IA_TEMPERATURE = _gfloat("IA_TEMPERATURE", 0.7)
IA_TOP_P = _gfloat("IA_TOP_P", 0.95)

# Modelo IA secundario
IA_PROVEEDOR_SECUNDARIO = _g("IA_PROVEEDOR_SECUNDARIO", "deepseek")
IA_MODELO_SECUNDARIO = _g("IA_MODELO_SECUNDARIO", "deepseek-v4-flash")
IA_MAX_TOKENS_SECUNDARIO = _gint("IA_MAX_TOKENS_SECUNDARIO", 16384)
IA_TEMPERATURE_SECUNDARIO = _gfloat("IA_TEMPERATURE_SECUNDARIO", 0.2)

# Pre-clasificador eliminado — scrapean todo, GLM-4.7 clasifica

# Vision
VISION_ACTIVAR = _gbool("VISION_ACTIVAR", True)
VISION_PROVEEDOR = _g("VISION_PROVEEDOR", "mimo")
VISION_MODELO = _g("VISION_MODELO", "mimo-v2.5")
VISION_API_URL = _g("VISION_API_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
VISION_THINKING = _g("VISION_THINKING", "disabled")

# Fotos
MAX_FOTOS_TOTALES = _gint("MAX_FOTOS_TOTALES", 10)
MAX_FOTOS_PREFILTRO = _gint("MAX_FOTOS_PREFILTRO", 10)
MAX_FOTOS_OCR = _gint("MAX_FOTOS_OCR", 3)
UMBRAL_LEGIBILIDAD = _gint("UMBRAL_LEGIBILIDAD", 3)

# Consenso imagenes
CONSENSO_DESCRIPCION = _gint("CONSENSO_IMAGENES_DESCRIPCION", 3)
CONSENSO_FORMA = _gint("CONSENSO_IMAGENES_FORMA", 2)
CONSENSO_CONCENTRACION = _gint("CONSENSO_IMAGENES_CONCENTRACION", 2)

# Scraping
MAX_FUENTES_WEB = _gint("MAX_FUENTES_WEB", 10)
SCRAPING_DELAY = _gfloat("SCRAPING_DELAY", 0.5)
SCRAPING_REINTENTOS = _gint("SCRAPING_REINTENTOS", 3)
SCRAPING_TEXTO_MAX = _gint("SCRAPING_TEXTO_MAX", 8000)

# Timeouts
TIMEOUT_VISION = _gint("TIMEOUT_VISION", 120)
TIMEOUT_TEXTO = _gint("TIMEOUT_TEXTO", 300)
TIMEOUT_RED = _gint("TIMEOUT_RED", 15)

# Ciclo
SCORE_CIERRE = _gint("SCORE_CIERRE", 88)
SCORE_CIERRE_NO_MED = _gint("SCORE_CIERRE_NO_MED", 70)
MAX_REINTENTOS = _gint("MAX_REINTENTOS", 3)
BATCH_SIZE = _gint("BATCH_SIZE", 5)

# Prompt y taxonomias
PROMPT_ARCHIVO = _g("PROMPT_ARCHIVO", "prompt_agente_v3_solidificado_final.txt")
TAXONOMIAS_CACHE = _g("TAXONOMIAS_CACHE", "scratch/taxonomias_local.txt")


def aplicar_entorno():
    """Pasa todos los valores del .env a os.environ para que evaluate_local y demas los lean."""
    os.environ["GLM_MODEL"] = IA_MODELO
    os.environ["GLM_MAX_TOKENS"] = str(IA_MAX_TOKENS)
    os.environ["GLM_TEMPERATURE"] = str(IA_TEMPERATURE)
    os.environ["GLM_TOP_P"] = str(IA_TOP_P)

    os.environ["DEEPSEEK_MODEL"] = IA_MODELO_SECUNDARIO
    os.environ["DEEPSEEK_MAX_TOKENS"] = str(IA_MAX_TOKENS_SECUNDARIO)

    os.environ["EXPERIMENT_TEXTO_PROVIDER"] = IA_PROVEEDOR

    os.environ["EXPERIMENT_PROMPT_FILE"] = PROMPT_ARCHIVO
    os.environ["EXPERIMENT_TAXONOMIAS_CACHE"] = TAXONOMIAS_CACHE

    os.environ["EXPERIMENT_VISION_ACTIVE"] = "1" if VISION_ACTIVAR else "0"
    os.environ["EXPERIMENT_VISION_PROVIDER"] = VISION_PROVEEDOR
    os.environ["EXPERIMENT_VISION_MODEL"] = VISION_MODELO
    os.environ["EXPERIMENT_VISION_THINKING"] = VISION_THINKING
    os.environ["EXPERIMENT_VISION_MAX_PREFILTRO"] = str(MAX_FOTOS_PREFILTRO)
    os.environ["EXPERIMENT_VISION_MAX_OCR"] = str(MAX_FOTOS_OCR)
    os.environ["EXPERIMENT_VISION_UMBRAL"] = str(UMBRAL_LEGIBILIDAD)
    os.environ["MIMO_API_URL"] = VISION_API_URL
    os.environ["MIMO_MODEL"] = VISION_MODELO
    os.environ["MIMO_THINKING"] = VISION_THINKING

    os.environ["ORQUESTADOR_BATCH_SIZE"] = str(BATCH_SIZE)
    os.environ["ORQUESTADOR_MAX_REINTENTOS"] = str(MAX_REINTENTOS)
    os.environ["ORQUESTADOR_SCORE_CIERRE"] = str(SCORE_CIERRE)
    os.environ["ORQUESTADOR_SCORE_CIERRE_NO_MED"] = str(SCORE_CIERRE_NO_MED)

    os.environ["MAX_FUENTES_WEB"] = str(MAX_FUENTES_WEB)
    os.environ["MAX_FOTOS_TOTALES"] = str(MAX_FOTOS_TOTALES)
    os.environ["SCRAPING_DELAY"] = str(SCRAPING_DELAY)
    os.environ["SCRAPING_REINTENTOS"] = str(SCRAPING_REINTENTOS)
    os.environ["SCRAPING_TEXTO_MAX"] = str(SCRAPING_TEXTO_MAX)

    os.environ["TIMEOUT_VISION"] = str(TIMEOUT_VISION)
    os.environ["TIMEOUT_TEXTO"] = str(TIMEOUT_TEXTO)
    os.environ["TIMEOUT_RED"] = str(TIMEOUT_RED)


def imprimir_plan(productos: list[dict]) -> None:
    print("=" * 72)
    print(f"EXPERIMENTO: {IA_PROVEEDOR} / {IA_MODELO}")
    print(f"  Productos    : {len(productos)}")
    print(f"  Filtro WHERE : {FILTRO_WHERE}")
    print(f"  Vision       : {'ON' if VISION_ACTIVAR else 'OFF'} ({VISION_PROVEEDOR} / {VISION_MODELO})")
    print(f"  Temp GLM     : {IA_TEMPERATURE} (top_p={IA_TOP_P})")
    print(f"  Fotos total  : {MAX_FOTOS_TOTALES} | pre-filtro: {MAX_FOTOS_PREFILTRO} | OCR: {MAX_FOTOS_OCR}")
    print(f"  Consenso     : desc={CONSENSO_DESCRIPCION} forma={CONSENSO_FORMA} conc={CONSENSO_CONCENTRACION}")
    print(f"  Fuente datos : DB REAL (Procurement.por_aprobacion_equivalencias)")
    print(f"  Salida       : {os.path.join(SALIDA_DIRECTORIO, SALIDA_ARCHIVO)}")
    print(f"  dry_run      : {DRY_RUN}")
    print("=" * 72)


def fetch_productos_db() -> list[dict]:
    """Lee productos directamente de la DB real con scraping en vivo."""
    import pyodbc

    server = os.getenv("DB_SERVER", "100.94.5.108,49751")
    database = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "")
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={user};PWD={password};"
        "TrustServerCertificate=yes;Encrypt=yes;"
    )

    timeout_db = int(os.getenv("TIMEOUT_RED", "20"))
    conn = pyodbc.connect(conn_str, timeout=timeout_db)
    try:
        cur = conn.cursor()

        # Si hay EANS especificos, filtrar por ellos
        if EANS:
            placeholders = ",".join(f"'{e}'" for e in EANS)
            query = f"""
                SELECT TOP ({len(EANS)})
                    codigo, codbarras, descrip1art,
                    ISNULL(ciclos_reproceso, 0) AS ciclos_reproceso,
                    principio_activo_Des, concentracion_Des, forma_farmaceutica_Des,
                    fabricante_Des, marca_Des, codigo_atc_Des, clasificacion_insumo_Des,
                    requiere_recipe, blister, generico, cantidad_presentacion,
                    contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
                FROM Procurement.por_aprobacion_equivalencias
                WHERE codbarras IN ({placeholders})
                ORDER BY ISNULL(LastUpdated, '1900-01-01') ASC
            """
        else:
            limit = NUM_PRODUCTOS if NUM_PRODUCTOS > 0 else 999999
            query = f"""
                SELECT TOP ({limit})
                    codigo, codbarras, descrip1art,
                    ISNULL(ciclos_reproceso, 0) AS ciclos_reproceso,
                    principio_activo_Des, concentracion_Des, forma_farmaceutica_Des,
                    fabricante_Des, marca_Des, codigo_atc_Des, clasificacion_insumo_Des,
                    requiere_recipe, blister, generico, cantidad_presentacion,
                    contenido_neto, contenido_neto_unidad_Des, segmento_etario, origen_Des
                FROM Procurement.por_aprobacion_equivalencias
                WHERE {FILTRO_WHERE}
                ORDER BY ISNULL(LastUpdated, '1900-01-01') ASC
            """

        cur.execute(query)
        rows = cur.fetchall()
    finally:
        conn.close()

    keys = [
        "principio_activo", "concentracion", "forma_farmaceutica", "fabricante", "marca",
        "codigo_atc", "clasificacion_insumo_Des", "requiere_recipe", "blister", "generico",
        "cantidad_presentacion", "contenido_neto", "contenido_neto_unidad_Des",
        "segmento_etario", "origen",
    ]

    productos = []
    for row in rows:
        ya = {}
        for idx, key in enumerate(keys):
            val = row[4 + idx]
            if val is not None and str(val).strip() != "":
                ya[key] = val
        productos.append({
            "ean": row[1],
            "descripcion": row[2],
            "codigo": row[0],
            "ciclos_reproceso": int(row[3]),
            "atributos_ya_encontrados": ya,
        })

    return productos


def enriquecer_con_scraping(productos: list[dict]) -> list[dict]:
    """Para cada producto: buscar en web + descargar imagenes (scraping en vivo)."""
    import orquestador_scraper as scrap

    max_fuentes = int(os.getenv("MAX_FUENTES_WEB", "10"))
    max_fotos = int(os.getenv("MAX_FOTOS_TOTALES", "10"))
    delay = float(os.getenv("SCRAPING_DELAY", "0.5"))

    enriquecidos = []
    for item in productos:
        codbarras = item["ean"]
        desc = item["descripcion"]
        print(f"  [scrap] {codbarras} — {desc[:50]}")

        fuentes, imagenes = [], []
        is_internal = codbarras.startswith("BLI_") or len(codbarras) != 13

        if not is_internal:
            urls = scrap.buscar_en_internet(f'"{codbarras}" {desc}', max_fuentes=max_fuentes)
            for idx, url in enumerate(urls, 1):
                fuente = scrap.extraer_fuente_web(url, idx, desc)
                if fuente:
                    fuentes.append(fuente)
                    imagenes.extend(fuente.get("imagenes_encontradas", []))
                    if len(set(imagenes)) >= max_fotos:
                        break
                time.sleep(delay)

        enriquecidos.append({
            **item,
            "fuentes_web": fuentes,
            "imagenes_b64": list(dict.fromkeys(imagenes))[:max_fotos],
        })

    return enriquecidos


def main() -> int:
    aplicar_entorno()
    set_run_id()

    # 1. Leer productos de la DB real
    log("Leyendo productos de la DB real...")
    productos = fetch_productos_db()
    if not productos:
        log("No se encontraron productos con el filtro especificado.", "ERROR")
        return 1

    log(f"{len(productos)} productos seleccionados")
    log_evento("productos_seleccionados", cantidad=len(productos), filtro=FILTRO_WHERE)

    # 2. Scrape en vivo
    log("Scraping web en vivo (fuentes + imagenes)...")
    productos = enriquecer_con_scraping(productos)
    log_evento("scraping_completado", productos=len(productos))

    imprimir_plan(productos)

    # 3. Dry run?
    if DRY_RUN:
        log("[dry_run] No se llaman APIs. Cambia DRY_RUN=false en .env para ejecutar.", "WARN")
        return 0

    # 4. Ejecutar pipeline
    log("Iniciando evaluacion con APIs reales...")
    log_evento("pipeline_inicio", modelo=IA_MODELO, proveedor=IA_PROVEEDOR)

    input_path = os.path.join(SALIDA_DIRECTORIO, "input_vivo.json")
    output_path = os.path.join(SALIDA_DIRECTORIO, SALIDA_ARCHIVO)
    Path(SALIDA_DIRECTORIO).mkdir(parents=True, exist_ok=True)

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=2, ensure_ascii=False)

    import evaluate_local as runner
    runner.main(input_path=input_path, output_path=output_path)

    log(f"Experimento completado. Resultados: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
