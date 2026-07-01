import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from evaluate_optimized_local import main

if __name__ == "__main__":
    main(
        input_path="scratch/eval_20_complejos.json",
        comp_path="scratch/resultados_20.json",
        excel_path="scratch/comparativa_20.xlsx"
    )
