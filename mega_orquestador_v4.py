import os
import subprocess
import time

def run_script(script_name):
    print(f"\n{'='*50}")
    print(f"🚀 INICIANDO: {script_name}")
    print(f"{'='*50}")
    
    start_time = time.time()
    result = subprocess.run(["python3", script_name], capture_output=True, text=True)
    
    # Print the output in real-time or after completion
    print(result.stdout)
    if result.stderr:
        print(f"⚠️ ERRORES EN {script_name}:")
        print(result.stderr)
        
    elapsed = time.time() - start_time
    print(f"✅ FINALIZADO: {script_name} en {elapsed:.2f} segundos.")
    print(f"{'='*50}\n")
    return result.returncode

def main():
    print("🌟 MEGA ORQUESTADOR V4 - PIPELINE DESACOPLADO 🌟")
    print("Iniciando secuencia de ejecución...")
    
    # FASE 1: Algoritmo de Auto-Aprendizaje Local
    print("\n>>> FASE 1: Extracción Local Dinámica")
    # Este script procesa en lotes de 4000. Idealmente, lo corremos una vez. Si hay más, se puede iterar.
    # Por ahora asume que process_4000_dynamic.py procesa lo que haya.
    code_f1 = run_script("scratch/process_4000_dynamic.py")
    
    # FASE 2: Web Scraping de los Remanentes
    if code_f1 == 0:
        print("\n>>> FASE 2: Extracción Web Scraping Asíncrona")
        code_f2 = run_script("scratch/fase2_scraper_db.py")
        
        # FASE 3: Motor de Inteligencia Artificial
        if code_f2 == 0:
            print("\n>>> FASE 3: Análisis IA (OpenRouter / Gemini)")
            code_f3 = run_script("scratch/motor_ia_v1.py")
            
            if code_f3 == 0:
                print("\n🎉 MEGA ORQUESTADOR V4 COMPLETADO EXITOSAMENTE 🎉")
            else:
                print("❌ Orquestador detenido por error en Fase 3.")
        else:
            print("❌ Orquestador detenido por error en Fase 2.")
    else:
        print("❌ Orquestador detenido por error en Fase 1.")

if __name__ == "__main__":
    # Ensure working directory is the base directory
    base_dir = "/home/synapse/source/repos/Clasificacion Medicamentos"
    if os.getcwd() != base_dir:
        os.chdir(base_dir)
    main()
