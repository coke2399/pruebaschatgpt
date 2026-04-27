import argparse
import csv
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup


DEFAULT_USER_AGENT = "SEOCompetitorScraper/1.0 (+https://example.com/bot-info)"


@dataclass
class PageResult:
    url: str
    status_code: Optional[int] = None
    title: str = ""
    meta_description: str = ""
    h1: str = ""
    h2: str = ""
    canonical: str = ""
    word_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    images_without_alt: int = 0
    error: str = ""
    blocked_by_robots: bool = False


class RobotsCache:
    """Cache sencillo de robots.txt por dominio."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._cache: Dict[str, RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        if robots_url not in self._cache:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                # Si robots.txt falla, seguimos ("cuando sea posible").
                return True
            self._cache[robots_url] = parser

        parser = self._cache[robots_url]
        return parser.can_fetch(self.user_agent, url)


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url


def extract_meta_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""


def extract_canonical(soup: BeautifulSoup, base_url: str) -> str:
    canonical = soup.find("link", attrs={"rel": lambda x: x and "canonical" in [r.lower() for r in x]})
    if canonical and canonical.get("href"):
        return urljoin(base_url, canonical["href"].strip())
    return ""


def extract_headings(soup: BeautifulSoup, tag_name: str) -> str:
    tags = soup.find_all(tag_name)
    texts = [t.get_text(" ", strip=True) for t in tags if t.get_text(strip=True)]
    return " | ".join(texts)


def count_words(soup: BeautifulSoup) -> int:
    for script_or_style in soup(["script", "style", "noscript"]):
        script_or_style.decompose()
    text = soup.get_text(" ", strip=True)
    words = [w for w in text.split() if w]
    return len(words)


def count_links(soup: BeautifulSoup, base_url: str) -> Tuple[int, int]:
    base_domain = urlparse(base_url).netloc.lower()
    internal = 0
    external = 0

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in {"http", "https"}:
            continue

        link_domain = parsed.netloc.lower()
        if link_domain == base_domain:
            internal += 1
        else:
            external += 1

    return internal, external


def count_images_without_alt(soup: BeautifulSoup) -> int:
    images = soup.find_all("img")
    return sum(1 for img in images if not img.get("alt") or not img.get("alt").strip())


def scrape_url(
    url: str,
    session: requests.Session,
    timeout: int,
    robots_cache: RobotsCache,
    respect_robots: bool,
) -> PageResult:
    result = PageResult(url=url)

    if respect_robots and not robots_cache.can_fetch(url):
        result.blocked_by_robots = True
        result.error = "Bloqueada por robots.txt"
        return result

    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        result.status_code = response.status_code

        # Parseamos HTML aunque no sea 200; puede servir para diagnóstico SEO.
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower() and not response.text.strip().lower().startswith("<!doctype html"):
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        result.title = soup.title.get_text(strip=True) if soup.title else ""
        result.meta_description = extract_meta_description(soup)
        result.h1 = extract_headings(soup, "h1")
        result.h2 = extract_headings(soup, "h2")
        result.canonical = extract_canonical(soup, response.url)
        result.word_count = count_words(soup)
        result.internal_links, result.external_links = count_links(soup, response.url)
        result.images_without_alt = count_images_without_alt(soup)

    except requests.exceptions.Timeout:
        result.error = "Timeout en la petición"
    except requests.exceptions.TooManyRedirects:
        result.error = "Demasiadas redirecciones"
    except requests.exceptions.RequestException as exc:
        result.error = f"Error de red: {exc}"
    except Exception as exc:
        result.error = f"Error inesperado: {exc}"

    return result


def read_urls(csv_path: str) -> List[str]:
    urls: List[str] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        sample = f.read(2048)
        f.seek(0)
        has_header = csv.Sniffer().has_header(sample)
        reader = csv.reader(f)

        if has_header:
            next(reader, None)

        for row in reader:
            if not row:
                continue
            url = normalize_url(row[0])
            if url:
                urls.append(url)

    # Quitar duplicadas manteniendo orden
    unique_urls = list(dict.fromkeys(urls))
    return unique_urls


def save_results(results: List[PageResult], output_csv: str) -> None:
    df = pd.DataFrame([r.__dict__ for r in results])
    df.to_csv(output_csv, index=False, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper SEO para analizar competidores.")
    parser.add_argument("--input", default="urls.csv", help="Archivo CSV con URLs (por defecto: urls.csv)")
    parser.add_argument("--output", default="resultados.csv", help="Archivo CSV de salida")
    parser.add_argument("--delay", type=float, default=1.5, help="Pausa entre peticiones en segundos")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout por petición en segundos")
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Ignora robots.txt (por defecto se respeta cuando sea posible)",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent para las peticiones")

    args = parser.parse_args()

    urls = read_urls(args.input)
    if not urls:
        raise SystemExit("No se encontraron URLs válidas en el archivo de entrada.")

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})
    robots_cache = RobotsCache(user_agent=args.user_agent)

    results: List[PageResult] = []

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Analizando: {url}")
        result = scrape_url(
            url=url,
            session=session,
            timeout=args.timeout,
            robots_cache=robots_cache,
            respect_robots=not args.ignore_robots,
        )
        results.append(result)
        if i < len(urls):
            time.sleep(max(args.delay, 0))

    save_results(results, args.output)
    print(f"Proceso completado. Resultados guardados en: {args.output}")


if __name__ == "__main__":
    main()
