"""
Generador de boletín HTML usando Jinja2.

Renderiza el template del boletín con los datos de novedades
y lo guarda en el directorio de reportes para GitHub Pages.
"""

import os
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from config import (
    EMPRESA, MENSAJE_INSTITUCIONAL, REPORTES_DIR,
    get_report_filename, get_report_period, GITHUB_PAGES_URL,
)

logger = logging.getLogger(__name__)


def generar_html(novedades: list, errores: list = None) -> str:
    """
    Genera el boletín en HTML.

    Args:
        novedades: Lista de novedades procesadas (filtradas, clasificadas, con análisis).
        errores: Lista de errores de scraping (opcional).

    Returns:
        Ruta del archivo HTML generado.
    """
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("boletin.html")

    now = datetime.now()
    filename = get_report_filename()

    # Agrupar novedades por corredor
    por_corredor = {}
    for novedad in novedades:
        corredor = novedad.get("corredor", "Sin corredor")
        if corredor not in por_corredor:
            por_corredor[corredor] = []
        por_corredor[corredor].append(novedad)

    # Conteo de impactos
    resumen = {
        "total": len(novedades),
        "alto": sum(1 for n in novedades if n.get("nivel_impacto") == "alto"),
        "medio": sum(1 for n in novedades if n.get("nivel_impacto") == "medio"),
        "bajo": sum(1 for n in novedades if n.get("nivel_impacto") == "bajo"),
    }

    html_content = template.render(
        empresa=EMPRESA,
        mensaje_institucional=MENSAJE_INSTITUCIONAL,
        periodo=get_report_period(),
        fecha=now.strftime("%d de %B de %Y"),
        hora=now.strftime("%I:%M %p"),
        novedades=novedades,
        por_corredor=por_corredor,
        resumen=resumen,
        errores=errores or [],
        github_pages_url=GITHUB_PAGES_URL,
    )

    # Guardar en docs/reportes/ para GitHub Pages
    os.makedirs(REPORTES_DIR, exist_ok=True)
    output_path = os.path.join(REPORTES_DIR, f"{filename}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"📄 Boletín HTML generado: {output_path}")
    return output_path
