#!/bin/bash
# Loop de 8 workers batch=5 en paralelo.
# Cada worker procesa 5 productos y vuelve a arrancar.
# Si no hay productos, espera 60s antes de reintentar.
# El cron de ZCode mata todo a las 20:00 VET.

cd "/home/synapse/source/repos/Clasificacion Medicamentos"
export DB_SERVER="100.94.5.108,49751"

MAX_WORKERS=8
LOG_DIR="/tmp/orq_loop"
mkdir -p "$LOG_DIR"

echo "[$(date)] Iniciando loop de $MAX_WORKERS workers batch=5"

launch_worker() {
    local id=$1
    while true; do
        local logfile="${LOG_DIR}/w${id}_$(date +%H%M%S).log"
        echo "[$(date)] W${id} arrancando batch..."
        python3 -u orquestador_produccion.py --trigger-json \
            "{\"TriggerID\":${id},\"ProcessName\":\"MDM_Farmaceutico_Scraper\",\"CheckQuery\":\"SELECT COUNT(*) FROM Procurement.por_aprobacion_equivalencias WHERE estado_ciclo = 'ABIERTO'\",\"ThresholdValue\":1}" \
            --sync > "$logfile" 2>&1
        local rc=$?
        local processed
        processed=$(grep -c "MDM-BATCH.*score=" "$logfile" 2>/dev/null)
        processed=${processed:-0}
        if [ "$processed" -eq 0 ]; then
            echo "[$(date)] W${id} sin productos, esperando 60s..."
            sleep 60
        else
            echo "[$(date)] W${id} procesó ${processed} productos, re-lanzando..."
            sleep 5
        fi
    done
}

# Lanzar 8 workers en background
for i in $(seq 1 $MAX_WORKERS); do
    launch_worker $i &
    echo "[$(date)] W${i} PID:$!"
done

echo "[$(date)] $MAX_WORKERS workers corriendo. Esperando hasta las 20:00 VET..."
wait
