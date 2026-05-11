from __future__ import annotations

import re
from urllib.parse import urlparse

from job_hunting.tools.search_result import SearchResult


class CareerPageResolver:
    _SUPPORTED_ATS_HOSTS = {
        "jobs.ashbyhq.com",
        "job-boards.greenhouse.io",
        "boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
        "jobs.lever.co",
        "jobs.personio.com",
        "apply.workable.com",
    }
    _CAREER_SEGMENT_MARKERS = {
        ("careers",),
        ("jobs",),
        ("join", "us"),
        ("work", "with", "us"),
    }
    _COMPANY_SUFFIX_TOKENS = {
        "inc",
        "ltd",
        "llc",
        "corp",
        "corporation",
        "limited",
        "labs",
    }

    def resolve(self, company: str, results: list[SearchResult]) -> str:
        company_tokens = self._company_tokens(company)

        for result in results:
            if self._is_supported_ats_url(result.url) and self._result_matches_company(
                result,
                company_tokens,
            ):
                return result.url

        for result in results:
            if self._is_career_like_url(result.url) and self._result_matches_company(
                result,
                company_tokens,
            ):
                return result.url

        return ""

    def _is_supported_ats_url(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().removeprefix("www.")
        path = (parsed.path or "").lower()

        if host in self._SUPPORTED_ATS_HOSTS:
            return True

        # Personio/BambooHR deployments can include company subdomains.
        if host.endswith(".jobs.personio.com"):
            return True
        if host.endswith(".bamboohr.com") or host == "bamboohr.com":
            return "/careers" in path

        return False

    def _is_career_like_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        for raw_segment in path.split("/"):
            segment_tokens = tuple(self._tokenize(raw_segment))
            if segment_tokens in self._CAREER_SEGMENT_MARKERS:
                return True
        return False

    def _company_tokens(self, company: str) -> set[str]:
        tokens = {token for token in self._tokenize(company) if token not in self._COMPANY_SUFFIX_TOKENS}
        if tokens:
            return tokens
        # Fallback for names mostly made of stripped suffixes.
        return set(self._tokenize(company))

    def _result_matches_company(self, result: SearchResult, company_tokens: set[str]) -> bool:
        if not company_tokens:
            return False

        parsed = urlparse(result.url)
        searchable_tokens = set(self._tokenize(result.title))
        searchable_tokens.update(self._tokenize(parsed.netloc))

        for raw_segment in (parsed.path or "").split("/"):
            searchable_tokens.update(self._tokenize(raw_segment))

        return any(token in searchable_tokens for token in company_tokens)

    def _tokenize(self, value: str) -> list[str]:
        return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]
