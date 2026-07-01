import sys
import os
import dspy

sys.path.insert(0, "/home/synapse/source/Generador_Prompts")
from generador import generate_prompt, api_key

lm = dspy.LM(
    model="openai/deepseek/deepseek-v4-pro",
    api_key=api_key,
    api_base="https://openrouter.ai/api/v1",
    max_tokens=16000
)
dspy.configure(lm=lm)

prompt_path = "/home/synapse/source/repos/Clasificacion Medicamentos/prompt_agente_v2.txt"
with open(prompt_path, "r", encoding="utf-8") as f:
    prompt_original = f.read()

idea = f"""
Tengo este MEGA-PROMPT de producción para un sistema de agentes que clasifican y extraen datos farmacéuticos.
Este prompt YA FUNCIONA BIEN EN PRODUCCIÓN. NO quiero que lo reduzcas ni lo compactes.

Mi objetivo es CONSOLIDARLO y SOLIDIFICARLO:
1. NO reducir longitud. Si necesita ser MÁS LARGO para ser más efectivo, hazlo más largo.
2. Mejorar la claridad y precisión de CADA instrucción sin eliminar NADA.
3. Reforzar las reglas de negocio existentes para que sean infalibles y sin ambigüedad.
4. Asegurar que los campos nuevos 'requiere_recipe' y 'registro_sanitario' estén perfectamente integrados en TODOS los ejemplos Few-Shot y en las instrucciones.
5. Mejorar las anclas anti-alucinación: si una regla puede ser malinterpretada, reescríbela con más claridad.
6. Reforzar la consistencia del JSON Schema: cada campo debe tener una descripción que no deje lugar a dudas.
7. Si detectas vacíos lógicos, ambigüedades o reglas que podrían confundir al LLM, AGRÉGALAS o REESCRÍBELAS con más detalle.
8. Mantener TODOS los ejemplos Few-Shot existentes y mejorarlos si es posible.
9. Mantener el flujo obligatorio de <analisis_clinico> (Scratchpad) exactamente como está.
10. NO cambiar los placeholders de template ({{taxonomias_existentes}}, {{context_json_str}}, {{nota_vision}}).
11. ¡NUEVA REGLA OBLIGATORIA!: Hemos notado que los modelos pequeños (como Flash) sufren de "Key Dropping" y omiten llaves del JSON si no están seguros. Debes inyectar una regla ABSOLUTA e implacable en el prompt que diga: "ESTRICTAMENTE OBLIGATORIO: Tu JSON de salida DEBE contener TODAS Y CADA UNA de las llaves definidas en el JSON Schema, sin excepción. Si un dato no aplica o no se encuentra, el valor debe ser explícitamente `null` o `0` según el tipo, pero LA LLAVE JAMÁS DEBE SER OMITIDA." Agrega esto en mayúsculas en la zona de reglas de formato JSON.

PRIORIDAD ABSOLUTA: EFECTIVIDAD > todo lo demás. El costo de tokens NO es una preocupación.

Por favor, devuelve el PROMPT CONSOLIDADO Y SOLIDIFICADO listo para producción.

[PROMPT ORIGINAL A CONSOLIDAR]:
{prompt_original}
"""

print("Generando con DeepSeek V4 Pro vía OpenRouter...")
resultado = generate_prompt(idea)

output_path = "/home/synapse/source/repos/Clasificacion Medicamentos/prompt_agente_v3_solidificado_final.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(resultado["prompt_optimizado"])

reasoning_path = "/home/synapse/source/repos/Clasificacion Medicamentos/scratch/reasoning_v3_deepseek_final.txt"
with open(reasoning_path, "w", encoding="utf-8") as f:
    f.write(resultado["reasoning"])

print("Consolidación completa. Guardado en prompt_agente_v3_solidificado_final.txt")
print(f"Tamaño original V2: {os.path.getsize(prompt_path)} bytes")
print(f"Tamaño V3 DeepSeek Final: {os.path.getsize(output_path)} bytes")
