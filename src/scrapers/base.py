"""
base.py — Módulo base para scrapers.

Centraliza la configuración de Selenium, manejo de errores,
reintentos y utilidades compartidas por todos los scrapers.

Uso:
    from src.scrapers.base import crear_driver, safe_scrape, extraer_texto

    driver = crear_driver()
    texto = extraer_texto(driver, "CSS_SELECTOR")
"""

import time
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN DE SELENIUM
# =============================================================================

def crear_driver(headless=True, timeout=20):
    """
    Crea y configura una instancia de Chrome WebDriver.

    Args:
        headless: Ejecutar sin interfaz gráfica (True para GitHub Actions).
        timeout: Timeout implícito en segundos.

    Returns:
        webdriver.Chrome configurado.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # Opciones necesarias para GitHub Actions (Ubuntu sin display)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Simular navegador real para evitar bloqueos
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Desactivar imágenes para mayor velocidad
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(timeout)
    driver.implicitly_wait(10)

    return driver


# =============================================================================
# DECORADOR DE REINTENTO
# =============================================================================

def safe_scrape(max_retries=2, delay=5, nombre_fuente="Fuente"):
    """
    Decorador que agrega reintentos y manejo de errores a funciones de scraping.

    Uso:
        @safe_scrape(max_retries=2, nombre_fuente="INVÍAS")
        def scrape():
            ...

    Si todos los reintentos fallan, retorna lista vacía en vez de lanzar excepción.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for intento in range(1, max_retries + 1):
                try:
                    resultado = func(*args, **kwargs)
                    return resultado
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"   ⚠️  {nombre_fuente} — intento {intento}/{max_retries} falló: {e}"
                    )
                    if intento < max_retries:
                        logger.info(f"   ⏳ Reintentando en {delay}s...")
                        time.sleep(delay)

            logger.error(
                f"   ❌ {nombre_fuente} — falló después de {max_retries} intentos: {last_error}"
            )
            # Retorna lista vacía para que el flujo continúe
            raise last_error

        return wrapper
    return decorator


# =============================================================================
# UTILIDADES DE EXTRACCIÓN
# =============================================================================

def esperar_elemento(driver, selector, timeout=15, by="css"):
    """
    Espera hasta que un elemento esté presente en la página.

    Args:
        driver: WebDriver activo.
        selector: Selector CSS o XPath.
        timeout: Tiempo máximo de espera en segundos.
        by: Tipo de selector ("css" o "xpath").

    Returns:
        WebElement encontrado.

    Raises:
        TimeoutException si no se encuentra el elemento.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    locator = By.CSS_SELECTOR if by == "css" else By.XPATH
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((locator, selector))
    )


def esperar_elementos(driver, selector, timeout=15, by="css"):
    """Espera y retorna múltiples elementos."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    locator = By.CSS_SELECTOR if by == "css" else By.XPATH
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((locator, selector))
    )


def extraer_texto(driver, selector, default="", by="css"):
    """
    Extrae texto de un elemento de forma segura.

    Returns:
        Texto del elemento o default si no se encuentra.
    """
    from selenium.webdriver.common.by import By

    try:
        locator = By.CSS_SELECTOR if by == "css" else By.XPATH
        element = driver.find_element(locator, selector)
        return element.text.strip()
    except Exception:
        return default


def extraer_textos(driver, selector, by="css"):
    """Extrae texto de múltiples elementos."""
    from selenium.webdriver.common.by import By

    try:
        locator = By.CSS_SELECTOR if by == "css" else By.XPATH
        elements = driver.find_elements(locator, selector)
        return [el.text.strip() for el in elements if el.text.strip()]
    except Exception:
        return []


def extraer_tabla(driver, tabla_selector, fila_selector, celda_selector, by="css"):
    """
    Extrae datos de una tabla HTML como lista de listas.

    Args:
        driver: WebDriver activo.
        tabla_selector: Selector de la tabla.
        fila_selector: Selector de las filas (relativo a la tabla).
        celda_selector: Selector de las celdas (relativo a cada fila).

    Returns:
        Lista de filas, donde cada fila es una lista de strings.
    """
    from selenium.webdriver.common.by import By

    try:
        locator = By.CSS_SELECTOR if by == "css" else By.XPATH
        tabla = driver.find_element(locator, tabla_selector)
        filas = tabla.find_elements(locator, fila_selector)

        datos = []
        for fila in filas:
            celdas = fila.find_elements(locator, celda_selector)
            textos = [celda.text.strip() for celda in celdas]
            if any(textos):  # Omitir filas vacías
                datos.append(textos)

        return datos
    except Exception as e:
        logger.debug(f"   Error extrayendo tabla: {e}")
        return []


def scroll_completo(driver, pausa=1.0):
    """
    Hace scroll hasta el final de la página para cargar contenido dinámico.
    Útil para páginas con lazy loading / infinite scroll.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pausa)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def timestamp_ahora():
    """Retorna timestamp actual formateado."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def limpiar_texto(texto):
    """Limpia whitespace excesivo de un texto extraído."""
    if not texto:
        return ""
    return " ".join(texto.split())
