"""
Filtro por corredor logístico.

Asocia cada novedad con uno o más corredores monitoreados
usando matching por keywords definidos en config.py.
"""

import logging
from config import CORREDORES

logger = logging.getLogger(__name__)


def filtrar_por_corredor(novedades: list) -> list:
    """
    Filtra y enriquece las novedades asignando el corredor logístico.

    Cada novedad se compara contra los keywords de los corredores.
    Si no hace match con ningún corredor, se descarta.

    Args:
        novedades: Lista de dicts con formato estándar de los scrapers.

    Returns:
        Lista de novedades que coinciden con al menos un corredor,
        enriquecidas con el campo 'corredor'.
    """
    novedades_filtradas = []

    for novedad in novedades:
        texto_busqueda = (
            f"{novedad.get('corredor_texto', '')} "
            f"{novedad.get('ubicacion', '')} "
            f"{novedad.get('detalle', '')}"
        ).lower()

        corredor_match = _encontrar_corredor(texto_busqueda)

        if corredor_match:
            novedad["corredor"] = corredor_match
            novedades_filtradas.append(novedad)
        else:
            logger.debug(
                f"   ⏭️  Novedad sin corredor asociado: {novedad.get('corredor_texto', '')[:60]}"
            )

    logger.info(
        f"🛣️  Filtro: {len(novedades_filtradas)}/{len(novedades)} "
        f"novedades coinciden con corredores monitoreados"
    )
    return novedades_filtradas


def _encontrar_corredor(texto: str) -> str | None:
    """
    Busca el corredor que mejor coincide con el texto dado.

    Retorna el nombre del corredor con más keywords encontrados.
    """
    mejor_match = None
    max_coincidencias = 0

    for corredor in CORREDORES:
        coincidencias = sum(
            1 for kw in corredor["keywords"]
            if kw.lower() in texto
        )

        if coincidencias > max_coincidencias:
            max_coincidencias = coincidencias
            mejor_match = corredor["nombre"]

    return mejor_match
