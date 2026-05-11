# Company Lead Sourcing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cron-runnable company sourcing flow that finds reviewable company leads from bounded public search queries, stores them in `data/<date>/company_candidates.csv`, skips already known companies, and sends a Telegram review notification.

**Architecture:** Add a separate Company Sourcing Flow/Crew that reads profile/search criteria plus `knowledge/company-source-queries.yaml`, plans bounded queries, lets the Company Researcher own deduplication, resolves career pages, writes pending-review candidates, and notifies Telegram. Keep `knowledge/companies.csv` immutable and keep all generated leads under `data/`.

**Tech Stack:** Python 3.10+, CrewAI Flow/Crew, CrewAI tools, stdlib `csv`/`json`/`urllib`, existing Telegram bot library, pytest with fake source responses.

---

## File Structure

- Create `knowledge/company-source-queries.yaml`: managed query templates and ATS search domains. This file is under an ignored directory, so implementation must use `git add -f knowledge/company-source-queries.yaml`.
- Modify `src/job_hunting/utils.py`: add company candidate data paths and file discovery helpers.
- Create `src/job_hunting/tools/company_candidate_store.py`: normalize company identity, read known companies/candidates, skip duplicates, and write candidate CSV rows.
- Create `src/job_hunting/tools/company_query_planner.py`: load query config and expand bounded query templates from search criteria/profile-derived inputs.
- Create `src/job_hunting/tools/company_public_search.py`: public/free search adapter with a fakeable interface; automated tests must mock it.
- Create `src/job_hunting/tools/career_page_resolver.py`: resolve direct ATS/career URLs from search results and company websites.
- Modify `src/job_hunting/tools/telegram_notifier.py`: add a company candidate review notification path without buttons.
- Modify `src/job_hunting/tools/__init__.py`: export new tools.
- Create `src/job_hunting/crews/company_sourcing/crew.py`: CrewAI agents and tasks for source planning, company research, fit analysis, and candidate writing.
- Create `src/job_hunting/crews/company_sourcing/config/agents.yaml`: agent prompts, with Company Researcher explicitly owning deduplication.
- Create `src/job_hunting/crews/company_sourcing/config/tasks.yaml`: sequential tasks and expected outputs.
- Create `src/job_hunting/flows/company_sourcing_flow.py`: cron-style flow that creates today's output directory, kicks off the crew, counts new pending candidates, and sends Telegram notification.
- Modify `src/job_hunting/main.py`: add `run_company_sourcing`.
- Modify `pyproject.toml`: add `job_hunting_source_companies` script.
- Add tests:
  - `tests/test_company_candidate_store.py`
  - `tests/test_company_query_planner.py`
  - `tests/test_company_sourcing_flow.py`
  - extend `tests/test_telegram_notifier.py`

## Task 1: Add Candidate Data Paths

**Files:**
- Modify: `src/job_hunting/utils.py`
- Test: `tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

Append these tests to `tests/test_utils.py`:

```python
from pathlib import Path

from job_hunting.utils import (
    all_company_candidate_files,
    company_candidates_file,
)


def test_company_candidates_file_uses_run_date():
    assert company_candidates_file("2026-05-11") == Path("data/2026-05-11/company_candidates.csv")


def test_all_company_candidate_files_finds_historical_files(tmp_path, monkeypatch):
    first = tmp_path / "data" / "2026-05-10" / "company_candidates.csv"
    second = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("company,career_page\nAcme,https://acme.com/careers\n")
    second.write_text("company,career_page\nRamp,https://ramp.com/careers\n")

    monkeypatch.chdir(tmp_path)

    assert all_company_candidate_files() == [first, second]
```

- [ ] **Step 2: Run the tests to verify failure**

Run:

```bash
uv run pytest tests/test_utils.py::test_company_candidates_file_uses_run_date tests/test_utils.py::test_all_company_candidate_files_finds_historical_files -v
```

Expected: FAIL because `company_candidates_file` and `all_company_candidate_files` are not defined.

- [ ] **Step 3: Implement the utilities**

Add these functions to `src/job_hunting/utils.py`:

```python
def company_candidates_file(run_date: str) -> Path:
    return Path(f"data/{run_date}/company_candidates.csv")


def all_company_candidate_files() -> list[Path]:
    return sorted(Path("data").glob("*/company_candidates.csv"))
