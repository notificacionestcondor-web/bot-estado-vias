"""
Generador de PDF — Convierte el boletín HTML a PDF.

Usa WeasyPrint para conversión de alta calidad.
El PDF se guarda localmente y se sube como artifact del workflow.
"""

import os
import logging

logger = logging.getLogger(__name__)


def generar_pdf(html_path: str) -> str | None:
    """
    Convierte un boletín HTML a PDF.

    Args:
        html_path: Ruta del archivo HTML a convertir.

    Returns:
        Ruta del PDF generado, o None si falla.
    """
    try:
        from weasyprint import HTML

        pdf_path = html_path.replace(".html", ".pdf")
        HTML(filename=html_path).write_pdf(pdf_path)

        logger.info(f"📄 PDF generado: {pdf_path}")
        return pdf_path

    except ImportError:
        logger.warning(
            "⚠️  WeasyPrint no instalado. Instalar con: pip install weasyprint"
        )
        return None
    except Exception as e:
        logger.error(f"❌ Error generando PDF: {e}")
        return None
