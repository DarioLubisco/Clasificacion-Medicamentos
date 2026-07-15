"""Carga y valida experimento.conf (formato INI)."""
from __future__ import annotations

import configparser
import json
import os
import random
from pathlib import Path
from typing import Any


class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, option: str) -> str:
        return option


def load_experiment_config(path: str = "experimento.conf") -> dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encuentra {path}")

    parser = CaseSensitiveConfigParser()
    parser.read(path, encoding="utf-8")

    def g(section: str, key: str, fallback: str = "") -> str:
        return parser.get(section, key, fallback=fallback).strip()

    def gbool(section: str, key: str, fallback: bool = False) -> bool:
        return parser.getboolean(section, key, fallback=fallback)

    def gint(section: str, key: str, fallback: int = 0) -> int:
        raw = g(section, key, "")
        return int(raw) if raw else fallback

    eans_raw = g("productos", "eans", "")
    eans = [x.strip() for x in eans_raw.replace("\n", ",").split(",") if x.strip()]

    return {
        "path": path,
        "experimento": {
            "nombre": g("experimento", "nombre"),
            "descripcion": g("experimento", "descripcion"),
            "activo": gbool("experimento", "activo", True),
        },
        "entrada": {
            "modo": g("entrada", "modo", "archivo_json"),
            "archivo_json": g("entrada", "archivo_json", "scratch/eval_from_conf.json"),
            # Dataset real con scraping (fuentes_web + URLs de imágenes), p.ej. eval_20_vision.json
            "archivo_entrada": g("entrada", "archivo_entrada", "scratch/eval_20_vision.json"),
            "archivo_referencia": g("entrada", "archivo_referencia", "scratch/resultados_20_vision.json"),
        },
        "productos": {
            "eans": eans,
            "cantidad": gint("productos", "cantidad", 0),
            "semilla_aleatoria": gint("productos", "semilla_aleatoria", 0),
        },
        "lote": {
            "batch_size": max(1, gint("lote", "batch_size", 1)),
        },
        "modelo_texto": {
            "proveedor": g("modelo_texto", "proveedor", "zai"),
            "modelo": g("modelo_texto", "modelo", "glm-4.7"),
            "temperature": float(g("modelo_texto", "temperature", "0.2") or "0.2"),
            "max_tokens": gint("modelo_texto", "max_tokens", 4000),
        },
        "modelo_vision": {
            "activo": gbool("modelo_vision", "activo", True),
            "modelo": g("modelo_vision", "modelo", "mimo-v2.5"),
            "proveedor": g("modelo_vision", "proveedor", "mimo"),
            "thinking": g("modelo_vision", "thinking", "disabled"),
            "api_url": g("modelo_vision", "api_url", "https://token-plan-sgp.xiaomimimo.com/v1"),
            "umbral_legibilidad": gint("modelo_vision", "umbral_legibilidad", 3),
            "max_imagenes_prefiltro": gint("modelo_vision", "max_imagenes_prefiltro", 10),
            "max_imagenes_ocr": gint("modelo_vision", "max_imagenes_ocr", 3),
        },
        "prompt": {
            "archivo": g("prompt", "archivo", "prompt_agente_v3_solidificado_final.txt"),
        },
        "taxonomias": {
            "modo": g("taxonomias", "modo", "cache_local"),
            "archivo_cache": g("taxonomias", "archivo_cache", "scratch/taxonomias_local.txt"),
        },
        "salida": {
            "directorio": g("salida", "directorio", "scratch"),
            "archivo_resultados": g("salida", "archivo_resultados", "experimento_resultados.json"),
            "archivo_excel": g("salida", "archivo_excel", ""),
            "guardar_incremental": gbool("salida", "guardar_incremental", True),
        },
        "comparativa": {
            "activa": gbool("comparativa", "activa", False),
            "archivo_baseline": g("comparativa", "archivo_baseline", ""),
            "modelo_baseline": g("comparativa", "modelo_baseline", "deepseek_v4_flash"),
            "archivo_reporte": g("comparativa", "archivo_reporte", "scratch/comparativa_experimento.xlsx"),
        },
        "credenciales": {
            "archivo": g("credenciales", "archivo", "../../N8N/synapse.credentials"),
        },
        "ejecucion": {
            "dry_run": gbool("ejecucion", "dry_run", True),
        },
    }