```

- [ ] **Step 4: Run the tests to verify pass**

Run:

```bash
uv run pytest tests/test_utils.py::test_company_candidates_file_uses_run_date tests/test_utils.py::test_all_company_candidate_files_finds_historical_files -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/utils.py tests/test_utils.py
git commit -m "Add company candidate data paths" \
  -m "Constraint: company leads are generated data under data/<date>/, not curated knowledge entries" \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Tested: uv run pytest tests/test_utils.py::test_company_candidates_file_uses_run_date tests/test_utils.py::test_all_company_candidate_files_finds_historical_files -v" \
  -m "Not-tested: full test suite"
```

## Task 2: Add Candidate Store and Deduplication

**Files:**
- Create: `src/job_hunting/tools/company_candidate_store.py`
- Modify: `src/job_hunting/tools/__init__.py`
- Test: `tests/test_company_candidate_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_company_candidate_store.py`:

```python
import csv
from pathlib import Path

from job_hunting.tools.company_candidate_store import (
    CompanyCandidate,
    CompanyCandidateStore,
    normalize_company_key,
)


def test_normalize_company_key_removes_case_and_suffix_noise():
    assert normalize_company_key("Ramp, Inc.") == "ramp"
    assert normalize_company_key("  ACME Labs Ltd  ") == "acme labs"


def test_store_skips_companies_already_in_knowledge_csv(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nRamp,https://ramp.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    candidate = CompanyCandidate(
        company="Ramp",
        career_page="https://ramp.com/careers",
        website="https://ramp.com",
        source="public_search",
        industry="FinTech",
        match_score=86,
        match_reason="FinTech and B2B SaaS fit.",
        status="pending_review",
        discovered_at="2026-05-11T09:00:00Z",
    )

    assert store.write_candidates([candidate]) == 0
    assert not Path("data/2026-05-11/company_candidates.csv").exists()


def test_store_skips_companies_already_in_historical_candidates(tmp_path, monkeypatch):
    historical = tmp_path / "data" / "2026-05-10"
    historical.mkdir(parents=True)
    (historical / "company_candidates.csv").write_text(
        "company,career_page,website,source,industry,match_score,match_reason,status,discovered_at\n"
        "Ramp,https://ramp.com/careers,https://ramp.com,public_search,FinTech,86,Existing,pending_review,2026-05-10T09:00:00Z\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "knowledge" / "companies.csv").write_text("Company,Career page\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    candidate = CompanyCandidate(
        company="Ramp",
        career_page="https://ramp.com/careers",
        website="https://ramp.com",
        source="public_search",
        industry="FinTech",
        match_score=86,
        match_reason="Duplicate from previous run.",
        status="pending_review",
        discovered_at="2026-05-11T09:00:00Z",
    )

    assert store.write_candidates([candidate]) == 0
    assert not Path("data/2026-05-11/company_candidates.csv").exists()


def test_store_writes_new_pending_review_candidates(tmp_path, monkeypatch):
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "knowledge" / "companies.csv").write_text("Company,Career page\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    candidate = CompanyCandidate(
        company="Mercury",
        career_page="https://mercury.com/jobs",
        website="https://mercury.com",
        source="public_search",
        industry="FinTech",
        match_score=84,
        match_reason="FinTech company with PM roles and remote-friendly positioning.",
        status="pending_review",
        discovered_at="2026-05-11T09:00:00Z",
    )

    assert store.write_candidates([candidate]) == 1

    output = Path("data/2026-05-11/company_candidates.csv")
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert rows == [
        {
            "company": "Mercury",
            "career_page": "https://mercury.com/jobs",
            "website": "https://mercury.com",
            "source": "public_search",
            "industry": "FinTech",
            "match_score": "84",
            "match_reason": "FinTech company with PM roles and remote-friendly positioning.",
            "status": "pending_review",
            "discovered_at": "2026-05-11T09:00:00Z",
        }
    ]
```

- [ ] **Step 2: Run the tests to verify failure**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py -v
```

Expected: FAIL because `company_candidate_store.py` does not exist.

- [ ] **Step 3: Implement the store**

Create `src/job_hunting/tools/company_candidate_store.py`:

