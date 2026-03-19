"""
Generador de JSON — Datos para el dashboard de GitHub Pages.

Genera dos archivos:
- ultimo_reporte.json: datos del reporte más reciente
- indice_reportes.json: índice de todos los reportes generados
"""

import os
import json
import logging
from datetime import datetime

from config import DATA_DIR, get_report_filename, get_report_period

logger = logging.getLogger(__name__)


def generar_json(novedades: list, html_path: str, errores: list = None) -> str:
    """
    Genera archivos JSON para alimentar el dashboard web.

    Args:
        novedades: Lista de novedades procesadas.
        html_path: Ruta del boletín HTML generado.
        errores: Lista de errores de scraping.

    Returns:
        Ruta del archivo JSON del último reporte.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now()

    # --- JSON del último reporte ---
    reporte_data = {
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M"),
        "periodo": get_report_period(),
        "total_novedades": len(novedades),
        "resumen": {
            "alto": sum(1 for n in novedades if n.get("nivel_impacto") == "alto"),
            "medio": sum(1 for n in novedades if n.get("nivel_impacto") == "medio"),
            "bajo": sum(1 for n in novedades if n.get("nivel_impacto") == "bajo"),
        },
        "novedades": [
            {
                "corredor": n.get("corredor", ""),
                "ubicacion": n.get("ubicacion", ""),
                "tipo_novedad": n.get("tipo_novedad", ""),
                "estado": n.get("estado", ""),
                "nivel_impacto": n.get("nivel_impacto", ""),
                "fuente": n.get("fuente", ""),
                "analisis_impacto": n.get("analisis_impacto", ""),
                "analisis_recomendacion": n.get("analisis_recomendacion", ""),
            }
            for n in novedades
        ],
        "errores_scraping": errores or [],
        "archivo_html": os.path.basename(html_path),
    }

    ultimo_path = os.path.join(DATA_DIR, "ultimo_reporte.json")
    with open(ultimo_path, "w", encoding="utf-8") as f:
        json.dump(reporte_data, f, ensure_ascii=False, indent=2)

    # --- Actualizar índice de reportes ---
    indice_path = os.path.join(DATA_DIR, "indice_reportes.json")
    try:
        with open(indice_path, "r", encoding="utf-8") as f:
            indice = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        indice = {"reportes": []}

    indice["reportes"].insert(0, {
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M"),
        "periodo": get_report_period(),
        "archivo": os.path.basename(html_path),
        "total_novedades": len(novedades),
        "alto": reporte_data["resumen"]["alto"],
        "medio": reporte_data["resumen"]["medio"],
        "bajo": reporte_data["resumen"]["bajo"],
    })

    # Mantener solo los últimos 90 reportes (30 días × 3 reportes/día)
    indice["reportes"] = indice["reportes"][:90]

    with open(indice_path, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    logger.info(f"📊 JSON generado: {ultimo_path}")
    return ultimo_path
