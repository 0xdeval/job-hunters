from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from job_hunting.tools.company_public_search import (
    PublicCompanySearch,
    SearchResult,
    extract_search_results,
)
from job_hunting.tools.search_result import SearchResult as SharedSearchResult


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_extract_search_results_reads_duckduckgo_result_links():
    html = """
    <html><body>
      <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fcareers">Example Careers</a>
      <a class="result__a" href="https://jobs.lever.co/example">Example Lever</a>
      <a class="not-result" href="https://ignore.me">Ignore</a>
    </body></html>
    """

    results = extract_search_results(html)

    assert results == [
        # DDG redirect URLs are normalized to target links.
        SearchResult(title="Example Careers", url="https://example.com/careers"),
        SearchResult(title="Example Lever", url="https://jobs.lever.co/example"),
    ]


def test_public_company_search_slices_to_max_results_and_builds_query(monkeypatch):
    html = """
    <a class="result__a" href="https://a.com/jobs">A</a>
    <a class="result__a" href="https://b.com/jobs">B</a>
    <a class="result__a" href="https://c.com/jobs">C</a>
    """
    captured = {}

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["ua"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return _FakeResponse(html)

    monkeypatch.setattr("job_hunting.tools.company_public_search.urlopen", _fake_urlopen)

    searcher = PublicCompanySearch()
    results = searcher.search("Acme Corp careers", max_results=2)

    assert [result.title for result in results] == ["A", "B"]
    parsed = urlparse(captured["url"])
    assert parsed.scheme == "https"
    assert parsed.netloc == "duckduckgo.com"
    assert parse_qs(parsed.query)["q"] == ["Acme Corp careers"]
    assert captured["ua"]
    assert captured["timeout"] == 20


def test_ddg_uddg_value_is_not_double_decoded():
    html = """
    <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fjobs%252Fplatform">Encoded</a>
    """

    results = extract_search_results(html)

    assert results == [
        SearchResult(title="Encoded", url="https://example.com/jobs%2Fplatform"),
    ]


def test_module_search_result_uses_shared_model():
    assert SearchResult is SharedSearchResult
