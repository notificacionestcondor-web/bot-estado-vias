"""
Scraper Movilidad Bogotá — Estado vial urbano.
https://www.movilidadbogota.gov.co/web/estado_de_vias

Este scraper intenta primero con requests + BeautifulSoup (más rápido).
Si el contenido es dinámico, cae a Selenium como fallback.

Modo descubrimiento:
    python -m src.scrapers.movilidad_bogota --descubrir
"""

import os
import sys
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import FUENTES
from src.scrapers.base import (
    crear_driver, safe_scrape, esperar_elemento,
    scroll_completo, timestamp_ahora, limpiar_texto,
)

logger = logging.getLogger(__name__)
FUENTE = FUENTES["movilidad_bogota"]

# =============================================================================
# SELECTORES — AJUSTAR SEGÚN ESTRUCTURA REAL
# =============================================================================

SELECTORES = {
    # Para requests + BeautifulSoup
    "contenedor_bs": "table, .view-content, .field-items, .node-content",
    "filas_bs": "tr",
    "celdas_bs": "td",

    # Para Selenium (fallback)
    "contenedor_sel": "table, .view-content, #block-system-main",
    "filas_sel": "tbody tr, .views-row",
    "celdas_sel": "td, .views-field",

    # Índices de columnas
    "col_sector": 0,
    "col_novedad": 1,
    "col_estado": 2,
    "col_detalle": 3,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}

FILAS_IGNORAR = ["total", "sector", "localidad", "---"]


@safe_scrape(max_retries=2, delay=5, nombre_fuente="Movilidad Bogotá")
def scrape():
    """
    Consulta Movilidad Bogotá.
    Intenta requests primero, si falla usa Selenium.
    """
    # Intento 1: requests + BS4 (rápido, sin navegador)
    try:
        novedades = _scrape_requests()
        if novedades:
            return novedades
        logger.info("   ⚠️  requests no encontró datos, probando Selenium...")
    except Exception as e:
        logger.info(f"   ⚠️  requests falló ({e}), probando Selenium...")

    # Intento 2: Selenium (para contenido dinámico)
    return _scrape_selenium()


