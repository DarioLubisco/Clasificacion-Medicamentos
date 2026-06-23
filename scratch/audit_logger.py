import os
from dotenv import load_dotenv
load_dotenv()
import pyodbc
import json
from datetime import datetime

CONN_STR = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER=100.94.5.108\\efficacis3;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD={os.getenv("DB_PASSWORD")};TrustServerCertificate=yes;Encrypt=yes;'

def log_ai_cycle(motor, enfoque, orquestador_version, scraper_version, extra_info=None):
    """
    Graba un registro de auditoría en dbo.synapse_log_actividad cada vez que se ejecuta un ciclo de IA.
    """
    try:
        conn = pyodbc.connect(CONN_STR, timeout=10)
        cursor = conn.cursor()
        
        detalle_payload = {
            "motor": motor,
            "enfoque": enfoque,
            "orquestador_version": orquestador_version,
            "scraper_version": scraper_version,
            "metadata": extra_info or {}
        }
        
        json_detalle = json.dumps(detalle_payload, ensure_ascii=False)
        
        query = """
            INSERT INTO dbo.synapse_log_actividad 
            (usuario_id, username, accion, modulo, detalle, ip, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, GETDATE())
        """
        
        # Insertando con usuario_id=1 (admin)
        cursor.execute(query, (
            1, # usuario_id bot
            'Synapse_Orchestrator', # username
            'ciclo_extraccion_ia', # accion
            'MDM_Scraper_Pipeline', # modulo
            json_detalle, # detalle
            '127.0.0.1' # ip
        ))
        
        conn.commit()
        conn.close()
        print("[Audit Logger] Ciclo de IA registrado correctamente en synapse_log_actividad.")
        return True
    except Exception as e:
        print(f"[Audit Logger] Error al registrar en BD: {e}")
        return False

if __name__ == "__main__":
    # Test execution
    log_ai_cycle(
        motor="Gemini-1.5-Pro",
        enfoque="M-Zero-Shot / OpenRouter",
        orquestador_version="v4.0",
        scraper_version="v11.0",
        extra_info={"test": "ok", "items_processed": 0}
    )
