"""
Scraper Policía de Tránsito y Transporte.
Fuente original: Twitter/X @TransitoPolicia

El acceso directo a la API de Twitter/X requiere cuenta de pago.
Este scraper usa estrategias alternativas:

1. Nitter (mirror público de Twitter — puede estar caído)
2. Google Search para tweets recientes
3. Página web oficial de la DITRA si existe

Modo descubrimiento:
    python -m src.scrapers.policia_transito --descubrir
"""

import os
import sys
import re
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import FUENTES
from src.scrapers.base import (
    crear_driver, safe_scrape,
    scroll_completo, timestamp_ahora, limpiar_texto,
)

logger = logging.getLogger(__name__)
FUENTE = FUENTES["policia_transito"]

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

TWITTER_USER = "TransitoPolicia"

# Instancias de Nitter públicas (mirrors de Twitter sin API)
# Estas cambian frecuentemente — actualizar si dejan de funcionar
NITTER_INSTANCES = [
    f"https://nitter.net/{TWITTER_USER}",
    f"https://nitter.privacydev.net/{TWITTER_USER}",
    f"https://nitter.poast.org/{TWITTER_USER}",
]

# URL para búsqueda de Google como fallback
GOOGLE_SEARCH_URL = "https://www.google.com/search"

# Keywords para filtrar tweets relevantes sobre vías
KEYWORDS_VIAS = [
    "vía", "via", "carretera", "cierre", "accidente", "bloqueo",
    "derrumbe", "restricción", "congestión", "tránsito", "transito",
    "precaución", "novedad", "emergencia", "km", "sector",
    "bogotá", "medellín", "cali", "bucaramanga",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9",
}


@safe_scrape(max_retries=2, delay=5, nombre_fuente="Policía de Tránsito")
def scrape():
    """
    Consulta alertas de la Policía de Tránsito.
    Intenta múltiples fuentes en orden de prioridad.
    """
    # Intento 1: Nitter (mirror de Twitter)
    for nitter_url in NITTER_INSTANCES:
        try:
            novedades = _scrape_nitter(nitter_url)
            if novedades:
                return novedades
        except Exception as e:
            logger.debug(f"   Nitter falló ({nitter_url}): {e}")

    # Intento 2: Búsqueda web
    try:
        novedades = _scrape_busqueda_web()
        if novedades:
            return novedades
    except Exception as e:
        logger.debug(f"   Búsqueda web falló: {e}")

    # Intento 3: Selenium directo
    try:
        return _scrape_selenium()
    except Exception as e:
        logger.warning(f"   Selenium falló: {e}")

    logger.warning("   ⚠️  No se pudo obtener datos de Policía de Tránsito")
    return []


def _scrape_nitter(base_url):
    """Extrae tweets recientes de Nitter."""
    logger.info(f"   🌐 Probando Nitter: {base_url}")

    response = requests.get(base_url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Nitter usa la clase "timeline-item" para cada tweet
    tweets = soup.select(".timeline-item .tweet-content, .tweet-body .tweet-content")

    if not tweets:
        # Intentar selectores alternativos
        tweets = soup.select(".entry-content, .status-content, article p")

    logger.info(f"   📊 {len(tweets)} tweets encontrados")

    novedades = []
    for tweet in tweets[:20]:  # Últimos 20 tweets
        texto = tweet.get_text(strip=True)
        texto_lower = texto.lower()

        # Filtrar solo tweets sobre vías
        relevancia = sum(1 for kw in KEYWORDS_VIAS if kw in texto_lower)
        if relevancia < 2:
            continue

        novedades.append({
            "corredor_texto": _extraer_corredor(texto),
            "ubicacion": _extraer_ubicacion(texto),
            "tipo_novedad": _inferir_tipo(texto_lower),
            "estado": _extraer_estado(texto),
            "fuente": FUENTE["nombre"],
            "link": FUENTE["url"],
            "fecha_reporte": timestamp_ahora(),
            "detalle": limpiar_texto(texto[:300]),
        })

    return novedades


def _scrape_busqueda_web():
    """Busca noticias recientes de @TransitoPolicia sobre vías."""
    logger.info("   🌐 Buscando alertas viales (búsqueda web)")

    query = f"@{TWITTER_USER} vía cierre accidente bloqueo"
    params = {"q": query, "tbm": "nws", "tbs": "qdr:d"}  # Últimas 24h

    response = requests.get(
        GOOGLE_SEARCH_URL, params=params, headers=HEADERS, timeout=10
    )

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Extraer resultados de búsqueda
    resultados = soup.select("div.g, .result, article")
    novedades = []

    for resultado in resultados[:10]:
        titulo = resultado.select_one("h3, .title")
        snippet = resultado.select_one(".snippet, .st, p")

        if not titulo:
            continue

        texto = f"{titulo.get_text()} {snippet.get_text() if snippet else ''}"
        texto_lower = texto.lower()

        relevancia = sum(1 for kw in KEYWORDS_VIAS if kw in texto_lower)
        if relevancia < 2:
            continue

        novedades.append({
            "corredor_texto": _extraer_corredor(texto),
            "ubicacion": _extraer_ubicacion(texto),
            "tipo_novedad": _inferir_tipo(texto_lower),
            "estado": _extraer_estado(texto),
            "fuente": FUENTE["nombre"],
            "link": FUENTE["url"],
            "fecha_reporte": timestamp_ahora(),
            "detalle": limpiar_texto(texto[:300]),
        })

    return novedades


def _scrape_selenium():
    """Último recurso: Selenium para acceder a la fuente."""
    from selenium.webdriver.common.by import By

    driver = crear_driver(headless=True, timeout=25)

    try:
        # Intentar Nitter con Selenium
        for nitter_url in NITTER_INSTANCES[:2]:
            try:
                logger.info(f"   🌐 Selenium: {nitter_url}")
                driver.get(nitter_url)

                import time
                time.sleep(4)

                tweets = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".timeline-item .tweet-content, .tweet-body, article"
                )

                novedades = []
                for tw in tweets[:20]:
                    texto = tw.text.strip()
                    texto_lower = texto.lower()

                    relevancia = sum(1 for kw in KEYWORDS_VIAS if kw in texto_lower)
                    if relevancia < 2:
                        continue

                    novedades.append({
                        "corredor_texto": _extraer_corredor(texto),
                        "ubicacion": _extraer_ubicacion(texto),
                        "tipo_novedad": _inferir_tipo(texto_lower),
                        "estado": _extraer_estado(texto),
                        "fuente": FUENTE["nombre"],
                        "link": FUENTE["url"],
                        "fecha_reporte": timestamp_ahora(),
                        "detalle": limpiar_texto(texto[:300]),
                    })

                if novedades:
                    return novedades

            except Exception as e:
                logger.debug(f"   Selenium Nitter falló: {e}")

        return []
    finally:
        driver.quit()