def _scrape_requests():
    """Extracción con requests + BeautifulSoup."""
    logger.info(f"   🌐 Consultando {FUENTE['url']} (requests)")

    response = requests.get(FUENTE["url"], headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    contenedor = soup.select_one(SELECTORES["contenedor_bs"])

    if not contenedor:
        return []

    filas = contenedor.select(SELECTORES["filas_bs"])
    logger.info(f"   📊 {len(filas)} filas encontradas (BS4)")

    novedades = []
    for fila in filas:
        celdas = fila.select(SELECTORES["celdas_bs"])
        if len(celdas) < 2:
            continue

        textos = [c.get_text(strip=True) for c in celdas]
        fila_lower = " ".join(textos).lower()

        if any(x in fila_lower for x in FILAS_IGNORAR):
            continue

        sector = _safe(textos, SELECTORES["col_sector"])
        novedad = _safe(textos, SELECTORES["col_novedad"])
        estado = _safe(textos, SELECTORES["col_estado"])
        detalle = _safe(textos, SELECTORES["col_detalle"])

        if not sector:
            continue
        if estado.lower() in ["normal", "sin novedad", ""]:
            continue

        novedades.append({
            "corredor_texto": f"Bogotá — {sector}",
            "ubicacion": f"Bogotá, {sector}",
            "tipo_novedad": _inferir_tipo(novedad, estado, detalle),
            "estado": estado or novedad,
            "fuente": FUENTE["nombre"],
            "link": FUENTE["url"],
            "fecha_reporte": timestamp_ahora(),
            "detalle": limpiar_texto(detalle),
        })

    logger.info(f"   📋 {len(novedades)} novedades extraídas (BS4)")
    return novedades


def _scrape_selenium():
    """Extracción con Selenium (fallback para contenido dinámico)."""
    from selenium.webdriver.common.by import By

    driver = crear_driver(headless=True, timeout=25)

    try:
        logger.info(f"   🌐 Accediendo con Selenium: {FUENTE['url']}")
        driver.get(FUENTE["url"])

        try:
            esperar_elemento(driver, SELECTORES["contenedor_sel"], timeout=15)
        except Exception:
            scroll_completo(driver, pausa=1.5)
            esperar_elemento(driver, SELECTORES["contenedor_sel"], timeout=10)

        contenedor = driver.find_element(By.CSS_SELECTOR, SELECTORES["contenedor_sel"])
        filas = contenedor.find_elements(By.CSS_SELECTOR, SELECTORES["filas_sel"])
        logger.info(f"   📊 {len(filas)} filas encontradas (Selenium)")

        novedades = []
        for fila in filas:
            celdas = fila.find_elements(By.CSS_SELECTOR, SELECTORES["celdas_sel"])
            if len(celdas) < 2:
                continue

            textos = [c.text.strip() for c in celdas]
            fila_lower = " ".join(textos).lower()

            if any(x in fila_lower for x in FILAS_IGNORAR):
                continue

            sector = _safe(textos, SELECTORES["col_sector"])
            novedad = _safe(textos, SELECTORES["col_novedad"])
            estado = _safe(textos, SELECTORES["col_estado"])
            detalle = _safe(textos, SELECTORES["col_detalle"])

            if not sector:
                continue
            if estado.lower() in ["normal", "sin novedad", ""]:
                continue

            novedades.append({
                "corredor_texto": f"Bogotá — {sector}",
                "ubicacion": f"Bogotá, {sector}",
                "tipo_novedad": _inferir_tipo(novedad, estado, detalle),
                "estado": estado or novedad,
                "fuente": FUENTE["nombre"],
                "link": FUENTE["url"],
                "fecha_reporte": timestamp_ahora(),
                "detalle": limpiar_texto(detalle),
            })

        logger.info(f"   📋 {len(novedades)} novedades (Selenium)")
        return novedades

    finally:
        driver.quit()


# =============================================================================
# UTILIDADES
# =============================================================================

CATEGORIAS = {
    "accidente": ["accidente", "siniestro", "volcamiento", "choque"],
    "cierre total": ["cierre", "cerrada", "cerrado"],
    "congestión": ["congestión", "congestionamiento", "represamiento", "tráfico"],
    "obras": ["obras", "mantenimiento", "intervención"],
    "bloqueo": ["bloqueo", "protesta", "manifestación", "marcha"],
    "inundación": ["inundación", "inundada", "encharcamiento"],
}


def _inferir_tipo(novedad, estado, detalle):
    texto = f"{novedad} {estado} {detalle}".lower()
    for tipo, kws in CATEGORIAS.items():
        if any(kw in texto for kw in kws):
            return tipo
    return novedad.lower() if novedad else "novedad"


def _safe(lista, idx, default=""):
    try:
        return lista[idx].strip()
    except (IndexError, AttributeError):
        return default


# =============================================================================
# MODO DESCUBRIMIENTO
# =============================================================================

def descubrir():
    """Guarda HTML con requests y con Selenium para comparar."""
    import time

    debug_dir = "data/debug"
    os.makedirs(debug_dir, exist_ok=True)

    logger.info("🔍 MODO DESCUBRIMIENTO — Movilidad Bogotá")

    # 1. Probar con requests
    try:
        response = requests.get(FUENTE["url"], headers=HEADERS, timeout=15)
        with open(os.path.join(debug_dir, "movilidad_requests.html"), "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info("   📄 HTML (requests) guardado")

        soup = BeautifulSoup(response.text, "html.parser")
        tablas = soup.select("table")
        logger.info(f"   📊 Tablas en requests: {len(tablas)}")
    except Exception as e:
        logger.warning(f"   requests falló: {e}")

    # 2. Probar con Selenium
    driver = crear_driver(headless=True, timeout=25)
    try:
        driver.get(FUENTE["url"])
        time.sleep(5)
        scroll_completo(driver, pausa=2)

        driver.save_screenshot(os.path.join(debug_dir, "movilidad_screenshot.png"))

        with open(os.path.join(debug_dir, "movilidad_selenium.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("   📄 HTML (Selenium) guardado")
        logger.info("   👉 Compara ambos HTML en data/debug/")
    finally:
        driver.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    if "--descubrir" in sys.argv:
        descubrir()
    else:
        resultado = scrape()
        print(f"\nNovedades: {len(resultado)}")
        for n in resultado:
            print(f"  [{n['tipo_novedad'].upper()}] {n['corredor_texto']}")
