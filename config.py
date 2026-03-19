"""
Configuración central del BOT Estado de Vías - Transportes Cóndor
Todos los parámetros configurables del sistema están aquí.
"""

import os
from datetime import datetime

# =============================================================================
# INFORMACIÓN CORPORATIVA
# =============================================================================

EMPRESA = "Transportes Cóndor"
MENSAJE_INSTITUCIONAL = (
    "Transportes Cóndor te mantiene informado para que programes "
    "tu logística con anticipación y seguridad."
)

# =============================================================================
# CORREDORES LOGÍSTICOS MONITOREADOS
# =============================================================================

CORREDORES = [
    {
        "nombre": "Bogotá – Medellín",
        "keywords": [
            "medellín", "medellin", "la línea", "la linea",
            "guaduas", "honda", "marinilla", "santuario",
            "villeta", "tobiagrande", "facatativá",
        ],
    },
    {
        "nombre": "Bogotá – Cali",
        "keywords": [
            "cali", "ibagué", "ibague", "buga",
            "calarcá", "calarca", "la paila", "tuluá", "tulua",
            "cajamarca", "espinal", "girardot",
        ],
    },
    {
        "nombre": "Bogotá – Eje Cafetero",
        "keywords": [
            "pereira", "manizales", "armenia", "chinchiná",
            "chinchina", "dosquebradas", "santa rosa de cabal",
        ],
    },
    {
        "nombre": "Bogotá – Bucaramanga",
        "keywords": [
            "bucaramanga", "tunja", "barbosa", "oiba",
            "socorro", "san gil", "piedecuesta",
        ],
    },
    {
        "nombre": "Bogotá – Cúcuta",
        "keywords": [
            "cúcuta", "cucuta", "pamplona",
            "berlín", "berlin", "chinácota", "chinacota",
        ],
    },
    {
        "nombre": "Bogotá – Costa Caribe",
        "keywords": [
            "barranquilla", "cartagena", "santa marta",
            "aguachica", "bosconia", "fundación", "fundacion",
            "san alberto", "gamarra",
        ],
    },
    {
        "nombre": "Bogotá – Popayán",
        "keywords": [
            "popayán", "popayan", "piendamó", "piendamo",
            "santander de quilichao", "jamundí", "jamundi",
        ],
    },
    {
        "nombre": "Bogotá – Pasto",
        "keywords": [
            "pasto", "ipiales", "la unión", "la union",
            "el pedregal", "chachagüí", "chachagui",
        ],
    },
    {
        "nombre": "Bogotá – Villavicencio",
        "keywords": [
            "villavicencio", "guayabetal", "cáqueza", "caqueza",
            "chipaque", "quetame", "km 58",
            "vía al llano", "via al llano",
        ],
    },
    {
        "nombre": "Bogotá – Boyacá",
        "keywords": [
            "tunja", "duitama", "sogamoso", "paipa",
            "villa de leyva", "ventaquemada",
        ],
    },
]

# =============================================================================
# CLASIFICACIÓN DE IMPACTO
# =============================================================================

IMPACTO_ALTO = [
    "cierre total", "cierre", "derrumbe", "bloqueo", "protesta",
    "deslizamiento", "caída de puente", "colapso",
]

IMPACTO_MEDIO = [
    "paso restringido", "obras", "tránsito controlado",
    "paso a un carril", "restricción parcial", "mantenimiento",
]

IMPACTO_BAJO = [
    "congestión", "congestion", "lluvias", "precaución",
    "neblina", "niebla", "operación normal",
]

# =============================================================================
# PLANTILLAS DE ANÁLISIS LOGÍSTICO
# =============================================================================

ANALISIS_TEMPLATES = {
    "alto": {
        "impacto": "Impacto operativo ALTO. Se estiman demoras significativas de {horas} horas en el corredor {corredor}.",
        "recomendacion": "Se recomienda suspender despachos temporalmente por este corredor y evaluar rutas alternas.",
        "horas_estimadas": "4 a 8",
    },
    "medio": {
        "impacto": "Impacto operativo MEDIO. Se estiman demoras moderadas de {horas} horas en el corredor {corredor}.",
        "recomendacion": "Se recomienda ajustar itinerarios y priorizar despachos con mayor margen de tránsito.",
        "horas_estimadas": "2 a 4",
    },
    "bajo": {
        "impacto": "Impacto operativo BAJO en el corredor {corredor}. Tránsito con precaución.",
        "recomendacion": "No se requieren ajustes operativos significativos.",
        "horas_estimadas": "0 a 1",
    },
}

# =============================================================================
# FUENTES DE DATOS
# =============================================================================

FUENTES = {
    "invias": {
        "nombre": "INVÍAS",
        "url": "https://www.invias.gov.co/index.php/estado-de-las-vias",
        "tipo": "selenium",
        "activa": True,
    },
    "ani": {
        "nombre": "ANI",
        "url": "https://www.ani.gov.co",
        "tipo": "selenium",
        "activa": True,
    },
    "policia_transito": {
        "nombre": "Policía de Tránsito y Transporte",
        "url": "https://twitter.com/TransitoPolicia",
        "tipo": "api",
        "activa": True,
    },
    "movilidad_bogota": {
        "nombre": "Movilidad Bogotá",
        "url": "https://www.movilidadbogota.gov.co/web/estado_de_vias",
        "tipo": "requests",
        "activa": True,
    },
    "ideam": {
        "nombre": "IDEAM",
        "url": "https://www.ideam.gov.co",
        "tipo": "selenium",
        "activa": True,
    },
}

# =============================================================================
# CONFIGURACIÓN DE CORREO
# =============================================================================

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": os.environ.get("GMAIL_USER", ""),
    "sender_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
    "sender_name": f"{EMPRESA} - Estado de Vías",
}

DESTINATARIOS = [
    email.strip()
    for email in os.environ.get("EMAIL_RECIPIENTS", "").split(",")
    if email.strip()
]

# =============================================================================
# GITHUB PAGES
# =============================================================================

GITHUB_PAGES_URL = os.environ.get(
    "GITHUB_PAGES_URL",
    "https://tu-usuario.github.io/bot-estado-vias"
)
DOCS_DIR = "docs"
REPORTES_DIR = f"{DOCS_DIR}/reportes"
DATA_DIR = f"{DOCS_DIR}/data"

# =============================================================================
# GENERAL
# =============================================================================

TIMEZONE = "America/Bogota"
HISTORICO_CSV = "data/historico.csv"


def get_report_filename():
    """Genera nombre del reporte según fecha/hora actual."""
    now = datetime.now()
    return f"Boletin_Vias_TCCondor_{now.strftime('%Y%m%d_%H%M')}"


def get_report_period():
    """Determina el periodo del reporte según la hora."""
    hour = datetime.now().hour
    if hour < 10:
        return "Primer Reporte — Planeación de despachos nacionales"
    elif hour < 14:
        return "Segundo Reporte — Actualización de novedades"
    else:
        return "Tercer Reporte — Cierre logístico del día"
