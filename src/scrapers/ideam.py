"""
Scraper IDEAM — Alertas climáticas y riesgo de deslizamientos.
https://www.ideam.gov.co

El IDEAM publica alertas sobre lluvias intensas, riesgo de deslizamientos
y condiciones climáticas que afectan las vías. El sitio es dinámico.

Estrategia:
1. Intenta RSS feeds del IDEAM (más estable)
2. Si falla, usa Selenium para la página de alertas

Modo descubrimiento:
    python -m src.scrapers.ideam --descubrir
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
FUENTE = FUENTES["ideam"]

# =============================================================================
# URLs Y SELECTORES
# =============================================================================

# RSS feeds del IDEAM (más estables que el sitio web)
RSS_URLS = [
    "https://www.ideam.gov.co/web/tiempo-y-clima/pronostico-del-dia",
    "http://www.ideam.gov.co/rss",
]

# Páginas de alertas para scraping con Selenium
ALERTAS_URLS = [
    "https://www.ideam.gov.co",
    "https://www.ideam.gov.co/web/tiempo-y-clima/alertas",
]

SELECTORES = {
    # Para alertas en la página principal
    "contenedor": ".alerta, .alert, .portlet-body, .journal-content, .web-content-column, article",
    "items_alerta": ".alerta-item, .alert-item, .entry-body, p, li",

    # Para la tabla de pronósticos/alertas
    "tabla": "table",
    "filas": "tbody tr, tr",
    "celdas": "td",
}

# Keywords que indican alerta relevante para vías
KEYWORDS_RELEVANTES = [
    "deslizamiento", "lluvia", "lluvias", "alerta", "roja", "naranja",
    "amarilla", "creciente", "inundación", "tormenta", "granizo",
    "derrumbe", "vía", "via", "carretera", "cundinamarca", "boyacá",
    "santander", "tolima", "antioquia", "cauca", "nariño", "meta",
    "caldas", "risaralda", "quindío", "valle",
]


@safe_scrape(max_retries=2, delay=5, nombre_fuente="IDEAM")
def scrape():
    """
    Consulta IDEAM para alertas climáticas relevantes para vías.
    Intenta RSS primero, luego Selenium.
    """
    # Intento 1: RSS/HTML directo
    try:
        novedades = _scrape_alertas_requests()
        if novedades:
            return novedades
    except Exception as e:
        logger.info(f"   ⚠️  requests falló ({e}), probando Selenium...")

    # Intento 2: Selenium
    return _scrape_selenium()


def _scrape_alertas_requests():
    """Intenta extraer alertas con requests + BS4."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    }

    novedades = []

    for url in ALERTAS_URLS:
        try:
            logger.info(f"   🌐 Consultando {url} (requests)")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            novedades.extend(_extraer_alertas_bs4(soup, url))

        except Exception as e:
            logger.debug(f"   Error en {url}: {e}")

    return _deduplicar(novedades)


def _extraer_alertas_bs4(soup, url):
    """Extrae alertas de una página del IDEAM usando BS4."""
    novedades = []

    # Buscar textos que contengan keywords de alertas
    # El IDEAM suele publicar alertas en párrafos o divs con clase "alerta"
    contenedores = soup.select(SELECTORES["contenedor"])

    for cont in contenedores:
        texto = cont.get_text(strip=True)
        texto_lower = texto.lower()

        # Filtrar solo contenido relevante para vías
        if len(texto) < 20 or len(texto) > 2000:
            continue

        relevante = sum(1 for kw in KEYWORDS_RELEVANTES if kw in texto_lower)
        if relevante < 2:
            continue

        # Determinar tipo de alerta
        tipo = _inferir_tipo(texto_lower)
        ubicacion = _extraer_ubicacion(texto)

        novedades.append({
            "corredor_texto": f"Alerta climática — {ubicacion}",
            "ubicacion": ubicacion,
            "tipo_novedad": tipo,
            "estado": _extraer_nivel_alerta(texto_lower),
            "fuente": FUENTE["nombre"],
            "link": url,
            "fecha_reporte": timestamp_ahora(),
            "detalle": limpiar_texto(texto[:300]),
        })

    return novedades


