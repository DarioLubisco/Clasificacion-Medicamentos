#!/usr/bin/env python3
"""
Runner único controlado por experimento.conf

Uso:
  python3 run_experimento.py
  python3 run_experimento.py --config experimento.conf
  python3 run_experimento.py --solo-preparar
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from experiment_config import (
    load_experiment_config,
    preparar_entrada_json,
    resolver_ruta_resultados,
)


def aplicar_entorno(cfg: dict) -> None:
    cred_path = cfg["credenciales"]["archivo"]
    if os.path.exists(cred_path):
        load_dotenv(cred_path)

    mt = cfg["modelo_texto"]
    os.environ["GLM_MODEL"] = mt["modelo"]
    os.environ["GLM_MAX_TOKENS"] = str(mt["max_tokens"])

    os.environ["EXPERIMENT_PROMPT_FILE"] = cfg["prompt"]["archivo"]
    os.environ["EXPERIMENT_TAXONOMIAS_CACHE"] = cfg["taxonomias"]["archivo_cache"]
    mv = cfg["modelo_vision"]
    os.environ["EXPERIMENT_VISION_ACTIVE"] = "1" if mv["activo"] else "0"
    os.environ["EXPERIMENT_VISION_PROVIDER"] = mv["proveedor"]
    os.environ["EXPERIMENT_VISION_MODEL"] = mv["modelo"]
    os.environ["EXPERIMENT_VISION_THINKING"] = mv.get("thinking", "disabled")
    os.environ["EXPERIMENT_VISION_MAX_PREFILTRO"] = str(mv["max_imagenes_prefiltro"])
    os.environ["EXPERIMENT_VISION_MAX_OCR"] = str(mv["max_imagenes_ocr"])
    os.environ["EXPERIMENT_VISION_UMBRAL"] = str(mv["umbral_legibilidad"])
    if mv.get("api_url"):
        os.environ["MIMO_API_URL"] = mv["api_url"]
    os.environ["MIMO_MODEL"] = mv["modelo"]
    os.environ["MIMO_THINKING"] = mv.get("thinking", "disabled")
    os.environ["EXPERIMENT_CONFIG_PATH"] = cfg["path"]


def imprimir_plan(cfg: dict, input_path: str, output_path: str) -> None:
    exp = cfg["experimento"]
    print("=" * 72)
    print(f"EXPERIMENTO: {exp['nombre']}")
    print(f"  {exp['descripcion']}")
    print("=" * 72)
    print(f"  Config       : {cfg['path']}")
    print(f"  Entrada      : {input_path}")
    print(f"  Salida       : {output_path}")
    print(f"  Batch size   : {cfg['lote']['batch_size']}")
    print(f"  Modelo texto : {cfg['modelo_texto']['proveedor']} / {cfg['modelo_texto']['modelo']}")
    print(f"  Vision       : {'ON' if cfg['modelo_vision']['activo'] else 'OFF'}")
    if cfg["modelo_vision"]["activo"]:
        mv = cfg["modelo_vision"]
        print(f"  Vision prov. : {mv['proveedor']} / {mv['modelo']} (thinking={mv.get('thinking', 'disabled')})")
        if mv["proveedor"] == "mimo":
            print(f"  MiMo URL     : {mv.get('api_url', os.environ.get('MIMO_API_URL', ''))}")
    print(f"  Prompt       : {os.environ.get('EXPERIMENT_PROMPT_FILE')}")
    print(f"  Dataset real : {cfg['entrada']['archivo_entrada']}")
    print(f"  Baseline     : {cfg['comparativa']['archivo_baseline']}")
    print(f"  Comparativa  : {'ON' if cfg['comparativa']['activa'] else 'OFF'}")
    print(f"  dry_run      : {cfg['ejecucion']['dry_run']}")
    print("=" * 72)


def ejecutar_evaluacion(cfg: dict, input_path: str, output_path: str) -> None:
    import evaluate_local as runner
    runner.main(input_path=input_path, output_path=output_path)


def generar_comparativa(cfg: dict, resultado_path: str, input_path: str) -> None:
    comp = cfg["comparativa"]
    baseline_path = comp["archivo_baseline"]
    modelo_baseline = comp["modelo_baseline"]
    reporte_path = comp["archivo_reporte"]

    if not os.path.exists(resultado_path):
        print(f"[comparativa] Sin resultados en {resultado_path}")
        return
    if not os.path.exists(baseline_path):
        print(f"[comparativa] Sin baseline en {baseline_path}")
        return

    with open(resultado_path, "r", encoding="utf-8") as f:
        nuevo = json.load(f)
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(input_path, "r", encoding="utf-8") as f:
        productos = json.load(f)

    filas = []
    for item in productos:
        ean = item["ean"]
        if ean not in baseline:
            continue
        bl = baseline[ean].get(modelo_baseline, {})
        bl_at = bl.get("atrib") or {}
        nv = nuevo.get("resultados_por_producto", {}).get(ean, {})
        nv_at = nv.get("atributos") or {}

        filas.append({
            "EAN": ean,
            "Descripcion": item.get("descripcion", ""),
            "Score_Nuevo": nv.get("score"),
            "Score_Baseline": bl.get("score"),
            "Confianza_Nuevo": nv_at.get("confianza_nivel"),
            "Confianza_Baseline": bl_at.get("confianza_nivel"),
            "Principio_Nuevo": nv_at.get("principio_activo"),
            "Principio_Baseline": bl_at.get("principio_activo"),
            "Concentracion_Nuevo": nv_at.get("concentracion"),
            "Concentracion_Baseline": bl_at.get("concentracion"),
            "Forma_Nuevo": nv_at.get("forma_farmaceutica"),
            "Forma_Baseline": bl_at.get("forma_farmaceutica"),
            "ATC_Nuevo": nv_at.get("codigo_atc"),
            "ATC_Baseline": bl_at.get("codigo_atc"),
            "Registro_Sanitario_Nuevo": nv_at.get("registro_sanitario"),
            "Registro_Sanitario_Baseline": bl_at.get("registro_sanitario"),
            "Exito_Nuevo": nv.get("exito"),
        })

    if not filas:
        print("[comparativa] No hay EANs coincidentes para comparar")
        return

    df = pd.DataFrame(filas)
    Path(reporte_path).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(reporte_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Comparativa")

    print(f"[comparativa] Reporte guardado: {os.path.abspath(reporte_path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecutar experimento desde experimento.conf")
    parser.add_argument("--config", default="experimento.conf", help="Ruta al archivo de control")
    parser.add_argument("--solo-preparar", action="store_true", help="Solo genera JSON de entrada")
    args = parser.parse_args()

    cfg = load_experiment_config(args.config)
    if not cfg["experimento"]["activo"]:
        print("Experimento marcado como inactivo en experimento.conf")
        return 0

    aplicar_entorno(cfg)
    input_path = preparar_entrada_json(cfg)
    output_path = resolver_ruta_resultados(cfg)
    imprimir_plan(cfg, input_path, output_path)

    if args.solo_preparar or cfg["ejecucion"]["dry_run"]:
        if cfg["ejecucion"]["dry_run"] and not args.solo_preparar:
            print("\n[dry_run] No se llaman APIs. Cambia [ejecucion] dry_run = false para ejecutar.")
        return 0

    print("\n>>> Iniciando evaluación con APIs reales...\n")
    ejecutar_evaluacion(cfg, input_path, output_path)

    if cfg["comparativa"]["activa"]:
        generar_comparativa(cfg, output_path, input_path)

    print("\n>>> Experimento completado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
