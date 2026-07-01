#!/bin/bash

# Backup
cp scratch/evaluate_optimized_local.py scratch/evaluate_optimized_local.py.bak

# PROMPT V2 (Original)
sed -i 's/prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_agente_v3_solidificado.txt")/prompt_template_path = os.path.join(os.path.dirname(__file__), "prompt_agente_v2.txt")/' scratch/evaluate_optimized_local.py
echo "== CORRIENDO V2 ORIGINAL =="
python3 scratch/evaluate_optimized_local.py > scratch/log_v2.txt
cp scratch/resultados_triple.json scratch/resultados_v2.json
cp scratch/comparativa_triple.xlsx scratch/comparativa_v2.xlsx

# PROMPT V3 (DeepSeek Solidificado)
sed -i 's/prompt_template_path = os.path.join(os.path.dirname(__file__), "prompt_agente_v2.txt")/prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_agente_v3_solidificado.txt")/' scratch/evaluate_optimized_local.py
echo "== CORRIENDO V3 SOLIDIFICADO =="
python3 scratch/evaluate_optimized_local.py > scratch/log_v3_sol.txt
cp scratch/resultados_triple.json scratch/resultados_v3_sol.json
cp scratch/comparativa_triple.xlsx scratch/comparativa_v3_sol.xlsx

# PROMPT V3 (Claude Opus 4.8)
sed -i 's/prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_agente_v3_solidificado.txt")/prompt_template_path = os.path.join(os.path.dirname(__file__), "prompt_agente_v3_opus48.txt")/' scratch/evaluate_optimized_local.py
echo "== CORRIENDO V3 OPUS =="
python3 scratch/evaluate_optimized_local.py > scratch/log_v3_opus.txt
cp scratch/resultados_triple.json scratch/resultados_v3_opus.json
cp scratch/comparativa_triple.xlsx scratch/comparativa_v3_opus.xlsx

# Restore
mv scratch/evaluate_optimized_local.py.bak scratch/evaluate_optimized_local.py
echo "== PRUEBA TRIPLE COMPLETADA =="