# =============================================================================
# UTILIDADES DE EXTRACCIÓN DE TEXTO
# =============================================================================

CIUDADES = [
    "Bogotá", "Medellín", "Cali", "Bucaramanga", "Cúcuta",
    "Barranquilla", "Cartagena", "Villavicencio", "Pereira",
    "Manizales", "Armenia", "Ibagué", "Popayán", "Pasto",
    "Tunja", "Santa Marta",
]


def _extraer_corredor(texto):
    """Intenta extraer el corredor mencionado en el tweet."""
    # Buscar patrón "vía X - Y" o "vía X Y"
    match = re.search(r'v[ií]a\s+([\w\s]+[-–]\s*[\w\s]+)', texto, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:60]

    # Buscar ciudades mencionadas
    encontradas = [c for c in CIUDADES if c.lower() in texto.lower()]
    if len(encontradas) >= 2:
        return f"{encontradas[0]} – {encontradas[1]}"
    if encontradas:
        return f"Zona {encontradas[0]}"

    return "Corredor no especificado"


def _extraer_ubicacion(texto):
    """Extrae la ubicación mencionada."""
    # Buscar "Km XX" o "kilómetro XX"
    match = re.search(r'[Kk]m\s*\.?\s*(\d+)', texto)
    km = f"Km {match.group(1)}" if match else ""

    # Buscar "sector X"
    match_sector = re.search(r'[Ss]ector\s+([\w\s]+?)[\.,;]', texto)
    sector = match_sector.group(1).strip() if match_sector else ""

    ubicacion_parts = [p for p in [km, sector] if p]
    if ubicacion_parts:
        return ", ".join(ubicacion_parts)

    # Fallback: ciudades encontradas
    encontradas = [c for c in CIUDADES if c.lower() in texto.lower()]
    return encontradas[0] if encontradas else "Ubicación no especificada"


def _inferir_tipo(texto):
    if any(x in texto for x in ["accidente", "siniestro", "volcamiento", "choque"]):
        return "accidente"
    if any(x in texto for x in ["bloqueo", "protesta", "manifestación", "paro"]):
        return "bloqueo"
    if any(x in texto for x in ["cierre", "cerrada", "cerrado"]):
        return "cierre total"
    if any(x in texto for x in ["derrumbe", "deslizamiento"]):
        return "derrumbe"
    if any(x in texto for x in ["congestión", "represamiento"]):
        return "congestión"
    return "novedad vial"


def _extraer_estado(texto):
    texto_lower = texto.lower()
    if any(x in texto_lower for x in ["cerrado", "cerrada", "cierre total"]):
        return "Cerrado"
    if any(x in texto_lower for x in ["un carril", "restringido", "controlado"]):
        return "Paso restringido"
    if "habilitad" in texto_lower:
        return "Habilitado"
    return "Con novedad"


# =============================================================================
# MODO DESCUBRIMIENTO
# =============================================================================

def descubrir():
    debug_dir = "data/debug"
    os.makedirs(debug_dir, exist_ok=True)

    logger.info("🔍 MODO DESCUBRIMIENTO — Policía de Tránsito")

    # Probar Nitter
    for url in NITTER_INSTANCES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            fname = url.split("/")[2].replace(".", "_")
            with open(os.path.join(debug_dir, f"policia_{fname}.html"), "w", encoding="utf-8") as f:
                f.write(r.text)
            logger.info(f"   ✅ {url} — Status: {r.status_code}")

            soup = BeautifulSoup(r.text, "html.parser")
            tweets = soup.select(".timeline-item, .tweet-body, article")
            logger.info(f"      Tweets encontrados: {len(tweets)}")
        except Exception as e:
            logger.info(f"   ❌ {url} — {e}")

    logger.info("   👉 Revisa data/debug/ para ver qué instancia funciona")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    if "--descubrir" in sys.argv:
        descubrir()
    else:
        resultado = scrape()
        print(f"\nNovedades: {len(resultado)}")
        for n in resultado:
            print(f"  [{n['tipo_novedad'].upper()}] {n['corredor_texto']}")
            print(f"  {n['detalle'][:80]}")