```python
import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from job_hunting.utils import all_company_candidate_files, company_candidates_file


FIELDNAMES = [
    "company",
    "career_page",
    "website",
    "source",
    "industry",
    "match_score",
    "match_reason",
    "status",
    "discovered_at",
]


@dataclass(frozen=True)
class CompanyCandidate:
    company: str
    career_page: str
    website: str
    source: str
    industry: str
    match_score: int
    match_reason: str
    status: str
    discovered_at: str


def normalize_company_key(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[,\\.]", "", normalized)
    normalized = re.sub(r"\\b(inc|ltd|llc|limited|corp|corporation)\\b", "", normalized)
    normalized = re.sub(r"\\s+", " ", normalized)
    return normalized.strip()


class CompanyCandidateStore:
    def __init__(self, run_date: str) -> None:
        self.run_date = run_date

    def write_candidates(self, candidates: list[CompanyCandidate]) -> int:
        known = self._known_company_keys()
        unique_rows: list[CompanyCandidate] = []

        for candidate in candidates:
            key = normalize_company_key(candidate.company)
            if not key or key in known:
                continue
            known.add(key)
            unique_rows.append(candidate)

        if not unique_rows:
            return 0

        output = company_candidates_file(self.run_date)
        output.parent.mkdir(parents=True, exist_ok=True)
        file_exists = output.exists()

        with output.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            for candidate in unique_rows:
                writer.writerow(asdict(candidate))

        return len(unique_rows)

    def _known_company_keys(self) -> set[str]:
        keys: set[str] = set()
        keys.update(self._read_knowledge_companies(Path("knowledge/companies.csv")))
        for candidate_file in all_company_candidate_files():
            keys.update(self._read_candidate_companies(candidate_file))
        return keys

    @staticmethod
    def _read_knowledge_companies(path: Path) -> set[str]:
        if not path.exists():
            return set()
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return {
                normalize_company_key(row.get("Company", ""))
                for row in csv.DictReader(handle)
                if row.get("Company")
            }

    @staticmethod
    def _read_candidate_companies(path: Path) -> set[str]:
        if not path.exists():
            return set()
        with path.open(newline="", encoding="utf-8") as handle:
            return {
                normalize_company_key(row.get("company", ""))
                for row in csv.DictReader(handle)
                if row.get("company")
            }
```

Update `src/job_hunting/tools/__init__.py`:

```python
from job_hunting.tools.company_candidate_store import CompanyCandidateStore
```

Add `"CompanyCandidateStore"` to `__all__`.

- [ ] **Step 4: Run the tests to verify pass**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/tools/company_candidate_store.py src/job_hunting/tools/__init__.py tests/test_company_candidate_store.py
git commit -m "Add company candidate store" \
  -m "Constraint: Company Researcher must skip already known companies before downstream work" \
  -m "Rejected: updating historical candidate rows | v1 only appends new reviewable companies" \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Tested: uv run pytest tests/test_company_candidate_store.py -v" \
  -m "Not-tested: live sourcing flow"
```

## Task 3: Add Query Config and Planner

**Files:**
- Create: `knowledge/company-source-queries.yaml`
- Create: `src/job_hunting/tools/company_query_planner.py`
- Test: `tests/test_company_query_planner.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_company_query_planner.py`:

```python
from pathlib import Path

from job_hunting.tools.company_query_planner import CompanyQueryPlanner


