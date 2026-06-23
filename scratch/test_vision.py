import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mega_orquestador_v3 import llamar_vision_multimodal

urls = [
    "https://www.farmadon.com.ve/wp-content/uploads/2024/12/Buscaminal-10Mg-X-20-Tabletas-Arte-Medico.png",
    "https://http2.mlstatic.com/D_NQ_NP_993652-MLM83971799130_052025-OO.png"
]

print("Probando llamar_vision_multimodal...")
res = llamar_vision_multimodal("0731946648628", "BUSCAMINAL 20 TABLETAS RECUBIERTAS", urls)
print("Resultado Vision:")
print(res)
