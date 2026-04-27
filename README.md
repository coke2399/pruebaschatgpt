# Scraper SEO de competidores (Python)

Este proyecto incluye un script en Python para analizar una lista de URLs y extraer métricas SEO on-page.

## ¿Qué extrae?

Para cada URL del archivo `urls.csv`:

- `title`
- `meta description`
- `H1`
- `H2`
- `canonical`
- `status code`
- `número de palabras`
- `enlaces internos`
- `enlaces externos`
- `imágenes sin ALT`
- `error` (si la URL está caída, bloqueada o falla la petición)
- `blocked_by_robots` (si robots.txt impide el acceso)

## Requisitos

- Python 3.9+
- Paquetes:
  - `requests`
  - `beautifulsoup4`
  - `pandas`

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
