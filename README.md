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
```

## Preparar `urls.csv`

Crea un archivo `urls.csv` con una URL por línea. Puedes usar cabecera o no.

Ejemplo con cabecera:

```csv
url
https://example.com
https://www.wikipedia.org
```

Ejemplo sin cabecera:

```csv
https://example.com
https://www.wikipedia.org
```

## Ejecución

Comando básico:

```bash
python scraper_seo.py --input urls.csv --output resultados.csv
```

Opciones útiles:

- `--delay 2` → pausa de 2 segundos entre peticiones.
- `--timeout 20` → timeout de 20 segundos por URL.
- `--ignore-robots` → ignora `robots.txt` (no recomendado).
- `--user-agent "MiBotSEO/1.0"` → cambia el User-Agent.

Ejemplo completo:

```bash
python scraper_seo.py --input urls.csv --output resultados.csv --delay 1.5 --timeout 15
```

## Respeto de `robots.txt`

Por defecto, el script intenta respetar `robots.txt` por dominio usando `urllib.robotparser`.

Si el archivo `robots.txt` no se puede leer (error de red, timeout, etc.), el script continúa para no bloquear todo el análisis ("cuando sea posible").

## Control de errores

El script captura y reporta errores comunes por URL, por ejemplo:

- timeout
- demasiadas redirecciones
- errores de red/bloqueos
- bloqueada por `robots.txt`

Estos errores se guardan en la columna `error` de `resultados.csv`.

## Salida

Se genera `resultados.csv` con una fila por URL y todas las métricas SEO extraídas.
