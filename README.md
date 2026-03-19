# 🛣️ BOT Estado de Vías — Transportes Cóndor

Bot automatizado que consulta, valida y consolida información sobre el estado de las vías nacionales y urbanas en Colombia, generando boletines técnicos diarios.

## Cómo funciona

El bot se ejecuta **3 veces al día** mediante GitHub Actions:

| Reporte | Hora (COT) | Propósito |
|---------|-----------|-----------|
| Primero | 6:00 AM | Planeación de despachos |
| Segundo | 12:00 PM | Actualización de novedades |
| Tercero | 5:00 PM | Cierre logístico del día |

### Flujo de ejecución

```
Scraping → Filtro por corredor → Clasificación de impacto → Análisis logístico → Boletín HTML/PDF → Correo + Web
```

## Corredores monitoreados

- Bogotá – Medellín
- Bogotá – Cali
- Bogotá – Eje Cafetero
- Bogotá – Bucaramanga
- Bogotá – Cúcuta
- Bogotá – Costa Caribe
- Bogotá – Popayán
- Bogotá – Pasto
- Bogotá – Villavicencio
- Bogotá – Boyacá

## Fuentes oficiales

- **INVÍAS** — Estado oficial de vías nacionales
- **ANI** — Vías concesionadas
- **Policía de Tránsito** — Accidentes y bloqueos
- **Movilidad Bogotá** — Estado vial urbano
- **IDEAM** — Alertas climáticas

## Configuración inicial

### 1. Crear el repositorio

```bash
git clone https://github.com/tu-usuario/bot-estado-vias.git
cd bot-estado-vias
pip install -r requirements.txt
```

### 2. Configurar GitHub Secrets

En tu repositorio → Settings → Secrets and variables → Actions:

| Secret | Descripción |
|--------|-------------|
| `GMAIL_USER` | Tu correo Gmail |
| `GMAIL_APP_PASSWORD` | App Password de Google (no tu contraseña normal) |
| `EMAIL_RECIPIENTS` | Correos destinatarios separados por coma |
| `GITHUB_PAGES_URL` | URL de tu GitHub Pages (ej: `https://usuario.github.io/bot-estado-vias`) |

### 3. Generar App Password de Gmail

1. Ve a https://myaccount.google.com/apppasswords
2. Selecciona "Correo" y "Otro (nombre personalizado)"
3. Copia la contraseña generada → ponla en `GMAIL_APP_PASSWORD`

### 4. Activar GitHub Pages

1. Ve a Settings → Pages en tu repositorio
2. Source: "Deploy from a branch"
3. Branch: `main`, carpeta: `/docs`
4. Guardar

### 5. Ejecución manual (prueba)

```bash
python main.py
```

O desde GitHub: Actions → "Generar Reporte Estado de Vías" → "Run workflow"

## Estructura del proyecto

```
bot-estado-vias/
├── .github/workflows/      ← GitHub Actions (cron 3x/día)
│   └── reporte.yml
├── src/
│   ├── scrapers/            ← Un archivo por fuente de datos
│   │   ├── invias.py
│   │   ├── ani.py
│   │   ├── policia_transito.py
│   │   ├── movilidad_bogota.py
│   │   └── ideam.py
│   ├── processing/          ← Filtrado, clasificación, análisis
│   │   ├── filter.py
│   │   ├── classify.py
│   │   └── analysis.py
│   ├── output/              ← Generación de HTML, PDF, JSON
│   │   ├── html_builder.py
│   │   ├── pdf_builder.py
│   │   └── json_builder.py
│   └── distribution/        ← Envío por correo
│       └── email_sender.py
├── templates/               ← Templates Jinja2
│   └── boletin.html
├── docs/                    ← GitHub Pages (dashboard + reportes)
│   ├── index.html
│   ├── reportes/
│   └── data/
├── data/                    ← Datos de configuración e histórico
├── main.py                  ← Orquestador principal
├── config.py                ← Toda la configuración centralizada
└── requirements.txt
```

## Agregar una nueva fuente

1. Crear `src/scrapers/nueva_fuente.py` con función `scrape()` que retorne lista de dicts estándar
2. Registrar en `config.py` → `FUENTES`
3. Agregar al `SCRAPER_MAP` en `src/scrapers/__init__.py`

## Agregar un nuevo corredor

Editar `config.py` → `CORREDORES` y agregar el nuevo corredor con sus keywords de matching.

---

*Transportes Cóndor te mantiene informado para que programes tu logística con anticipación y seguridad.*
