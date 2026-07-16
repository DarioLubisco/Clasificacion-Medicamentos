"""
API HTTP local compatible con el contrato antiguo de synapse-api.

n8n llama POST /api/orquestador/start con la fila de AutomationTriggers.
"""
from __future__ import annotations

import os
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from synapse_cred import load_synapse_credentials

load_synapse_credentials()

from orquestador_produccion import handle_trigger

app = FastAPI(title="MDM Orquestador Local", version="1.0.0")


class TriggerPayload(BaseModel):
    TriggerID: int | None = None
    ProcessName: str | None = None
    CheckQuery: str | None = None
    ThresholdValue: int | None = None
    ExecutionTarget: str | None = None
    ActionCommand: str | None = None
    IsActive: bool | None = None
    LastTriggered: str | None = None

    class Config:
        extra = "allow"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mdm-orquestador-local"}


@app.get("/api/orquestador/status")
def status() -> dict[str, str]:
    return {
        "agent": "Orquestador Local V11",
        "model": os.getenv("GLM_MODEL", "glm-4.7"),
        "status": "online",
    }


@app.post("/api/orquestador/start")
def start(trigger: TriggerPayload, background_tasks: BackgroundTasks) -> dict[str, Any]:
    payload = trigger.model_dump()
    background_tasks.add_task(handle_trigger, payload)
    return {
        "status": "accepted",
        "TriggerID": payload.get("TriggerID"),
        "agent": "Orquestador Local V11",
    }


if __name__ == "__main__":
    port = int(os.getenv("ORQUESTADOR_API_PORT", "8012"))
    uvicorn.run("orquestador_local_api:app", host="0.0.0.0", port=port, reload=False)