def _cargar_dataset_entrada(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} debe ser un JSON array de productos")
    return data


def _producto_desde_dataset(ean: str, dataset: list[dict]) -> dict:
    for item in dataset:
        if item.get("ean") == ean:
            return {
                "ean": ean,
                "descripcion": item.get("descripcion", ""),
                "fuentes_web": item.get("fuentes_web", []),
                "imagenes_b64": item.get("imagenes_b64", []),
            }
    raise KeyError(f"EAN {ean} no encontrado en dataset de entrada")


def validar_fidelidad_produccion(cfg: dict[str, Any], productos: list[dict]) -> None:
    """Advierte si el experimento no replica el pipeline real."""
    vision_on = cfg["modelo_vision"]["activo"]
    avisos: list[str] = []

    for item in productos:
        ean = item.get("ean", "?")
        fuentes = item.get("fuentes_web") or []
        imagenes = item.get("imagenes_b64") or []

        if not fuentes:
            avisos.append(f"  - EAN {ean}: sin fuentes_web (solo descripción)")
        elif any(isinstance(f, str) and "experimento.conf" in f for f in fuentes):
            avisos.append(f"  - EAN {ean}: fuentes_web sintéticas, no scraping real")

        if vision_on and not imagenes:
            avisos.append(f"  - EAN {ean}: visión ON pero sin imágenes")

    if not vision_on:
        avisos.insert(0, "  - modelo_vision.activo = false (producción siempre usa Gemini pre-filtro + OCR)")

    if avisos:
        print("[ADVERTENCIA] El experimento NO replica producción:")
        for aviso in avisos:
            print(aviso)
        print("  Usa archivo_entrada = scratch/eval_20_vision.json y modelo_vision.activo = true")


def preparar_entrada_json(cfg: dict[str, Any]) -> str:
    entrada = cfg["entrada"]
    productos_cfg = cfg["productos"]
    modo = entrada["modo"]
    out_path = entrada["archivo_json"]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    if modo == "archivo_json":
        if not os.path.exists(out_path):
            raise FileNotFoundError(f"modo=archivo_json pero no existe {out_path}")
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validar_fidelidad_produccion(cfg, data)
        print(f"[entrada] Usando JSON existente: {out_path} ({len(data)} productos)")
        return out_path

    if modo in ("eans_lista", "resultados_previos"):
        dataset_path = entrada["archivo_entrada"]
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Falta dataset de entrada real: {dataset_path}")
        dataset = _cargar_dataset_entrada(dataset_path)

        if modo == "eans_lista":
            eans = productos_cfg["eans"]
            if not eans:
                raise ValueError("modo=eans_lista requiere [productos].eans")
            productos = [_producto_desde_dataset(ean, dataset) for ean in eans]
        else:
            keys = [item["ean"] for item in dataset if item.get("ean")]
            cantidad = productos_cfg["cantidad"] or len(keys)
            semilla = productos_cfg["semilla_aleatoria"]
            if semilla:
                random.seed(semilla)
            seleccion = random.sample(keys, min(cantidad, len(keys)))
            productos = [_producto_desde_dataset(ean, dataset) for ean in seleccion]
    else:
        raise ValueError(f"modo de entrada no soportado: {modo}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(productos, f, indent=2, ensure_ascii=False)

    validar_fidelidad_produccion(cfg, productos)
    print(f"[entrada] Generado {out_path} con {len(productos)} producto(s)")
    return out_path


def resolver_ruta_resultados(cfg: dict[str, Any]) -> str:
    salida = cfg["salida"]
    directorio = salida["directorio"]
    Path(directorio).mkdir(parents=True, exist_ok=True)
    archivo = salida["archivo_resultados"] or "experimento_resultados.json"
    if not os.path.isabs(archivo) and "/" not in archivo and "\\" not in archivo:
        archivo = os.path.join(directorio, archivo)
    return archivo
