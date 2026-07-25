"""Cliente de reporte de errores alineado con el protocolo n8n de Synapse.

Solo debe alertar ante problemas de ACCESO a ValueSERP (red, auth, créditos,
caída del proveedor). Un EAN sin resultados orgánicos NO es motivo de alerta.

Uso desde el scraper MDM (Clasificacion Medicamentos):

    from n8n_error_reporter import report_valueserp_access_failure

    report_valueserp_access_failure(
        trigger_id=1,
        ean="1254896321544",
        http_status=503,
        api_message="Service Unavailable",
    )
"""

from __future__ import annotations

import json
import logging
import os
import socket
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_WEBHOOK_URL = "https://n8n.farmaciaamericana.es/webhook/scraper-error-report"
DEFAULT_ORIGIN_IP = os.getenv("DEBIAN_HOST_IP", "10.147.18.4")
DEFAULT_WORKFLOW_ID = "AAnxxGYtgg5sD0o8"
DEFAULT_WORKFLOW_NAME = "[PROD] Orquestador Clasificador (Ventanas)"


def _post_alert(payload: dict[str, Any]) -> bool:
    webhook_url = os.getenv("N8N_SCRAPER_ERROR_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
    token = os.getenv("N8N_SCRAPER_ERROR_TOKEN", "")

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Synapse-Webhook-Token"] = token

    request = urllib.request.Request(webhook_url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            if response.status >= 400:
                logger.error("n8n webhook respondió %s: %s", response.status, body)
                return False
            logger.info("Alerta enviada a n8n: %s", body)
            return True
    except urllib.error.HTTPError as exc:
        logger.error("n8n webhook HTTP %s: %s", exc.code, exc.read().decode("utf-8", errors="replace"))
        return False
    except (urllib.error.URLError, socket.timeout) as exc:
        logger.error("No se pudo contactar el webhook n8n: %s", exc)
        return False


def report_external_error(
    *,
    severity: str = "warning",
    service_name: str,
    diagnosis: str,
    probable_causes: str,
    native_log: str,
    destination_entity: str,
    title: str | None = None,
    origin_entity: str = "Servidor Debian Webservices",
    origin_ip: str | None = None,
    trigger_id: int | None = None,
    workflow_id: str = DEFAULT_WORKFLOW_ID,
    workflow_name: str = DEFAULT_WORKFLOW_NAME,
    context: dict[str, Any] | None = None,
) -> bool:
    """Envía una alerta estructurada al flujo [PROD] External Error Reporter (Scraper)."""
    if trigger_id is not None and "[T" not in service_name:
        service_name = f"{service_name} [T{trigger_id}]"

    payload = {
        "severity": severity,
        "title": title,
        "service_name": service_name,
        "origin_entity": origin_entity,
        "origin_ip": origin_ip or DEFAULT_ORIGIN_IP,
        "destination_entity": destination_entity,
        "diagnosis": diagnosis,
        "probable_causes": probable_causes,
        "native_log": native_log,
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "context": context or {},
    }
    return _post_alert(payload)


def is_valueserp_access_failure(
    *,
    http_status: int | None = None,
    organic_count: int | None = None,
    api_message: str | None = None,
    request_success: bool | None = None,
    access_error: str | None = None,
) -> bool:
    """True solo si hay un problema de acceso/servicio, no si el EAN no tiene resultados."""
    if access_error:
        return True

    if http_status is None:
        return True

    if http_status >= 400:
        return True

    if request_success is False:
        return True

    # Respuesta HTTP OK pero la API indica fallo en el cuerpo (sin status HTTP de error).
    if api_message:
        lowered = api_message.lower()
        failure_markers = (
            "invalid api",
            "api key",
            "payment required",
            "run out of",
            "rate limit",
            "too many requests",
            "service unavailable",
            "internal server error",
            "sign up for a plan",
        )
        if any(marker in lowered for marker in failure_markers):
            return True

    # API respondió correctamente: sin alerta aunque el EAN no tenga resultados.
    if http_status < 400 and (request_success is None or request_success is True):
        return False

    return True


def log_valueserp_no_results(
    *,
    trigger_id: int,
    ean: str,
    http_status: int | None = None,
    organic_count: int | None = None,
    query: str | None = None,
) -> None:
    """Registra en log un producto sin resultados, sin generar alerta."""
    logger.info(
        "ValueSERP sin resultados para EAN %s [T%s] (%s, organic_results=%s, query=%s)",
        ean,
        trigger_id,
        f"http_status={http_status}" if http_status is not None else "http_status=desconocido",
        organic_count,
        query or ean,
    )


def report_valueserp_access_failure(
    *,
    trigger_id: int,
    ean: str,
    http_status: int | None = None,
    organic_count: int | None = None,
    api_message: str | None = None,
    request_success: bool | None = None,
    query: str | None = None,
    access_error: str | None = None,
) -> bool:
    """Alerta solo si ValueSERP no es accesible o devuelve error de servicio."""
    if not is_valueserp_access_failure(
        http_status=http_status,
        organic_count=organic_count,
        api_message=api_message,
        request_success=request_success,
        access_error=access_error,
    ):
        log_valueserp_no_results(
            trigger_id=trigger_id,
            ean=ean,
            http_status=http_status,
            organic_count=organic_count,
            query=query,
        )
        return False

    status_part = f"http_status={http_status}" if http_status is not None else "http_status=sin_respuesta"
    organic_part = f"organic_results={organic_count}" if organic_count is not None else "organic_results=desconocido"
    api_part = f"api_message={api_message}" if api_message else "api_message=sin_mensaje"
    query_part = f"query={query or ean}"
    error_part = f"access_error={access_error}" if access_error else ""

    if access_error:
        causes = "Timeout, error de red o imposibilidad de contactar api.valueserp.com."
        diagnosis = f"No se pudo acceder a ValueSERP mientras se procesaba el producto {ean}."
        title = "Fallo de acceso a ValueSERP"
    elif http_status in (402,):
        causes = "Créditos de ValueSERP agotados o problema de facturación (HTTP 402)."
        diagnosis = "ValueSERP rechazó la solicitud por créditos o facturación."
        title = "ValueSERP sin créditos"
    elif http_status in (429,):
        causes = "Rate limit de ValueSERP alcanzado (HTTP 429). Reintentar con backoff."
        diagnosis = "ValueSERP bloqueó la solicitud por exceso de peticiones."
        title = "ValueSERP rate limit"
    elif http_status in (401, 403):
        causes = "API key inválida o no autorizada en ValueSERP."
        diagnosis = "ValueSERP rechazó la autenticación de la API key."
        title = "ValueSERP no autorizado"
    elif http_status and http_status >= 500:
        causes = "ValueSERP respondió con error de servidor. Posible incidente del proveedor."
        diagnosis = f"ValueSERP devolvió HTTP {http_status} (fallo del proveedor)."
        title = "ValueSERP caído o degradado"
    elif request_success is False or api_message:
        causes = "ValueSERP respondió con error lógico en el cuerpo de la API."
        diagnosis = f"ValueSERP reportó fallo de servicio al consultar el producto {ean}."
        title = "ValueSERP respondió con error"
    else:
        causes = "No se pudo completar la consulta a ValueSERP."
        diagnosis = f"Fallo de acceso a ValueSERP para el producto {ean}."
        title = "Fallo de acceso a ValueSERP"

    native_log = ", ".join(part for part in [status_part, organic_part, api_part, query_part, error_part] if part)

    return report_external_error(
        severity="warning",
        service_name="MDM_Farmaceutico_Scraper",
        trigger_id=trigger_id,
        title=title,
        destination_entity="ValueSERP API (api.valueserp.com)",
        diagnosis=diagnosis,
        probable_causes=causes,
        native_log=native_log,
        context={
            "ean": ean,
            "trigger_id": trigger_id,
            "http_status": http_status,
            "organic_count": organic_count,
            "api_message": api_message,
            "request_success": request_success,
            "access_error": access_error,
            "query": query or ean,
        },
    )


def report_valueserp_no_urls(
    *,
    trigger_id: int,
    ean: str,
    http_status: int | None = None,
    organic_count: int | None = None,
    api_message: str | None = None,
    request_success: bool | None = None,
    query: str | None = None,
    access_error: str | None = None,
) -> bool:
    """Alias retrocompatible: solo alerta si hay fallo de acceso, no por EAN sin resultados."""
    return report_valueserp_access_failure(
        trigger_id=trigger_id,
        ean=ean,
        http_status=http_status,
        organic_count=organic_count,
        api_message=api_message,
        request_success=request_success,
        query=query,
        access_error=access_error,
    )


def report_scraper_critical(
    *,
    trigger_id: int,
    diagnosis: str,
    probable_causes: str,
    native_log: str,
    destination_entity: str = "MSSQL Server (EnterpriseAdmin_AMC)",
    context: dict[str, Any] | None = None,
) -> bool:
    return report_external_error(
        severity="critical",
        service_name="MDM_Farmaceutico_Scraper",
        trigger_id=trigger_id,
        destination_entity=destination_entity,
        diagnosis=diagnosis,
        probable_causes=probable_causes,
        native_log=native_log,
        context=context,
    )
