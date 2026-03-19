"""
Clasificación automática de impacto logístico.

Asigna nivel de impacto (alto, medio, bajo) a cada novedad
según el tipo de evento, usando las reglas de config.py.
"""

import logging
from config import IMPACTO_ALTO, IMPACTO_MEDIO, IMPACTO_BAJO

logger = logging.getLogger(__name__)


def clasificar_impacto(novedades: list) -> list:
    """
    Clasifica cada novedad por nivel de impacto logístico.

    Enriquece cada novedad con los campos:
    - 'nivel_impacto': "alto", "medio", "bajo"
    - 'color_impacto': color hex para el boletín

    Args:
        novedades: Lista de novedades ya filtradas por corredor.

    Returns:
        Lista de novedades con clasificación de impacto.
    """
    for novedad in novedades:
        texto = (
            f"{novedad.get('tipo_novedad', '')} "
            f"{novedad.get('estado', '')}"
        ).lower()

        nivel = _determinar_nivel(texto)
        novedad["nivel_impacto"] = nivel
        novedad["color_impacto"] = COLORES[nivel]

    # Ordenar: alto primero, luego medio, luego bajo
    orden = {"alto": 0, "medio": 1, "bajo": 2}
    novedades.sort(key=lambda n: orden.get(n.get("nivel_impacto", "bajo"), 3))

    # Log resumen
    conteo = {"alto": 0, "medio": 0, "bajo": 0}
    for n in novedades:
        conteo[n["nivel_impacto"]] += 1
    logger.info(
        f"🏷️  Clasificación: {conteo['alto']} alto, "
        f"{conteo['medio']} medio, {conteo['bajo']} bajo"
    )

    return novedades


COLORES = {
    "alto": "#DC2626",     # Rojo
    "medio": "#F59E0B",    # Naranja/Amarillo
    "bajo": "#10B981",     # Verde
}

LABELS = {
    "alto": "🔴 ALTO",
    "medio": "🟡 MEDIO",
    "bajo": "🟢 BAJO",
}


def _determinar_nivel(texto: str) -> str:
    """Determina el nivel de impacto según keywords en el texto."""
    for keyword in IMPACTO_ALTO:
        if keyword in texto:
            return "alto"

    for keyword in IMPACTO_MEDIO:
        if keyword in texto:
            return "medio"

    for keyword in IMPACTO_BAJO:
        if keyword in texto:
            return "bajo"

    return "bajo"
