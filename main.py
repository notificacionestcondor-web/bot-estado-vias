"""
main.py — Orquestador principal del BOT Estado de Vías.

Ejecuta el flujo completo:
1. Consulta fuentes oficiales (scrapers)
2. Filtra por corredores logísticos
3. Clasifica impacto
4. Genera análisis logístico
5. Construye boletín HTML + PDF
6. Genera JSON para dashboard
7. Envía correo electrónico

Uso:
    python main.py
"""

import os
import sys
import logging
from datetime import datetime

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    EMPRESA, GITHUB_PAGES_URL, REPORTES_DIR,
    get_report_filename, get_report_period, HISTORICO_CSV,
)
from src.scrapers import ejecutar_scrapers
from src.processing.filter import filtrar_por_corredor
from src.processing.classify import clasificar_impacto
from src.processing.analysis import generar_analisis
from src.output.html_builder import generar_html
from src.output.pdf_builder import generar_pdf
from src.output.json_builder import generar_json
from src.distribution.email_sender import enviar_reporte


def setup_logging():
    """Configura logging para consola con formato legible."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def guardar_historico(novedades: list):
    """Guarda las novedades en el CSV histórico."""
    import csv

    os.makedirs(os.path.dirname(HISTORICO_CSV), exist_ok=True)
    file_exists = os.path.exists(HISTORICO_CSV)

    fieldnames = [
        "timestamp", "corredor", "ubicacion", "tipo_novedad",
        "estado", "nivel_impacto", "fuente", "detalle",
    ]

    with open(HISTORICO_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        now = datetime.now().isoformat()
        for n in novedades:
            writer.writerow({
                "timestamp": now,
                "corredor": n.get("corredor", ""),
                "ubicacion": n.get("ubicacion", ""),
                "tipo_novedad": n.get("tipo_novedad", ""),
                "estado": n.get("estado", ""),
                "nivel_impacto": n.get("nivel_impacto", ""),
                "fuente": n.get("fuente", ""),
                "detalle": n.get("detalle", ""),
            })


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    now = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🛣️  BOT ESTADO DE VÍAS — {EMPRESA}")
    logger.info(f"📅 {now.strftime('%Y-%m-%d %I:%M %p')}")
    logger.info(f"📋 {get_report_period()}")
    logger.info("=" * 60)

    # --- PASO 1: Scraping ---
    logger.info("")
    logger.info("PASO 1/7 — Consultando fuentes oficiales...")
    novedades, errores = ejecutar_scrapers()
    logger.info(f"   Total novedades extraídas: {len(novedades)}")
    if errores:
        logger.warning(f"   ⚠️  {len(errores)} fuentes con error")

    if not novedades:
        logger.warning("⚠️  No se encontraron novedades. Generando boletín vacío.")

    # --- PASO 2: Filtro por corredor ---
    logger.info("")
    logger.info("PASO 2/7 — Filtrando por corredores logísticos...")
    novedades = filtrar_por_corredor(novedades)

    # --- PASO 3: Clasificación de impacto ---
    logger.info("")
    logger.info("PASO 3/7 — Clasificando impacto logístico...")
    novedades = clasificar_impacto(novedades)

    # --- PASO 4: Análisis logístico ---
    logger.info("")
    logger.info("PASO 4/7 — Generando análisis logístico...")
    novedades = generar_analisis(novedades)

    # --- PASO 5: Generar boletín HTML ---
    logger.info("")
    logger.info("PASO 5/7 — Generando boletín HTML...")
    html_path = generar_html(novedades, errores)

    # --- PASO 6: Generar PDF ---
    logger.info("")
    logger.info("PASO 6/7 — Generando PDF...")
    pdf_path = generar_pdf(html_path)

    # --- Generar JSON para dashboard ---
    json_path = generar_json(novedades, html_path, errores)

    # --- Guardar histórico ---
    guardar_historico(novedades)

    # --- PASO 7: Enviar correo ---
    logger.info("")
    logger.info("PASO 7/7 — Enviando reporte por correo...")
    filename = get_report_filename()
    boletin_url = f"{GITHUB_PAGES_URL}/reportes/{filename}.html"
    enviar_reporte(novedades, html_path, pdf_path, boletin_url)

    # --- Resumen final ---
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ EJECUCIÓN COMPLETADA")
    logger.info(f"   📄 HTML: {html_path}")
    if pdf_path:
        logger.info(f"   📄 PDF:  {pdf_path}")
    logger.info(f"   📊 JSON: {json_path}")
    logger.info(f"   🌐 URL:  {boletin_url}")
    logger.info(f"   📝 Novedades: {len(novedades)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