def _scrape_selenium():
    """Extracción con Selenium para contenido dinámico."""
    from selenium.webdriver.common.by import By

    driver = crear_driver(headless=True, timeout=25)
    novedades = []

    try:
        for url in ALERTAS_URLS:
            try:
                logger.info(f"   🌐 Selenium: {url}")
                driver.get(url)

                import time
                time.sleep(4)
                scroll_completo(driver, pausa=1)

                # Buscar contenedores de alertas
                contenedores = driver.find_elements(By.CSS_SELECTOR, SELECTORES["contenedor"])

                for cont in contenedores:
                    texto = cont.text.strip()
                    texto_lower = texto.lower()

                    if len(texto) < 20 or len(texto) > 2000:
                        continue

                    relevante = sum(1 for kw in KEYWORDS_RELEVANTES if kw in texto_lower)
                    if relevante < 2:
                        continue

                    novedades.append({
                        "corredor_texto": f"Alerta climática — {_extraer_ubicacion(texto)}",
                        "ubicacion": _extraer_ubicacion(texto),
                        "tipo_novedad": _inferir_tipo(texto_lower),
                        "estado": _extraer_nivel_alerta(texto_lower),
                        "fuente": FUENTE["nombre"],
                        "link": url,
                        "fecha_reporte": timestamp_ahora(),
                        "detalle": limpiar_texto(texto[:300]),
                    })

            except Exception as e:
                logger.debug(f"   Error en {url}: {e}")

    finally:
        driver.quit()

    return _deduplicar(novedades)


# =============================================================================
# UTILIDADES
# =============================================================================

DEPARTAMENTOS = [
    "Cundinamarca", "Boyacá", "Santander", "Tolima", "Antioquia",
    "Caldas", "Risaralda", "Quindío", "Valle del Cauca", "Cauca",
    "Nariño", "Meta", "Norte de Santander", "Cesar", "Magdalena",
    "Atlántico", "Bolívar",
]


def _extraer_ubicacion(texto):
    """Extrae departamentos o regiones mencionadas en el texto."""
    encontrados = [d for d in DEPARTAMENTOS if d.lower() in texto.lower()]
    if encontrados:
        return ", ".join(encontrados[:3])
    return "Zona no especificada"


def _inferir_tipo(texto):
    if any(x in texto for x in ["deslizamiento", "derrumbe"]):
        return "deslizamiento"
    if any(x in texto for x in ["inundación", "creciente", "desbordamiento"]):
        return "inundación"
    if any(x in texto for x in ["lluvia", "lluvias", "tormenta", "granizo"]):
        return "lluvias"
    if "viento" in texto:
        return "viento fuerte"
    return "alerta climática"


def _extraer_nivel_alerta(texto):
    if "alerta roja" in texto:
        return "Alerta ROJA — Riesgo muy alto"
    if "alerta naranja" in texto:
        return "Alerta NARANJA — Riesgo alto"
    if "alerta amarilla" in texto:
        return "Alerta AMARILLA — Riesgo moderado"
    return "Alerta climática activa"


def _deduplicar(novedades):
    """Elimina novedades duplicadas por ubicación + tipo."""
    vistos = set()
    unicos = []
    for n in novedades:
        clave = f"{n['ubicacion']}-{n['tipo_novedad']}"
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(n)
    return unicos


# =============================================================================
# MODO DESCUBRIMIENTO
# =============================================================================

def descubrir():
    import time

    debug_dir = "data/debug"
    os.makedirs(debug_dir, exist_ok=True)

    logger.info("🔍 MODO DESCUBRIMIENTO — IDEAM")

    # Requests
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"}
    for url in ALERTAS_URLS:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            fname = url.replace("https://", "").replace("/", "_")[:50]
            with open(os.path.join(debug_dir, f"ideam_req_{fname}.html"), "w", encoding="utf-8") as f:
                f.write(r.text)
            logger.info(f"   📄 HTML (requests): {url}")
        except Exception as e:
            logger.warning(f"   requests falló para {url}: {e}")

    # Selenium
    driver = crear_driver(headless=True, timeout=25)
    try:
        driver.get(FUENTE["url"])
        time.sleep(5)
        scroll_completo(driver, pausa=2)

        driver.save_screenshot(os.path.join(debug_dir, "ideam_screenshot.png"))
        with open(os.path.join(debug_dir, "ideam_selenium.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("   📸 Screenshot + HTML (Selenium) guardados")
        logger.info("   👉 Inspecciona data/debug/")
    finally:
        driver.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    if "--descubrir" in sys.argv:
        descubrir()
    else:
        resultado = scrape()
        print(f"\nAlertas: {len(resultado)}")
        for n in resultado:
            print(f"  [{n['tipo_novedad'].upper()}] {n['ubicacion']}")
            print(f"  {n['estado']}")
