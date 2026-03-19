"""
Scraper ANI — Estado de vías concesionadas.
https://www.ani.gov.co

La ANI publica información sobre el estado de corredores concesionados,
obras en curso y restricciones. El sitio es dinámico → Selenium.

Modo descubrimiento:
    python -m src.scrapers.ani --descubrir
"""

import os
import sys
import logging
from datetime import datetime

from config import FUENTES
from src.scrapers.base import (
    crear_driver, safe_scrape, esperar_elemento,
    scroll_completo, timestamp_ahora, limpiar_texto,
)

logger = logging.getLogger(__name__)
FUENTE = FUENTES["ani"]

# =============================================================================
# SELECTORES — AJUSTAR SEGÚN ESTRUCTURA REAL
# =============================================================================

SELECTORES = {
    "contenedor": "table, .view-content, .field-items, #block-system-main table",
    "filas": "tbody tr",
    "celdas": "td",
    "col_corredor": 0,
    "col_concesion": 1,
    "col_novedad": 2,
    "col_estado": 3,
    "col_observaciones": 4,
}

FILAS_IGNORAR = ["total", "---", "concesión", "concesion"]


@safe_scrape(max_retries=2, delay=5, nombre_fuente="ANI")
def scrape():
    """Consulta ANI y extrae novedades de vías concesionadas."""
    driver = crear_driver(headless=True, timeout=30)

    try:
        logger.info(f"   🌐 Accediendo a {FUENTE['url']}")
        driver.get(FUENTE["url"])

        try:
            esperar_elemento(driver, SELECTORES["contenedor"], timeout=20)
        except Exception:
            scroll_completo(driver, pausa=1.5)
            esperar_elemento(driver, SELECTORES["contenedor"], timeout=10)

        return _extraer_novedades(driver)

    finally:
        driver.quit()


def _extraer_novedades(driver):
    from selenium.webdriver.common.by import By

    novedades = []

    try:
        contenedor = driver.find_element(By.CSS_SELECTOR, SELECTORES["contenedor"])
        filas = contenedor.find_elements(By.CSS_SELECTOR, SELECTORES["filas"])
        logger.info(f"   📊 {len(filas)} filas encontradas")

        for i, fila in enumerate(filas):
            try:
                celdas = fila.find_elements(By.CSS_SELECTOR, SELECTORES["celdas"])
                if len(celdas) < 3:
                    continue

                textos = [c.text.strip() for c in celdas]
                fila_lower = " ".join(textos).lower()

                if any(x in fila_lower for x in FILAS_IGNORAR):
                    continue

                corredor = _safe(textos, SELECTORES["col_corredor"])
                concesion = _safe(textos, SELECTORES["col_concesion"])
                novedad = _safe(textos, SELECTORES["col_novedad"])
                estado = _safe(textos, SELECTORES["col_estado"])
                obs = _safe(textos, SELECTORES["col_observaciones"])

                if not corredor:
                    continue

                if estado.lower() in ["normal", "operación normal", ""]:
                    continue

                ubicacion = f"{corredor}, {concesion}" if concesion else corredor

                novedades.append({
                    "corredor_texto": f"Concesión {concesion} - {corredor}".strip(),
                    "ubicacion": limpiar_texto(ubicacion),
                    "tipo_novedad": _inferir_tipo(novedad, estado, obs),
                    "estado": estado or novedad,
                    "fuente": FUENTE["nombre"],
                    "link": FUENTE["url"],
                    "fecha_reporte": timestamp_ahora(),
                    "detalle": limpiar_texto(obs),
                })

            except Exception as e:
                logger.debug(f"   Error fila {i}: {e}")

    except Exception as e:
        logger.error(f"   ❌ Error tabla ANI: {e}")

    logger.info(f"   📋 {len(novedades)} novedades extraídas")
    return novedades


CATEGORIAS = {
    "obras": ["obras", "construcción", "mantenimiento", "rehabilitación", "ampliación"],
    "cierre total": ["cierre total", "cerrada", "cerrado"],
    "paso restringido": ["restringido", "un carril", "controlado"],
    "derrumbe": ["derrumbe", "deslizamiento"],
    "congestión": ["congestión", "demoras"],
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


def descubrir():
    """Guarda screenshot + HTML para inspección."""
    import time

    debug_dir = "data/debug"
    os.makedirs(debug_dir, exist_ok=True)

    logger.info("🔍 MODO DESCUBRIMIENTO — ANI")
    driver = crear_driver(headless=True, timeout=30)

    try:
        driver.get(FUENTE["url"])
        time.sleep(5)
        scroll_completo(driver, pausa=2)

        driver.save_screenshot(os.path.join(debug_dir, "ani_screenshot.png"))

        with open(os.path.join(debug_dir, "ani_page.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        from selenium.webdriver.common.by import By
        tablas = driver.find_elements(By.CSS_SELECTOR, "table")
        logger.info(f"   📊 Tablas: {len(tablas)}")
        for i, t in enumerate(tablas):
            filas = t.find_elements(By.CSS_SELECTOR, "tr")
            logger.info(f"      Tabla {i}: {len(filas)} filas")

        logger.info("   👉 Inspecciona data/debug/ y actualiza SELECTORES")
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
