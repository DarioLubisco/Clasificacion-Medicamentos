"""ETL incremental Mercado Vivo → por_aprobacion_equivalencias (trigger n8n #2)."""
from __future__ import annotations

import concurrent.futures
import os
import time

import pyodbc
import requests

from synapse_cred import load_synapse_credentials

load_synapse_credentials()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_db_connection() -> pyodbc.Connection:
    server = os.getenv("DB_SERVER", "100.94.5.108,49751")
    database = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "")
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={user};PWD={password};"
        "TrustServerCertificate=yes;Encrypt=yes;"
    )
    return pyodbc.connect(conn_str, timeout=15)


def process_ai_summary(barcode: str, raw_descriptions: str) -> tuple[str, str, str]:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    prompt = (
        "Eres un asistente experto en datos farmacéuticos. Recibes múltiples descripciones "
        "variantes de un mismo producto separadas por '|'.\n"
        "Devuelve una única descripción limpia, formal y concisa (máximo 1 línea).\n"
        "Sin comillas, markdown ni explicaciones.\n"
        f"Descripciones: {raw_descriptions}"
    )
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"].strip()
        if summary.startswith("```"):
            summary = summary.split("\n", 1)[-1]
        summary = summary.replace("```", "").replace('"', "").strip()
        return barcode, summary[:950], raw_descriptions
    except Exception as exc:
        print(f"Error procesando {barcode}: {exc}")
        return barcode, raw_descriptions[:950], raw_descriptions


def main() -> None:
    start = time.time()
    print("ETL Mercado Vivo incremental...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT codigo_barras, STRING_AGG(descripcion_producto, ' | ')
        FROM Analitica.Mercado_Vivo_PDR
        WHERE codigo_barras IS NOT NULL
          AND codigo_barras NOT LIKE '%[^0-9]%'
          AND LEN(codigo_barras) >= 6
          AND codigo_barras NOT IN (
              SELECT codbarras FROM Procurement.por_aprobacion_equivalencias
          )
        GROUP BY codigo_barras
        """
    )
    rows = cursor.fetchall()
    if not rows:
        print("Sin productos nuevos.")
        conn.close()
        return

    print(f"Nuevos códigos: {len(rows)}")
    results: list[tuple[str, str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [
            pool.submit(process_ai_summary, row[0], row[1]) for row in rows
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    insert_sql = """
        INSERT INTO Procurement.por_aprobacion_equivalencias
            (codbarras, descrip1art, descripcion_mercado_concat)
        VALUES (?, ?, ?)
    """
    cursor.fast_executemany = True
    for i in range(0, len(results), 500):
        batch = results[i : i + 500]
        cursor.executemany(insert_sql, batch)
        conn.commit()
        print(f"Insertados {i + len(batch)}/{len(results)}")

    conn.close()
    print(f"ETL completado en {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