def test_query_planner_expands_enabled_ats_and_web_templates(tmp_path):
    config = tmp_path / "company-source-queries.yaml"
    config.write_text(
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
      - jobs.lever.co
  web_search:
    enabled: true
    templates:
      - "{role} remote {industry} careers"
      - "site:{domain} \\"{role}\\" \\"{industry}\\""
""",
        encoding="utf-8",
    )

    planner = CompanyQueryPlanner(config_path=config)

    queries = planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Senior Product Manager"],
        industries=["FinTech"],
    )

    assert "Product Manager remote FinTech careers" in queries
    assert 'site:jobs.ashbyhq.com "Product Manager" "FinTech"' in queries
    assert 'site:jobs.lever.co "Product Manager" "FinTech"' in queries
    assert len(queries) == len(set(queries))


def test_query_planner_ignores_disabled_groups(tmp_path):
    config = tmp_path / "company-source-queries.yaml"
    config.write_text(
        """
source_groups:
  ats_search:
    enabled: false
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: true
    templates:
      - "{seniority} {industry} Europe remote"
""",
        encoding="utf-8",
    )

    planner = CompanyQueryPlanner(config_path=config)

    assert planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Lead Product Manager"],
        industries=["AI"],
    ) == ["Lead Product Manager AI Europe remote"]
```

- [ ] **Step 2: Run the tests to verify failure**

Run:

```bash
uv run pytest tests/test_company_query_planner.py -v
```

Expected: FAIL because `company_query_planner.py` does not exist.

- [ ] **Step 3: Add the query config**

Create `knowledge/company-source-queries.yaml`:

```yaml
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
      - job-boards.greenhouse.io
      - jobs.lever.co
      - jobs.personio.com
      - apply.workable.com
      - bamboohr.com/careers

  web_search:
    enabled: true
    templates:
      - "{role} remote {industry} careers"
      - "{seniority} product manager {industry} Europe remote"
      - "{industry} startups hiring product manager remote"
      - "site:{domain} \"Product Manager\" \"Remote\" \"{industry}\""
```

- [ ] **Step 4: Implement the planner**

Create `src/job_hunting/tools/company_query_planner.py`:

```python
from pathlib import Path
from string import Formatter
from typing import Any

import yaml


class CompanyQueryPlanner:
    def __init__(self, config_path: Path | str = "knowledge/company-source-queries.yaml") -> None:
        self.config_path = Path(config_path)

    def plan_queries(
        self,
        roles: list[str],
        seniorities: list[str],
        industries: list[str],
    ) -> list[str]:
        config = self._load_config()
        groups = config.get("source_groups", {})
        queries: list[str] = []

        ats = groups.get("ats_search", {})
        web = groups.get("web_search", {})
        domains = ats.get("domains", []) if ats.get("enabled") else []

        if web.get("enabled"):
            for template in web.get("templates", []):
                for role in roles:
                    for seniority in seniorities:
                        for industry in industries:
                            if "{domain}" in template:
                                for domain in domains:
                                    queries.append(self._format(template, role, seniority, industry, domain))
                            else:
                                queries.append(self._format(template, role, seniority, industry, ""))

        return list(dict.fromkeys(query for query in queries if query.strip()))

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Company source query config not found: {self.config_path}")
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Company source query config must be a mapping: {self.config_path}")
        return data

    @staticmethod
    def _format(template: str, role: str, seniority: str, industry: str, domain: str) -> str:
        allowed = {
            "role": role,
            "seniority": seniority,
            "industry": industry,
            "domain": domain,
        }
        fields = {field for _, field, _, _ in Formatter().parse(template) if field}
        missing = fields - allowed.keys()
        if missing:
            raise ValueError(f"Unsupported query template fields: {sorted(missing)}")
        return template.format(**allowed)
```

- [ ] **Step 5: Run the tests to verify pass**

Run:

```bash
uv run pytest tests/test_company_query_planner.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -f knowledge/company-source-queries.yaml
git add src/job_hunting/tools/company_query_planner.py tests/test_company_query_planner.py
git commit -m "Add company source query planner" \
  -m "Constraint: company discovery must use bounded managed query templates" \
  -m "Rejected: broad web crawling | public source discovery remains explicit and reviewable" \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Tested: uv run pytest tests/test_company_query_planner.py -v" \
  -m "Not-tested: live search result quality"
```

## Task 4: Add Public Search and Career Page Resolver Tools

**Files:**
- Create: `src/job_hunting/tools/company_public_search.py`
- Create: `src/job_hunting/tools/career_page_resolver.py`
- Modify: `src/job_hunting/tools/__init__.py`
- Test: `tests/test_company_public_search.py`
- Test: `tests/test_career_page_resolver.py`

- [ ] **Step 1: Write failing tests for URL extraction and resolver behavior**

Create `tests/test_company_public_search.py`:

```python
from job_hunting.tools.company_public_search import SearchResult, extract_search_results


def test_extract_search_results_reads_links_from_duckduckgo_html():
    html = """
    <a class="result__a" href="https://jobs.ashbyhq.com/acme">Acme Product Manager</a>
    <a class="result__a" href="https://example.com/about">Ignore About</a>
    """

    assert extract_search_results(html) == [
        SearchResult(title="Acme Product Manager", url="https://jobs.ashbyhq.com/acme"),
        SearchResult(title="Ignore About", url="https://example.com/about"),
    ]
```

Create `tests/test_career_page_resolver.py`:

```python
from job_hunting.tools.career_page_resolver import CareerPageResolver, SearchResult


def test_resolver_accepts_supported_ats_url_as_career_page():
    resolver = CareerPageResolver()

    resolved = resolver.resolve(
        company="Acme",
        results=[SearchResult(title="Acme jobs", url="https://jobs.ashbyhq.com/acme")],
    )

    assert resolved == "https://jobs.ashbyhq.com/acme"


def test_resolver_prefers_career_like_company_url():
    resolver = CareerPageResolver()

    resolved = resolver.resolve(
        company="Acme",
        results=[
            SearchResult(title="Acme homepage", url="https://acme.com"),
            SearchResult(title="Careers at Acme", url="https://acme.com/careers"),
        ],
    )

    assert resolved == "https://acme.com/careers"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_company_public_search.py tests/test_career_page_resolver.py -v
```

Expected: FAIL because both modules are missing.

- [ ] **Step 3: Implement public search parsing**

Create `src/job_hunting/tools/company_public_search.py`:

```python
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_result_link = False
        self._current_href = ""
        self._current_text: list[str] = []
        self.results: list[SearchResult] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "a" and "result__a" in (attr_map.get("class") or ""):
            self._in_result_link = True
            self._current_href = attr_map.get("href") or ""
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_result_link:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_result_link:
            title = unescape(" ".join(self._current_text).strip())
            if title and self._current_href:
                self.results.append(SearchResult(title=title, url=self._current_href))
            self._in_result_link = False
            self._current_href = ""
            self._current_text = []


def extract_search_results(html: str) -> list[SearchResult]:
    parser = _DuckDuckGoParser()
    parser.feed(html)
    return parser.results


class PublicCompanySearch:
    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        encoded = quote_plus(query)
        request = Request(
            f"https://duckduckgo.com/html/?q={encoded}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        return extract_search_results(html)[:max_results]
```

- [ ] **Step 4: Implement career page resolver**

Create `src/job_hunting/tools/career_page_resolver.py`:

```python
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


SUPPORTED_ATS_HOSTS = (
    "jobs.ashbyhq.com",
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.personio.com",
    "apply.workable.com",
)


class CareerPageResolver:
    def resolve(self, company: str, results: list[SearchResult]) -> str:
        for result in results:
            if self._is_supported_ats_url(result.url):
                return result.url

        for result in results:
            lowered = result.url.lower()
            if any(part in lowered for part in ("/careers", "/jobs", "/join-us", "/work-with-us")):
                return result.url

        return ""

    @staticmethod
    def _is_supported_ats_url(url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == supported or host.endswith(f".{supported}") for supported in SUPPORTED_ATS_HOSTS)
```

Update `src/job_hunting/tools/__init__.py` to export `PublicCompanySearch` and `CareerPageResolver`.

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
uv run pytest tests/test_company_public_search.py tests/test_career_page_resolver.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/company_public_search.py src/job_hunting/tools/career_page_resolver.py src/job_hunting/tools/__init__.py tests/test_company_public_search.py tests/test_career_page_resolver.py
git commit -m "Add public company search tools" \
  -m "Constraint: v1 uses free public search surfaces behind a fakeable adapter" \
  -m "Rejected: live network calls in automated tests | tests use parsing and resolver units only" \
  -m "Confidence: medium" \
  -m "Scope-risk: moderate" \
  -m "Tested: uv run pytest tests/test_company_public_search.py tests/test_career_page_resolver.py -v" \
  -m "Not-tested: live search engine availability"
```

## Task 5: Add Telegram Candidate Review Notification

**Files:**
- Modify: `src/job_hunting/tools/telegram_notifier.py`
- Test: `tests/test_telegram_notifier.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_telegram_notifier.py`:

```python
def test_send_company_candidates_message_has_no_inline_keyboard():
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=45))
    mock_bot.send_document = AsyncMock()

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot):
        asyncio.run(
            tool._send_company_candidates_review(
                run_date="2026-05-11",
                candidate_count=12,
                path=Path("data/2026-05-11/company_candidates.csv"),
            )
        )

    _, kwargs = mock_bot.send_message.call_args
    assert kwargs["parse_mode"] == "HTML"
    assert kwargs["reply_markup"] is None
    assert "12 new company candidates found" in kwargs["text"]
    assert "data/2026-05-11/company_candidates.csv" in kwargs["text"]
    mock_bot.send_document.assert_not_called()
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```bash
uv run pytest tests/test_telegram_notifier.py::test_send_company_candidates_message_has_no_inline_keyboard -v
```

Expected: FAIL because `_send_company_candidates_review` does not exist.

- [ ] **Step 3: Implement the notification method**

Add to `TelegramNotifierTool` in `src/job_hunting/tools/telegram_notifier.py`:

```python
    def send_company_candidates_review(self, run_date: str, candidate_count: int, path: Path) -> str:
        asyncio.run(self._send_company_candidates_review(run_date, candidate_count, path))
        return f"Telegram company candidate review notification sent for {run_date}"

    async def _send_company_candidates_review(self, run_date: str, candidate_count: int, path: Path) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        safe_path = escape(str(path))
        text = (
            f"🧭 <b>{candidate_count} new company candidates found</b>\n"
            f"Review <code>{safe_path}</code> and set <code>status=approved</code> "
            "for companies you want discovery to monitor."
        )
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )
```

- [ ] **Step 4: Run notifier tests**

Run:

```bash
uv run pytest tests/test_telegram_notifier.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/tools/telegram_notifier.py tests/test_telegram_notifier.py
git commit -m "Notify when company candidates need review" \
  -m "Constraint: v1 uses informational Telegram notifications without approval buttons" \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Tested: uv run pytest tests/test_telegram_notifier.py -v" \
  -m "Not-tested: live Telegram delivery"
```

## Task 6: Add Company Sourcing Crew and Flow

**Files:**
- Create: `src/job_hunting/crews/company_sourcing/__init__.py`
- Create: `src/job_hunting/crews/company_sourcing/crew.py`
- Create: `src/job_hunting/crews/company_sourcing/config/agents.yaml`
- Create: `src/job_hunting/crews/company_sourcing/config/tasks.yaml`
- Create: `src/job_hunting/flows/company_sourcing_flow.py`
- Modify: `src/job_hunting/flows/__init__.py`
- Modify: `src/job_hunting/main.py`
- Modify: `pyproject.toml`
- Test: `tests/test_company_sourcing_flow.py`

- [ ] **Step 1: Write the failing flow test**

Create `tests/test_company_sourcing_flow.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

from job_hunting.flows.company_sourcing_flow import CompanySourcingFlow


def test_company_sourcing_flow_notifies_when_candidates_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    output.parent.mkdir(parents=True)
    output.write_text(
        "company,career_page,website,source,industry,match_score,match_reason,status,discovered_at\n"
        "Mercury,https://mercury.com/jobs,https://mercury.com,public_search,FinTech,84,Fit,pending_review,2026-05-11T09:00:00Z\n",
        encoding="utf-8",
    )

    notifier = MagicMock()

    with patch("job_hunting.flows.company_sourcing_flow.today", return_value="2026-05-11"), patch(
        "job_hunting.flows.company_sourcing_flow.CompanySourcingCrew"
    ) as crew_cls, patch(
        "job_hunting.flows.company_sourcing_flow.TelegramNotifierTool",
        return_value=notifier,
    ):
        crew_cls.return_value.crew.return_value.kickoff.return_value = None
        result = CompanySourcingFlow().run_company_sourcing_crew()
        CompanySourcingFlow().send_review_notification(result)

    assert result == {"run_date": "2026-05-11", "candidate_count": 1, "path": output}
    notifier.send_company_candidates_review.assert_called_once_with(
        run_date="2026-05-11",
        candidate_count=1,
        path=output,
    )
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```bash
uv run pytest tests/test_company_sourcing_flow.py -v
```

Expected: FAIL because `company_sourcing_flow.py` does not exist.

- [ ] **Step 3: Create CrewAI config files**

Create `src/job_hunting/crews/company_sourcing/config/agents.yaml`:

```yaml
source_planner:
  role: Company Source Planner
  goal: Build a bounded list of public/free company sourcing queries from search criteria, profile, and company-source-queries.yaml.
  backstory: You keep lead sourcing explicit, reviewable, and narrow. You never crawl broadly.

company_researcher:
  role: Company Researcher
  goal: Execute bounded searches, extract company candidates, and skip companies already present in knowledge/companies.csv or data/*/company_candidates.csv before downstream work.
  backstory: You own deduplication for company sourcing and avoid wasting work on already known companies.

fit_analyst:
  role: Company Fit Analyst
  goal: Evaluate whether each company matches the user's industries, values, interests, and product management search direction.
  backstory: You prefer concise, evidence-backed fit reasoning over speculative company claims.

candidate_writer:
  role: Company Candidate Writer
  goal: Write only new pending-review company candidates to data/<date>/company_candidates.csv.
  backstory: You keep generated data separate from curated knowledge files.
```

Create `src/job_hunting/crews/company_sourcing/config/tasks.yaml`:

```yaml
plan_company_sources_task:
  description: >
    Read knowledge/search-criteria.md, profile files, and knowledge/company-source-queries.yaml.
    Produce bounded public/free queries for relevant Product Manager roles and industries.
  expected_output: A JSON list of search queries.
  agent: source_planner

research_companies_task:
  description: >
    Execute the planned queries, extract candidate companies and source URLs, and skip companies
    already present in knowledge/companies.csv or data/*/company_candidates.csv before career
    page resolution or fit scoring.
  expected_output: A JSON list of new company candidates with company, website, source, and source evidence.
  agent: company_researcher

score_company_fit_task:
  description: >
    Evaluate each new company against the user's preferred industries, values, interests, and
    remote Product Manager direction. Keep only companies with clear fit evidence.
  expected_output: A JSON list of candidates with company, website, career_page, industry, match_score, and match_reason.
  agent: fit_analyst

write_company_candidates_task:
  description: >
    Write the final candidates to data/{today}/company_candidates.csv with status pending_review.
  expected_output: The number of newly written company candidates and the output path.
  agent: candidate_writer
```

- [ ] **Step 4: Create the crew class**

Create `src/job_hunting/crews/company_sourcing/__init__.py`:

```python
from job_hunting.crews.company_sourcing.crew import CompanySourcingCrew

__all__ = ["CompanySourcingCrew"]
```

Create `src/job_hunting/crews/company_sourcing/crew.py`:

```python
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileReadTool

from job_hunting.config import get_llm


@CrewBase
class CompanySourcingCrew:
    """Discovers reviewable company leads for future vacancy discovery."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def source_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["source_planner"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def company_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["company_researcher"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def fit_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fit_analyst"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def candidate_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["candidate_writer"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @task
    def plan_company_sources_task(self) -> Task:
        return Task(config=self.tasks_config["plan_company_sources_task"])

    @task
    def research_companies_task(self) -> Task:
        return Task(config=self.tasks_config["research_companies_task"])

    @task
    def score_company_fit_task(self) -> Task:
        return Task(config=self.tasks_config["score_company_fit_task"])

    @task
    def write_company_candidates_task(self) -> Task:
        return Task(config=self.tasks_config["write_company_candidates_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

- [ ] **Step 5: Create the flow and entry point**

Create `src/job_hunting/flows/company_sourcing_flow.py`:

```python
import csv
from pathlib import Path

from crewai.flow.flow import Flow, listen, start

from job_hunting.crews.company_sourcing.crew import CompanySourcingCrew
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import company_candidates_file, today


class CompanySourcingFlow(Flow):
    @start()
    def run_company_sourcing_crew(self) -> dict:
        run_date = today()
        output = company_candidates_file(run_date)
        output.parent.mkdir(parents=True, exist_ok=True)

        CompanySourcingCrew().crew().kickoff(inputs={"today": run_date})

        return {
            "run_date": run_date,
            "candidate_count": self._count_pending_candidates(output),
            "path": output,
        }

    @listen(run_company_sourcing_crew)
    def send_review_notification(self, result: dict) -> None:
        if result["candidate_count"] <= 0:
            print("No new company candidates found today.")
            return

        TelegramNotifierTool().send_company_candidates_review(
            run_date=result["run_date"],
            candidate_count=result["candidate_count"],
            path=result["path"],
        )

    @staticmethod
    def _count_pending_candidates(path: Path) -> int:
        if not path.exists():
            return 0
        with path.open(newline="", encoding="utf-8") as handle:
            return sum(1 for row in csv.DictReader(handle) if row.get("status") == "pending_review")
```

Update `src/job_hunting/main.py`:

```python
def run_company_sourcing() -> None:
    """Cron entry point — discover reviewable company leads and notify Telegram."""
    from job_hunting.flows.company_sourcing_flow import CompanySourcingFlow
    CompanySourcingFlow().kickoff()
```

Update `pyproject.toml`:

```toml
job_hunting_source_companies = "job_hunting.main:run_company_sourcing"
```

- [ ] **Step 6: Run the flow test**

Run:

```bash
uv run pytest tests/test_company_sourcing_flow.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/job_hunting/crews/company_sourcing src/job_hunting/flows/company_sourcing_flow.py src/job_hunting/flows/__init__.py src/job_hunting/main.py pyproject.toml tests/test_company_sourcing_flow.py
git commit -m "Add company sourcing flow skeleton" \
  -m "Constraint: company sourcing is a separate cron entry point from vacancy discovery" \
  -m "Rejected: mutating knowledge/companies.csv | generated leads stay in data/<date>/company_candidates.csv" \
  -m "Confidence: medium" \
  -m "Scope-risk: moderate" \
  -m "Tested: uv run pytest tests/test_company_sourcing_flow.py -v" \
  -m "Not-tested: live CrewAI sourcing run"
```

## Task 7: Wire Deterministic Tools Into Crew Tasks

**Files:**
- Modify: `src/job_hunting/crews/company_sourcing/crew.py`
- Modify: `src/job_hunting/crews/company_sourcing/config/tasks.yaml`
- Test: targeted imports and unit tests from earlier tasks

- [ ] **Step 1: Add tools to agents**

Modify `src/job_hunting/crews/company_sourcing/crew.py` imports:

```python
from job_hunting.tools.career_page_resolver import CareerPageResolver
from job_hunting.tools.company_candidate_store import CompanyCandidateStore
from job_hunting.tools.company_public_search import PublicCompanySearch
from job_hunting.tools.company_query_planner import CompanyQueryPlanner
```

If these classes are plain services rather than `BaseTool` subclasses after implementation, wrap them in CrewAI `BaseTool` classes before attaching them to agents. Keep the underlying service classes separate so unit tests stay deterministic.

- [ ] **Step 2: Update task prompts to require tool-backed outputs**

Modify `src/job_hunting/crews/company_sourcing/config/tasks.yaml` so `research_companies_task` explicitly says:

```yaml
    The Company Researcher must use the deduplication-backed candidate store before asking
    downstream agents to resolve or score a company. Companies already present in
    knowledge/companies.csv or data/*/company_candidates.csv must be skipped.
```

- [ ] **Step 3: Run import and focused tests**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py tests/test_company_query_planner.py tests/test_company_public_search.py tests/test_career_page_resolver.py tests/test_company_sourcing_flow.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/job_hunting/crews/company_sourcing/crew.py src/job_hunting/crews/company_sourcing/config/tasks.yaml
git commit -m "Wire company sourcing crew tools" \
  -m "Constraint: deterministic services stay unit-testable outside CrewAI execution" \
  -m "Confidence: medium" \
  -m "Scope-risk: moderate" \
  -m "Tested: uv run pytest tests/test_company_candidate_store.py tests/test_company_query_planner.py tests/test_company_public_search.py tests/test_career_page_resolver.py tests/test_company_sourcing_flow.py -v" \
  -m "Not-tested: live public search quality"
```

## Task 8: Final Verification

**Files:**
- Verify all changed files

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py tests/test_company_query_planner.py tests/test_company_public_search.py tests/test_career_page_resolver.py tests/test_company_sourcing_flow.py tests/test_telegram_notifier.py tests/test_utils.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS. If uv resolves with Python 3.13 on macOS x86_64 and fails on `onnxruntime==1.26.0`, record the dependency platform blocker and rerun with a supported interpreter if available.

- [ ] **Step 3: Verify entry point import**

Run:

```bash
uv run python -c "from job_hunting.main import run_company_sourcing; print(run_company_sourcing.__name__)"
```

Expected output:

```text
run_company_sourcing
```

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted files.

- [ ] **Step 5: Final commit if verification-only edits were needed**

If verification required small fixes, commit them:

```bash
git add <changed-files>
git commit -m "Stabilize company lead sourcing verification" \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Tested: uv run pytest" \
  -m "Not-tested: live Telegram and live public search execution"
```

## Plan Self-Review

- Spec coverage: covered bounded query config, separate Company Sourcing Flow/Crew, candidate CSV under `data/`, Company Researcher deduplication ownership, skip-known-company behavior, Telegram review notification, no mutation of `knowledge/companies.csv`, and tests using fake/non-live source data.
- Placeholder scan: no placeholder markers, incomplete sections, or open-ended error handling steps.
- Type consistency: `CompanyCandidate`, `CompanyCandidateStore`, `CompanyQueryPlanner`, `PublicCompanySearch`, `CareerPageResolver`, and `TelegramNotifierTool.send_company_candidates_review` names are consistent across tasks.
- Known verification risk: this worktree currently cannot create a uv environment with Python 3.13 on macOS x86_64 because `onnxruntime==1.26.0` has no compatible wheel. Use a supported interpreter or record that dependency blocker if it remains.
