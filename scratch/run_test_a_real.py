"""
Test A — Dataset con EANs REALES (búsqueda EAN-exacto).

Genera scratch/eval_test_a_real.json con 5 productos de
Procurement.por_aprobacion_equivalencias, scrapeados usando el EAN
entrecomillado (estrategia de orquestador_scraper.procesar_lote l.192).
"""
import os
import sys
import json
import pyodbc
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import orquestador_scraper as scrap


def _dominio(url: str) -> str:
    """Dominio raíz para deduplicación de imágenes por fuente independiente."""
    try:
        host = urlparse(url).netloc.lower()
        for pref in ("www.", "cdn.", "static.", "img.", "images."):
            if host.startswith(pref):
                host = host[len(pref):]
        return host
    except Exception:
        return ""

# 5 EANs reales con atributos ya validados en la tabla.
PRODUCTOS = [
    ("7703991000112", "Cialis 5 mg x 14 comprimidos (Tadalafilo) Lilly"),
    ("7591243802528", "Bisoprolol 2.5mg x 30 tabletas (Astimol) Biotech"),
    ("7591585111968", "OMMUNAL 3.5 mg Pediátrico (Lisado Bacteriano) sobres Leti"),
    ("6921875005362", "CEFTRIAXONA 1G X 1 AMP (I.M/I.V) KMPLUS"),
    ("7703763869756", "Rifaximina 400 mg x 10 tabletas (Pharmetique)"),
]


def generar_dataset():
    resultados = []
    for i, (ean, desc) in enumerate(PRODUCTOS, 1):
        print(f"\n[{i}/5] Scrapeando EAN {ean} - {desc[:50]}...")
        # Búsqueda EAN-exacto (entrecomillado). Si no hay resultados, NO cae a descripción
        # (misma política que procesar_lote para evitar falsos positivos).
        urls_web = scrap.buscar_en_internet(f'"{ean}"', max_fuentes=5)
        if not urls_web:
            print(f"  ⚠ Búsqueda EAN-exacto sin resultados para {ean}. Sin fuentes web.")
        fuentes_extraidas = []
        todas_imagenes = []
        dominios_usados = set()
        for idx, url in enumerate(urls_web, 1):
            fuente_data = scrap.extraer_fuente_web(url, idx, desc_maestra=desc)
            if fuente_data:
                fuentes_extraidas.append(fuente_data)
                for img_url in fuente_data["imagenes_encontradas"]:
                    dom = _dominio(img_url) or _dominio(url)
                    # Independencia: 1 imagen por dominio.
                    if dom and dom not in dominios_usados:
                        dominios_usados.add(dom)
                        todas_imagenes.append(img_url)
                    elif not dom:
                        todas_imagenes.append(img_url)
                    if len(set(todas_imagenes)) >= 5:
                        break
                if len(set(todas_imagenes)) >= 5:
                    break
        resultados.append({
            "ean": ean,
            "descripcion": desc,
            "fuentes_web": fuentes_extraidas,
            "imagenes_b64": list(dict.fromkeys(todas_imagenes))[:5],
        })
        print(f"  → {len(fuentes_extraidas)} fuentes web, {len(set(todas_imagenes))} imágenes")

    out = "scratch/eval_test_a_real.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nDataset guardado: {out}")
    return out


if __name__ == "__main__":
    generar_dataset()
