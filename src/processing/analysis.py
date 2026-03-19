"""
Generador de análisis logístico automático.

Produce texto de impacto operativo y recomendación
para cada novedad, usando plantillas de config.py.
"""

import logging
from config import ANALISIS_TEMPLATES

logger = logging.getLogger(__name__)


def generar_analisis(novedades: list) -> list:
    """
    Genera análisis logístico para cada novedad.

    Enriquece cada novedad con:
    - 'analisis_impacto': texto de impacto operativo
    - 'analisis_recomendacion': recomendación Transportes Cóndor
    - 'tiempo_normalizacion': tiempo estimado de normalización

    Args:
        novedades: Lista de novedades clasificadas.

    Returns:
        Lista de novedades con análisis logístico.
    """
    for novedad in novedades:
        nivel = novedad.get("nivel_impacto", "bajo")
        corredor = novedad.get("corredor", "corredor no identificado")
        template = ANALISIS_TEMPLATES.get(nivel, ANALISIS_TEMPLATES["bajo"])

        novedad["analisis_impacto"] = template["impacto"].format(
            horas=template["horas_estimadas"],
            corredor=corredor,
        )
        novedad["analisis_recomendacion"] = template["recomendacion"]
        novedad["tiempo_normalizacion"] = f"{template['horas_estimadas']} horas"

    logger.info(f"📊 Análisis logístico generado para {len(novedades)} novedades")
    return novedades
