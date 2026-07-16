#!/usr/bin/env python3
"""Despliega el orquestador local V11 al servidor Debian (10.147.18.204)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = os.getenv("MDM_DEPLOY_HOST", "10.147.18.204")
USER = os.getenv("MDM_DEPLOY_USER", "root")
PASS = os.getenv("MDM_DEPLOY_PASSWORD", "Twinc3pt.2")
LOCAL = Path(__file__).resolve().parent
REMOTE = "/home/synapse/clasificacion"
CREDS = os.getenv("SYNAPSE_CREDENTIALS_PATH", "/root/N8N/synapse.credentials")

FILES = [
    "orquestador_produccion.py",
    "orquestador_local_api.py",
    "evaluate_local.py",
    "orquestador_scraper.py",
    "etl_mercado_vivo_incremental.py",
    "synapse_cred.py",
    "zai_client.py",
    "mimo_client.py",
    "limpiador_farmaceutico_regex.py",
    "prompt_agente_v3_solidificado_final.txt",
    ".env",
]


def main() -> int:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    print(f"Conectado a {HOST}")

    sftp = ssh.open_sftp()
    ssh.exec_command(f"mkdir -p {REMOTE}/scratch")
    for name in FILES:
        sftp.put(str(LOCAL / name), f"{REMOTE}/{name}")
        print(f"  ↑ {name}")

    tax = LOCAL / "scratch" / "taxonomias_local.txt"
    if tax.exists():
        sftp.put(str(tax), f"{REMOTE}/scratch/taxonomias_local.txt")

    sftp.close()

    unit = f"""[Unit]
Description=Pipeline Clasificacion Farmaceutica
After=network.target

[Service]
Type=simple
WorkingDirectory={REMOTE}
Environment=SYNAPSE_CREDENTIALS_PATH={CREDS}
Environment=EXPERIMENT_TAXONOMIAS_CACHE={REMOTE}/scratch/taxonomias_local.txt
Environment=ORQUESTADOR_API_PORT=8012
ExecStart=/usr/bin/python3 {REMOTE}/orquestador_local_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    cmds = [
        f"cat > /etc/systemd/system/mdm-orquestador-local.service <<'EOF'\n{unit}EOF",
        "systemctl daemon-reload",
        "systemctl enable mdm-orquestador-local",
        "systemctl restart mdm-orquestador-local",
        "sleep 2",
        "systemctl is-active mdm-orquestador-local",
        "curl -s http://127.0.0.1:8012/api/orquestador/status",
    ]
    for cmd in cmds:
        _, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)

    ssh.close()
    print("Deploy completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
