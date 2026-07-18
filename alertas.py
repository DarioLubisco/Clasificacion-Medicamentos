"""
Sistema de alertas y logging del orquestador farmacéutico.

Dos canales independientes (si uno falla, el otro igual registra):

1. Tabla SQL `Procurement.OrquestadorLog` — histórico consultable, métricas, auditoría.
2. Telegram directo (bot AMC_NOTIFICACION_BOT → chat ERROR_CHAT_ID) — alerta inmediata al humano.
   Mismo bot y chat que usan los workflows de n8n, para converger todas las alertas.

Diseño:
- `log_evento(severidad, componente, mensaje, ...)` — SIEMPRE escribe a la tabla SQL.
  Severidad ERROR o WARN → además envía Telegram.
- Sin n8n: Python habla directo con SQL Server y con la API de Telegram.
- Credenciales vienen de synapse.credentials (cargadas por synapse_cred / el wrapper).

Uso típico desde orquestador_produccion.py:
    from alertas import log_evento
    log_evento("WARN", "SCRAPER", f"Sin scraping para {codbarras} (código interno)",
               codbarras=codbarras, trigger_id=trigger_id)
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Optional

import pyodbc


def _conn_str() -> str:
    server = os.getenv("DB_SERVER", "100.94.5.108,49751")
    # si vino como instancia nombrada (\efficacis3), forzar puerto explícito
    if "\\" in server:
        server = server.split("\\")[0] + ",49751"
    database = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "")
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={user};PWD={password};"
        "TrustServerCertificate=yes;Encrypt=yes;"
    )


def _to_db_log(
    severidad: str,
    componente: str,
    mensaje: str,
    codbarras: Optional[str],
    trigger_id: Optional[int],
    detalle: Optional[str],
) -> bool:
    """Escribe una fila en Procurement.OrquestadorLog. Devuelve True si OK."""
    try:
        conn = pyodbc.connect(_conn_str(), timeout=10)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Procurement.OrquestadorLog "
                "(Severidad, Componente, Mensaje, Codbarras, TriggerID, Detalle) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                severidad,
                componente,
                mensaje[:1000],
                codbarras,
                trigger_id,
                detalle,
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        # Si ni siquiera podemos loguear a BD, al menos que quede en stderr.
        # No propagar: el orquestador no debe caer por no poder loguear.
        import sys
        print(f"[alertas] No se pudo escribir a OrquestadorLog: {exc}", file=sys.stderr)
        return False


def _to_telegram(texto: str) -> bool:
    """Envía un mensaje directo a Telegram (bot AMC_NOTIFICACION_BOT → ERROR_CHAT_ID).
    Usa el mismo bot y chat que los workflows de n8n, para que todas las alertas
    del sistema converjan en el mismo lugar."""
    bot = os.getenv("TELEGRAM_AMC_NOTIFICACION_BOT")
    chat = os.getenv("ERROR_CHAT_ID")
    if not bot or not chat:
        return False
    url = f"https://api.telegram.org/bot{bot}/sendMessage"
    payload = json.dumps({"chat_id": chat, "text": texto, "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        import sys
        print(f"[alertas] Telegram falló: {exc}", file=sys.stderr)
        return False


def log_evento(
    severidad: str,
    componente: str,
    mensaje: str,
    codbarras: Optional[str] = None,
    trigger_id: Optional[int] = None,
    detalle: Optional[Any] = None,
    alerta_telegram: Optional[bool] = None,
) -> None:
    """Registra un evento del orquestador.

    - severidad: 'INFO', 'WARN', 'ERROR'
    - componente: 'SCRAPER', 'VISION', 'LLM', 'WRITER', 'GENERAL'
    - mensaje: descripción corta (max 1000 chars, se trunca)
    - codbarras/trigger_id: contexto del producto/lote (opcionales)
    - detalle: objeto arbitrario (dict, str) — se serializa a JSON si no es str
    - alerta_telegram: si None, se infiere (ERROR/WARN → True). Pasar False para silenciar.

    Siempre escribe a la tabla SQL. Si severidad es ERROR/WARN (o alerta_telegram=True),
    también manda Telegram. Si Telegram falla, no afecta nada más.
    """
    sev = (severidad or "INFO").upper().strip()
    comp = (componente or "GENERAL").upper().strip()
    if alerta_telegram is None:
        alerta_telegram = sev in ("WARN", "ERROR")

    detalle_str = detalle if isinstance(detalle, str) else (
        json.dumps(detalle, ensure_ascii=False, default=str) if detalle is not None else None
    )

    _to_db_log(sev, comp, mensaje, codbarras, trigger_id, detalle_str)

    if alerta_telegram:
        tag = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "🔴"}.get(sev, "•")
        cb = f" <code>{codbarras}</code>" if codbarras else ""
        tid = f" [T{trigger_id}]" if trigger_id else ""
        texto = f"{tag} <b>{comp}</b>{tid}{cb}\n{mensaje}"
        _to_telegram(texto)
