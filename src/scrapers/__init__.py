"""
Módulo de scrapers — Extracción de datos de fuentes oficiales.

Cada scraper implementa la función `scrape()` que retorna una lista
de novedades con el formato estándar:

{
    "corredor_texto": str,      # Texto original del corredor/ubicación
    "ubicacion": str,            # Municipio, km, sector
    "tipo_novedad": str,         # cierre total, derrumbe, obras, etc.
    "estado": str,               # cerrado, paso restringido, etc.
    "fuente": str,               # Nombre de la fuente
    "link": str,                 # URL del reporte
    "fecha_reporte": str,        # Fecha del reporte original
    "detalle": str,              # Descripción adicional
}
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def ejecutar_scrapers():
    """
    Ejecuta todos los scrapers activos y retorna las novedades consolidadas.
    Si un scraper falla, registra el error y continúa con los demás.
    """
    from config import FUENTES
    from src.scrapers import invias, ani, movilidad_bogota, ideam, policia_transito

    SCRAPER_MAP = {
        "invias": invias.scrape,
        "ani": ani.scrape,
        "movilidad_bogota": movilidad_bogota.scrape,
        "ideam": ideam.scrape,
        "policia_transito": policia_transito.scrape,
    }

    todas_novedades = []
    errores = []

    for clave, config_fuente in FUENTES.items():
        if not config_fuente.get("activa", False):
            logger.info(f"⏭️  {config_fuente['nombre']} — desactivada, se omite")
            continue

        scraper_fn = SCRAPER_MAP.get(clave)
        if not scraper_fn:
            logger.warning(f"⚠️  No hay scraper implementado para: {clave}")
            continue

        try:
            logger.info(f"🔍 Consultando {config_fuente['nombre']}...")
            novedades = scraper_fn()
            logger.info(f"   ✅ {len(novedades)} novedades encontradas")
            todas_novedades.extend(novedades)
        except Exception as e:
            error_msg = f"❌ Error en {config_fuente['nombre']}: {str(e)}"
            logger.error(error_msg)
            errores.append({
                "fuente": config_fuente["nombre"],
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })

    return todas_novedades, errores
