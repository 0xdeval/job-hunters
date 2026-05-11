from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen

from job_hunting.tools.search_result import SearchResult


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._current_href: str | None = None
        self._collect_text = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        attr_map = dict(attrs)
        classes = (attr_map.get("class") or "").split()
        if "result__a" not in classes:
            return

        self._current_href = attr_map.get("href")
        self._collect_text = True
        self._title_parts = []

    def handle_data(self, data: str) -> None:
        if self._collect_text:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._collect_text:
            return

        title = "".join(self._title_parts).strip()
        href = (self._current_href or "").strip()

        if title and href:
            self.results.append(SearchResult(title=title, url=_resolve_duckduckgo_url(href)))

        self._current_href = None
        self._collect_text = False
        self._title_parts = []


def _resolve_duckduckgo_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    return url


def extract_search_results(html: str) -> list[SearchResult]:
    parser = _DuckDuckGoParser()
    parser.feed(html)
    return parser.results


class PublicCompanySearch:
    _BASE_URL = "https://duckduckgo.com/html/?q="
    _USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        encoded_query = quote_plus(query)
        url = f"{self._BASE_URL}{encoded_query}"
        request = Request(url, headers={"User-Agent": self._USER_AGENT})

        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")

        return extract_search_results(html)[:max_results]
