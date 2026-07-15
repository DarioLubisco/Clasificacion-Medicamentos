"""Carga credenciales desde el archivo único del workspace Synapse."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# /home/synapse/source/N8N/synapse.credentials
SYNAPSE_CREDENTIALS_PATH = Path(__file__).resolve().parents[2] / "N8N" / "synapse.credentials"


def load_synapse_credentials() -> Path:
    """Carga synapse.credentials y devuelve la ruta usada."""
    path = os.getenv("SYNAPSE_CREDENTIALS_PATH", str(SYNAPSE_CREDENTIALS_PATH))
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No se encuentra synapse.credentials en {path}. "
            "Define SYNAPSE_CREDENTIALS_PATH o verifica N8N/synapse.credentials."
        )
    load_dotenv(path)
    return Path(path)
