#!/usr/bin/env python3
"""
Prueba rápida de GLM-4.7 vía OpenRouter para verificar que funciona correctamente.
"""
import os
import json
import urllib.request

# Cargar credenciales
OPENROUTER_API_KEY = "sk-or-v1-<redactado>"

def probar_glm47():
    """Prueba GLM-4.7 con una petición simple"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "z-ai/glm-4.7",
        "messages": [
            {
                "role": "user",
                "content": "Responde únicamente con la palabra: EXITO"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100,
        "include_reasoning": True  # Importante: incluir razonamiento
    }
    
    print("=== PRUEBA DE GLM-4.7 VIA OPENROUTER ===")
    print(f"Modelo: z-ai/glm-4.7")
    print("Enviando petición...")
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode())
            
            usage = result.get('usage', {})
            p_tokens = usage.get('prompt_tokens', 0)
            c_tokens = usage.get('completion_tokens', 0)
            
            # Calcular costo según precios de OpenRouter
            costo = (p_tokens * 0.40 + c_tokens * 1.75) / 1000000.0
            
            print(f"\n✅ PETICIÓN EXITOSA")
            print(f"Tokens input: {p_tokens}")
            print(f"Tokens output: {c_tokens}")
            print(f"Costo: ${costo:.6f}")
            
            if 'choices' in result and result['choices']:
                choice = result['choices'][0]
                content = choice.get('message', {}).get('content')
                reasoning = choice.get('message', {}).get('reasoning')
                print(f"\nRespuesta del modelo (content): {content}")
                print(f"Razonamiento (reasoning): {reasoning}")
                
                # GLM-4.7 usa 'reasoning' para el pensamiento previo
                if content and "EXITO" in content.upper():
                    print("\n🎉 GLM-4.7 FUNCIONA CORRECTAMENTE!")
                    return True
                elif reasoning and "EXITO" in reasoning.upper():
                    print("\n🎉 GLM-4.7 FUNCIONA CORRECTAMENTE (en reasoning)!")
                    return True
                else:
                    print("\n⚠️ Respuesta inesperada o nula")
                    return False
            else:
                print("\n❌ Error: Sin choices en respuesta")
                print(f"Full result: {json.dumps(result, indent=2)}")
                return False
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    probar_glm47()