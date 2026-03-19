"""
Scraper INVÍAS — Estado oficial de vías nacionales.
https://www.invias.gov.co/index.php/estado-de-las-vias

INVÍAS publica una tabla/listado con el estado de las vías nacionales.
El sitio carga contenido dinámicamente con JavaScript → requiere Selenium.

=============================================================================
CÓMO AJUSTAR LOS SELECTORES:

1. Ejecuta:  python -m src.scrapers.invias --descubrir
   Esto abre el sitio, guarda un screenshot y el HTML en data/debug/

2. Abre el HTML en tu navegador, inspecciona la estructura de la tabla.

3. Actualiza los selectores en la sección SELECTORES de este archivo.

4. Ejecuta:  python -m src.scrapers.invias
   Para probar la extracción con los selectores nuevos.
=============================================================================
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
FUENTE = FUENTES["invias"]

# =============================================================================
# SELECTORES — AJUSTAR SEGÚN LA ESTRUCTURA REAL DEL SITIO
# =============================================================================
# Usa el modo --descubrir para inspeccionar la página y actualizar.
#
# INVÍAS típicamente muestra los datos en una tabla HTML o en bloques <div>.
# Los selectores por defecto buscan patrones comunes, pero probablemente
# necesitarás ajustarlos.

SELECTORES = {
    # Contenedor principal de la tabla o listado de vías
    "contenedor": "table.table, #estado-vias, .views-table, .table-responsive table, .field-items table",

    # Filas de datos dentro del contenedor
    "filas": "tbody tr",

    # Celdas dentro de cada fila
    "celdas": "td",

    # Índices de columnas (ajustar al orden real de la tabla)
    "col_corredor": 0,        # Nombre del corredor o vía
    "col_sector": 1,          # Sector o ubicación específica
    "col_novedad": 2,         # Tipo de novedad o evento
    "col_estado": 3,          # Estado actual de la vía
    "col_observaciones": 4,   # Observaciones o detalles
}

# Filas a ignorar (encabezados repetidos, subtotales, vacíos)
FILAS_IGNORAR = ["total", "resumen", "departamento", "---", "corredor"]


# =============================================================================
# SCRAPER PRINCIPAL
# =============================================================================

@safe_scrape(max_retries=2, delay=5, nombre_fuente="INVÍAS")
def scrape():
    """
    Consulta INVÍAS y extrae novedades de vías nacionales.

    Returns:
        list[dict]: Novedades con formato estándar del sistema.
    """
    driver = crear_driver(headless=True, timeout=30)

    try:
        logger.info(f"   🌐 Accediendo a {FUENTE['url']}")
        driver.get(FUENTE["url"])

        # Esperar carga del contenido dinámico
        try:
            esperar_elemento(driver, SELECTORES["contenedor"], timeout=20)
            logger.info("   ✅ Contenido cargado")
        except Exception:
            logger.info("   ⏳ Contenedor no encontrado directo, haciendo scroll...")
            scroll_completo(driver, pausa=1.5)
            esperar_elemento(driver, SELECTORES["contenedor"], timeout=10)

        return _extraer_novedades(driver)

    finally:
        driver.quit()


def _extraer_novedades(driver):
    """Extrae novedades de la tabla de INVÍAS."""
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

                # Filtrar filas irrelevantes
                fila_lower = " ".join(textos).lower()
                if any(x in fila_lower for x in FILAS_IGNORAR):
                    continue

                corredor = _safe_idx(textos, SELECTORES["col_corredor"])
                sector = _safe_idx(textos, SELECTORES["col_sector"])
                novedad = _safe_idx(textos, SELECTORES["col_novedad"])
                estado = _safe_idx(textos, SELECTORES["col_estado"])
                observaciones = _safe_idx(textos, SELECTORES["col_observaciones"])

                if not corredor and not sector:
                    continue

                # Filtrar operación normal
                if estado.lower() in ["normal", "operación normal", "transitable", ""]:
                    continue

                novedades.append({
                    "corredor_texto": f"{corredor} {sector}".strip(),
                    "ubicacion": limpiar_texto(f"{corredor}, {sector}") if sector else corredor,
                    "tipo_novedad": _inferir_tipo(novedad, estado, observaciones),
                    "estado": estado or novedad,
                    "fuente": FUENTE["nombre"],
                    "link": FUENTE["url"],
                    "fecha_reporte": timestamp_ahora(),
                    "detalle": limpiar_texto(observaciones),
                })

            except Exception as e:
                logger.debug(f"   Error fila {i}: {e}")

    except Exception as e:
        logger.error(f"   ❌ Error tabla INVÍAS: {e}")

    logger.info(f"   📋 {len(novedades)} novedades con contenido relevante")
    return novedades


# =============================================================================
# UTILIDADES
# =============================================================================

CATEGORIAS = {
    "cierre total": ["cierre total", "cerrada", "cerrado", "interrumpida"],
    "derrumbe": ["derrumbe", "deslizamiento", "remoción en masa"],
    "bloqueo": ["bloqueo", "protesta", "paro", "manifestación"],
    "accidente": ["accidente", "siniestro", "volcamiento"],
    "obras": ["obras", "mantenimiento", "rehabilitación", "construcción"],
    "paso restringido": ["paso restringido", "un carril", "controlado"],
    "inundación": ["inundación", "inundada", "creciente"],
    "lluvias": ["lluvia", "lluvias", "tormenta"],
    "congestión": ["congestión", "congestionamiento"],
}


def _inferir_tipo(novedad, estado, detalle):
    """Infiere tipo de novedad por keywords."""
    texto = f"{novedad} {estado} {detalle}".lower()
    for tipo, kws in CATEGORIAS.items():
        if any(kw in texto for kw in kws):
            return tipo
    return novedad.lower() if novedad else "novedad"


def _safe_idx(lista, idx, default=""):
    try:
        return lista[idx].strip()
    except (IndexError, AttributeError):
        return default


# =============================================================================
# MODO DESCUBRIMIENTO
# =============================================================================

def descubrir():
    """Guarda screenshot + HTML del sitio para inspección de selectores."""
    import time

    debug_dir = "data/debug"
    os.makedirs(debug_dir, exist_ok=True)

    logger.info("🔍 MODO DESCUBRIMIENTO — INVÍAS")
    logger.info(f"   Accediendo a {FUENTE['url']}...")

    driver = crear_driver(headless=True, timeout=30)

    try:
        driver.get(FUENTE["url"])
        time.sleep(5)
        scroll_completo(driver, pausa=2)

        # Screenshot
        ss = os.path.join(debug_dir, "invias_screenshot.png")
        driver.save_screenshot(ss)
        logger.info(f"   📸 Screenshot: {ss}")

        # HTML
        html = os.path.join(debug_dir, "invias_page.html")
        with open(html, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info(f"   📄 HTML: {html}")

        # Detectar estructura
        from selenium.webdriver.common.by import By
        tablas = driver.find_elements(By.CSS_SELECTOR, "table")
        logger.info(f"   📊 Tablas encontradas: {len(tablas)}")

        for i, tabla in enumerate(tablas):
            filas = tabla.find_elements(By.CSS_SELECTOR, "tr")
            logger.info(f"      Tabla {i}: {len(filas)} filas")
            if filas:
                celdas = filas[0].find_elements(By.CSS_SELECTOR, "th, td")
                heads = [c.text.strip()[:30] for c in celdas]
                logger.info(f"      Encabezados: {heads}")

        # Buscar contenedores por clase/id
        divs = driver.find_elements(
            By.CSS_SELECTOR,
            "[class*='estado'], [class*='vias'], [class*='table'], [id*='estado'], [id*='vias']"
        )
        logger.info(f"   🔎 Contenedores candidatos: {len(divs)}")
        for d in divs[:8]:
            cls = d.get_attribute("class") or ""
            did = d.get_attribute("id") or ""
            logger.info(f"      <{d.tag_name} class='{cls[:60]}' id='{did}'>")

        logger.info("\n   👉 Inspecciona data/debug/ y actualiza SELECTORES en invias.py")

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
            print(f"  Estado: {n['estado']}")
