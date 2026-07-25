"""
Sistema de logging dual para el pipeline de clasificacion.

Genera dos archivos por ejecucion:
  1. .log  — texto legible con timestamps (para humanos)
  2. .jsonl — un JSON por linea (para pandas/jq/analisis)

Uso:
  from pipeline_logger import log, log_evento, log_producto, set_run_id
  set_run_id()  # auto-genera timestamp unico
  log("Iniciando pipeline...")
  log_producto(ean, score, costo, tiempo, atributos)
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

_RUN_ID: str = ""
_LOG_DIR: str = ""
_LOG_FILE: str = ""
_JSONL_FILE: str = ""
_TIEMPO_INICIO: float = 0.0


def set_run_id(nombre: str = "") -> str:
    """Inicializa el run. Crea directorio de logs y devuelve el run_id."""
    global _RUN_ID, _LOG_DIR, _LOG_FILE, _JSONL_FILE, _TIEMPO_INICIO

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    _RUN_ID = nombre or f"run_{ts}"
    _TIEMPO_INICIO = time.time()

    log_activar = os.getenv("LOG_ACTIVAR", "true").lower() in ("true", "1", "yes")
    log_json = os.getenv("LOG_JSON", "false").lower() in ("true", "1", "yes")

    if log_activar:
        salida_dir = os.getenv("SALIDA_DIRECTORIO", "scratch")
        _LOG_DIR = os.path.join(salida_dir, "logs")
        Path(_LOG_DIR).mkdir(parents=True, exist_ok=True)
        _LOG_FILE = os.path.join(_LOG_DIR, f"{_RUN_ID}.log")
        if log_json:
            _JSONL_FILE = os.path.join(_LOG_DIR, f"{_RUN_ID}.jsonl")
        else:
            _JSONL_FILE = ""
    else:
        _LOG_DIR = ""
        _LOG_FILE = ""
        _JSONL_FILE = ""

    return _RUN_ID


def get_run_id() -> str:
    return _RUN_ID


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _segundos_run() -> float:
    if _TIEMPO_INICIO:
        return round(time.time() - _TIEMPO_INICIO, 2)
    return 0.0


def log(mensaje: str, nivel: str = "INFO") -> None:
    """Escribe una linea al .log legible y la imprime a stdout."""
    linea = f"[{_ts()}] [{nivel:5s}] [+{_segundos_run():>8.1f}s] {mensaje}"
    print(linea)
    if _LOG_FILE:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea + "\n")


def log_evento(evento: str, **datos) -> None:
    """Escribe un evento estructurado al .jsonl y al .log."""
    registro = {
        "timestamp": _ts(),
        "run_id": _RUN_ID,
        "t_segundos": _segundos_run(),
        "evento": evento,
        **datos,
    }

    if _JSONL_FILE:
        with open(_JSONL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")

    nivel = datos.get("nivel", "INFO")
    resumen = f"{evento}"
    if datos:
        partes = [f"{k}={v}" for k, v in datos.items() if k not in ("nivel",)]
        resumen += " | " + " ".join(partes)
    log(resumen, nivel)


def log_producto(
    ean: str,
    descripcion: str,
    score: int | None = None,
    costo: float = 0.0,
    tiempo: float = 0.0,
    exito: bool = False,
    atributos: dict | None = None,
    error: str | None = None,
    modelo: str = "",
    fuentes_web: int = 0,
    imagenes: int = 0,
    ocr_aprobadas: int = 0,
) -> None:
    """Registra el resultado completo de un producto procesado."""
    atributos = atributos or {}
    registro = {
        "timestamp": _ts(),
        "run_id": _RUN_ID,
        "t_segundos": _segundos_run(),
        "evento": "producto",
        "ean": ean,
        "descripcion": descripcion[:120],
        "exito": exito,
        "score": score,
        "costo_usd": round(costo, 6),
        "tiempo_s": round(tiempo, 2),
        "modelo": modelo,
        "fuentes_web": fuentes_web,
        "imagenes_descargadas": imagenes,
        "ocr_aprobadas": ocr_aprobadas,
        "principio_activo": atributos.get("principio_activo"),
        "concentracion": atributos.get("concentracion"),
        "forma_farmaceutica": atributos.get("forma_farmaceutica"),
        "codigo_atc": atributos.get("codigo_atc"),
        "fabricante": atributos.get("fabricante"),
        "generico": atributos.get("generico"),
        "confianza_nivel": atributos.get("confianza_nivel"),
        "estado_ciclo": atributos.get("estado_ciclo"),
        "error": error,
    }

    if _JSONL_FILE:
        with open(_JSONL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")

    # Resumen legible
    status = "✓" if exito else "✗"
    log(
        f"{status} EAN {ean} | score={score} | costo=${costo:.4f} | {tiempo:.1f}s | "
        f"fuentes={fuentes_web} imgs={imagenes} ocr={ocr_aprobadas} | "
        f"{atributos.get('principio_activo', '?')} {atributos.get('concentracion', '?')}",
        "INFO" if exito else "WARN",
    )


def log_resumen(metricas: dict) -> None:
    """Registra el resumen final de la ejecucion."""
    log_evento("resumen", **metricas)
    log("=" * 72)
    log(f"RESUMEN FINAL | run_id={_RUN_ID}")
    log(f"  Productos OK : {metricas.get('productos_exitosos', 0)}")
    log(f"  Productos FAIL: {metricas.get('productos_fallidos', 0)}")
    log(f"  Tiempo total : {metricas.get('tiempo_total', 0):.1f}s")
    log(f"  Costo total  : ${metricas.get('costo_total', 0):.4f}")
    log(f"  Llamadas IA  : vision={metricas.get('total_llamadas_vision', 0)} texto={metricas.get('total_llamadas_texto', 0)}")
    log(f"  Log          : {_LOG_FILE}")
    log(f"  JSONL        : {_JSONL_FILE}")
    log("=" * 72)
