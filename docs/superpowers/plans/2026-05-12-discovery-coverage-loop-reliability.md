# Discovery Coverage Loop Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move discovery company iteration into deterministic Python flow code so each company gets one CrewAI kickoff and one terminal coverage result.

**Architecture:** `DiscoveryFlow` will read `knowledge/companies.csv`, initialize coverage, and invoke `DiscoveryCrew` once per company with `today`, `company`, and `career_page`. The discovery scout prompt will handle one company only, while `DiscoveryCoverageTool` will reject `not_attempted` and reject failed rows that do not explain why they failed.

**Tech Stack:** Python 3.10+, CrewAI Flow/Crew, pytest, pydantic, PyYAML, uv.

---

## File Structure

- Modify `src/job_hunting/flows/discovery_flow.py`: add CSV company loading, per-company kickoff loop, injectable crew factory for tests, and flow-level failure recording.
- Modify `src/job_hunting/tools/discovery_coverage.py`: validate that failed tool reports include useful `notes`.
- Modify `src/job_hunting/crews/discovery/config/tasks.yaml`: rewrite `scrape_vacancies_task` for one provided company per kickoff.
- Modify `tests/test_discovery_coverage.py`: add failed-note validation test.
- Create `tests/test_discovery_flow.py`: cover per-company loop, success preservation, exception failure recording, and missing CSV behavior.
- Modify `tests/test_discovery_crew_config.py`: replace old `max_iter` budget test with prompt-contract tests.

## Verification Notes

Plain `uv run pytest` may fail on macOS x86_64 because `onnxruntime==1.26.0` has no wheel for this platform. When that happens, use the repo-documented workaround:

```bash
uv sync --no-install-package onnxruntime
uv run --no-sync pytest
```

Still run `uv run pytest` at the end and report the platform resolver failure if it remains.

---

### Task 1: Add DiscoveryFlow Per-Company Loop Tests

**Files:**
- Create: `tests/test_discovery_flow.py`
- Modify: `src/job_hunting/flows/discovery_flow.py`

- [ ] **Step 1: Write failing flow tests**

Create `tests/test_discovery_flow.py` with:

```python
import csv
import json
from pathlib import Path
from unittest.mock import MagicMock

from job_hunting.flows.discovery_flow import DiscoveryFlow


def _read_coverage_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_run_discovery_crew_invokes_one_crew_per_company(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.discovery_flow.today", lambda: "2026-05-12")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )

    kickoffs: list[dict[str, str]] = []

    def crew_factory():
        crew = MagicMock()

        def kickoff(inputs):
            kickoffs.append(inputs)

        crew.kickoff.side_effect = kickoff
        return crew

    result = DiscoveryFlow(crew_factory=crew_factory).run_discovery_crew()

    assert result == []
    assert kickoffs == [
        {
            "today": "2026-05-12",
            "company": "Acme",
            "career_page": "https://acme.com/careers",
        },
        {
            "today": "2026-05-12",
            "company": "Beta",
            "career_page": "https://beta.com/jobs",
        },
    ]


def test_successful_company_run_preserves_completed_coverage(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.discovery_flow.today", lambda: "2026-05-12")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nAcme,https://acme.com/careers\n",
        encoding="utf-8",
    )

    def crew_factory():
        crew = MagicMock()

        def kickoff(inputs):
            from job_hunting.tools.discovery_coverage import DiscoveryCoverageStore

            DiscoveryCoverageStore(inputs["today"]).record(
                company=inputs["company"],
                career_page=inputs["career_page"],
                status="completed",
                jobs_found=3,
                matched_jobs=1,
                notes="Scraped successfully",
                scraped_at="2026-05-12T10:00:00Z",
            )

        crew.kickoff.side_effect = kickoff
        return crew

    DiscoveryFlow(crew_factory=crew_factory).run_discovery_crew()

    rows = _read_coverage_rows(Path("data/2026-05-12/discovery_coverage.csv"))
    assert rows[0]["status"] == "completed"
    assert rows[0]["jobs_found"] == "3"
    assert rows[0]["matched_jobs"] == "1"
    assert rows[0]["notes"] == "Scraped successfully"


def test_company_exception_records_failed_reason_and_continues(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.discovery_flow.today", lambda: "2026-05-12")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )

    def crew_factory():
        crew = MagicMock()

        def kickoff(inputs):
            if inputs["company"] == "Acme":
                raise TimeoutError("Selenium timed out")
            from job_hunting.tools.discovery_coverage import DiscoveryCoverageStore

            DiscoveryCoverageStore(inputs["today"]).record(
                company=inputs["company"],
                career_page=inputs["career_page"],
                status="completed",
                jobs_found=0,
                matched_jobs=0,
                notes="No matching roles",
                scraped_at="2026-05-12T10:01:00Z",
            )

        crew.kickoff.side_effect = kickoff
        return crew

    DiscoveryFlow(crew_factory=crew_factory).run_discovery_crew()

    rows = _read_coverage_rows(Path("data/2026-05-12/discovery_coverage.csv"))
    assert rows[0]["company"] == "Acme"
    assert rows[0]["status"] == "failed"
    assert rows[0]["jobs_found"] == "0"
    assert rows[0]["matched_jobs"] == "0"
    assert rows[0]["notes"] == "Crew kickoff failed: TimeoutError: Selenium timed out"
    assert rows[1]["company"] == "Beta"
    assert rows[1]["status"] == "completed"


def test_missing_companies_csv_creates_header_only_coverage(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.discovery_flow.today", lambda: "2026-05-12")
    crew_factory = MagicMock()

    result = DiscoveryFlow(crew_factory=crew_factory).run_discovery_crew()

    assert result == []
    crew_factory.assert_not_called()
    assert Path("data/2026-05-12/discovery_coverage.csv").read_text(
        encoding="utf-8"
    ) == "company,career_page,status,jobs_found,matched_jobs,notes,scraped_at\n"


def test_run_discovery_crew_still_returns_historical_pending_scores(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.discovery_flow.today", lambda: "2026-05-12")
    score_dir = Path("data/2026-05-10/scores")
    score_dir.mkdir(parents=True)
    score = {
        "vacancy_id": "acme--pm",
        "date": "2026-05-10",
        "company": "Acme",
        "title": "Product Manager",
        "score": 90,
        "reasoning": "Strong fit",
        "status": "pending_approval",
        "requires_cover_letter": False,
    }
    (score_dir / "acme--pm.json").write_text(json.dumps(score), encoding="utf-8")

    result = DiscoveryFlow(crew_factory=MagicMock()).run_discovery_crew()

    assert result == [score]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_flow.py -q
```

Expected: FAIL because `DiscoveryFlow` does not accept `crew_factory`, does not call one crew per company, and imports `date.today()` instead of `today()`.

- [ ] **Step 3: Implement the minimal flow changes**

Replace `src/job_hunting/flows/discovery_flow.py` with:

```python
import csv
import json
from pathlib import Path
from typing import Callable, Protocol

from crewai.flow.flow import Flow, listen, start

from job_hunting.config import MIN_SCORE
from job_hunting.crews.discovery.crew import DiscoveryCrew
from job_hunting.tools.discovery_coverage import DiscoveryCoverageStore
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import all_score_files, scores_dir, today, vacancies_dir


class KickoffCrew(Protocol):
    def kickoff(self, inputs: dict[str, str]):
        ...


class DiscoveryFlow(Flow):
    def __init__(self, crew_factory: Callable[[], KickoffCrew] | None = None):
        super().__init__()
        self._crew_factory = crew_factory or self._default_crew_factory

    @start()
    def run_discovery_crew(self) -> list[dict]:
        today_str = today()
        vacancies_dir(today_str).mkdir(parents=True, exist_ok=True)
        scores_dir(today_str).mkdir(parents=True, exist_ok=True)

        store = DiscoveryCoverageStore(today_str)
        store.initialize_from_companies()

        for company in self._read_companies():
            try:
                self._crew_factory().kickoff(
                    inputs={
                        "today": today_str,
                        "company": company["company"],
                        "career_page": company["career_page"],
                    }
                )
            except Exception as exc:
                store.record(
                    company=company["company"],
                    career_page=company["career_page"],
                    status="failed",
                    jobs_found=0,
                    matched_jobs=0,
                    notes=_format_failure_note(exc),
                )

        return self._pending_approval_scores()

    @listen(run_discovery_crew)
    def send_approval_requests(self, qualifying_vacancies: list[dict]) -> None:
        if not qualifying_vacancies:
            print("No qualifying vacancies found today.")
            return

        notifier = TelegramNotifierTool()
        for vacancy in qualifying_vacancies:
            notifier._run(
                message_type="approval",
                company=vacancy["company"],
                title=vacancy["title"],
                url=vacancy.get("url", ""),
                score=vacancy["score"],
                vacancy_id=vacancy["vacancy_id"],
                date=vacancy["date"],
            )
            print(f"Sent approval request for {vacancy['vacancy_id']}")

    @staticmethod
    def _default_crew_factory() -> KickoffCrew:
        return DiscoveryCrew().crew()

    @staticmethod
    def _read_companies(companies_path: Path = Path("knowledge/companies.csv")) -> list[dict[str, str]]:
        if not companies_path.exists():
            return []

        companies: list[dict[str, str]] = []
        with companies_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                company = (row.get("Company") or row.get("company") or "").strip()
                career_page = (
                    row.get("Career page") or row.get("career_page") or ""
                ).strip()
                if company or career_page:
                    companies.append({"company": company, "career_page": career_page})
        return companies

    @staticmethod
    def _pending_approval_scores() -> list[dict]:
        qualifying = []
        for score_file in all_score_files():
            try:
                data = json.loads(score_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("score", 0) >= MIN_SCORE and data.get("status") == "pending_approval":
                qualifying.append(data)
        return qualifying


def _format_failure_note(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return f"Crew kickoff failed: {type(exc).__name__}: {message}"
    return f"Crew kickoff failed: {type(exc).__name__}"
```

- [ ] **Step 4: Run flow tests to verify they pass**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/job_hunting/flows/discovery_flow.py tests/test_discovery_flow.py
git commit -m "Route discovery per company from Python" -m "DiscoveryFlow now owns company iteration, invokes one crew kickoff per company, records flow-level failures with actionable notes, and keeps pending-score notification scanning intact." -m "Constraint: Coverage reliability must not depend on a single LLM task looping through every company.
Rejected: Raising vacancy_scout max_iter | it keeps the unreliable procedural loop inside the agent.
Confidence: high
Scope-risk: moderate
Directive: Keep company iteration in DiscoveryFlow unless explicit concurrency or scheduler design replaces it.
Tested: uv run --no-sync pytest tests/test_discovery_flow.py -q
Not-tested: Full suite deferred until prompt and validation updates land.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 2: Enforce Failed Coverage Notes

**Files:**
- Modify: `tests/test_discovery_coverage.py`
- Modify: `src/job_hunting/tools/discovery_coverage.py`

- [ ] **Step 1: Write failing validation tests**

Append these tests to `tests/test_discovery_coverage.py`:

```python
def test_tool_input_rejects_failed_without_actionable_notes():
    with pytest.raises(ValidationError):
        DiscoveryCoverageInput(
            run_date="2026-05-12",
            company="Acme",
            career_page="https://acme.com/careers",
            status="failed",
            notes="",
        )

    with pytest.raises(ValidationError):
        DiscoveryCoverageInput(
            run_date="2026-05-12",
            company="Acme",
            career_page="https://acme.com/careers",
            status="failed",
            notes="error",
        )


def test_tool_input_accepts_failed_with_specific_reason():
    model = DiscoveryCoverageInput(
        run_date="2026-05-12",
        company="Acme",
        career_page="https://acme.com/careers",
        status="failed",
        notes="Selenium timeout after opening career page",
    )

    assert model.notes == "Selenium timeout after opening career page"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_coverage.py::test_tool_input_rejects_failed_without_actionable_notes tests/test_discovery_coverage.py::test_tool_input_accepts_failed_with_specific_reason -q
```

Expected: FAIL because `DiscoveryCoverageInput` currently accepts `status="failed"` with empty or generic notes.

- [ ] **Step 3: Implement pydantic validation**

In `src/job_hunting/tools/discovery_coverage.py`, update the pydantic imports:

```python
from pydantic import BaseModel, Field, model_validator
```

Add this method inside `DiscoveryCoverageInput`:

```python
    @model_validator(mode="after")
    def failed_status_requires_actionable_notes(self):
        if self.status != "failed":
            return self

        normalized_notes = self.notes.strip()
        generic_notes = {"failed", "failure", "error", "unknown", "n/a", "na"}
        if len(normalized_notes) < 10 or normalized_notes.casefold() in generic_notes:
            raise ValueError("failed coverage rows require a specific reason in notes")
        self.notes = normalized_notes
        return self
```

- [ ] **Step 4: Run coverage tests**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_coverage.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/job_hunting/tools/discovery_coverage.py tests/test_discovery_coverage.py
git commit -m "Require reasons for failed discovery coverage" -m "DiscoveryCoverageInput now rejects failed status reports that do not include a specific notes value, keeping generated coverage CSVs useful for review." -m "Constraint: Users need to understand why failed companies failed from the CSV.
Rejected: Accepting generic failed/error notes | they do not explain the operational cause.
Confidence: high
Scope-risk: narrow
Directive: Keep failed coverage rows actionable without requiring log inspection.
Tested: uv run --no-sync pytest tests/test_discovery_coverage.py -q
Not-tested: Full suite deferred until prompt contract update lands.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 3: Rewrite Scout Prompt For One Company

**Files:**
- Modify: `tests/test_discovery_crew_config.py`
- Modify: `src/job_hunting/crews/discovery/config/tasks.yaml`
- Modify: `src/job_hunting/crews/discovery/config/agents.yaml`

- [ ] **Step 1: Replace the old prompt-budget test**

Replace `tests/test_discovery_crew_config.py` with:

```python
from pathlib import Path

import yaml


def _scrape_task_description() -> str:
    config_path = Path("src/job_hunting/crews/discovery/config/tasks.yaml")
    tasks_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return tasks_config["scrape_vacancies_task"]["description"]


def test_scrape_task_handles_one_provided_company():
    description = _scrape_task_description()

    assert "{company}" in description
    assert "{career_page}" in description
    assert "one company" in description.lower()


def test_scrape_task_does_not_read_or_loop_through_company_csv():
    description = _scrape_task_description().lower()

    assert "read knowledge/companies.csv" not in description
    assert "for each company" not in description
    assert "every company from knowledge/companies.csv" not in description
    assert "run window" not in description
    assert "batch" not in description
    assert "not_attempted" not in description
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_crew_config.py -q
```

Expected: FAIL because the current prompt reads and loops through `knowledge/companies.csv`.

- [ ] **Step 3: Rewrite `scrape_vacancies_task`**

In `src/job_hunting/crews/discovery/config/tasks.yaml`, replace only `scrape_vacancies_task.description` with:

```yaml
    Today's date is {today}. You are discovering new job vacancies for one company only.

    Company: {company}
    Career page: {career_page}

    1. Use the "Read a file's content" tool to read knowledge/profile.yaml. Use this to understand the roles, seniority, and keywords the candidate is interested in.
    2. Use the "Scrape website with Selenium" tool to scrape the provided Career page URL for this company.
       Identify all open job positions (title and URL) available from this career page.
       If the provided career page cannot be evaluated as a career page for this company, use "Discovery Coverage Reporter" with:
       - run_date: {today}
       - company: {company}
       - career_page: {career_page}
       - status: "skipped"
       - jobs_found: 0
       - matched_jobs: 0
       - notes: a specific reason the page cannot be evaluated
       Then return [].
       If scraping or page evaluation fails because of a tool error, timeout, HTTP error, or unexpected page failure, use "Discovery Coverage Reporter" with:
       - run_date: {today}
       - company: {company}
       - career_page: {career_page}
       - status: "failed"
       - jobs_found: 0
       - matched_jobs: 0
       - notes: the specific failure reason
       Then return [].
    3. **FILTERING STEP**: Look at the list of job titles found. Only proceed with roles that are a potential match for the candidate based on the profile search preferences. Ignore completely irrelevant roles (e.g. if the candidate is an engineer, ignore HR, Legal, or unrelated Sales roles).
    4. For each vacancy that passed the filter:
       a. Use "Vacancy Dedup Checker" with the vacancy URL. If result is "duplicate", skip entirely.
       b. Use the "Scrape website with Selenium" tool to open the job-specific URL. Read the page content.
          If the page shows the job is closed, filled, or returns an error, skip entirely.
       c. Extract: full job description, required skills, any explicit application questions
          (e.g. "Why do you want to work here?"), and whether a cover letter is requested.
       d. Generate a vacancy ID as: lowercase company name and title, spaces and
          special chars replaced with hyphens, double-hyphen between company and title.
          Example: "Acme Corp" + "Senior PM" -> "acme-corp--senior-pm"
       e. Use the "Write to a file" tool to save a JSON file to data/{today}/vacancies/<vacancy_id>.json
          with this exact schema:
          {{
            "id": "<vacancy_id>",
            "company": "{company}",
            "title": "<job_title>",
            "url": "<job_url>",
            "description": "<full_job_description>",
            "questions": ["<question1>", "<question2>"],
            "scraped_at": "<ISO8601 timestamp>"
          }}
          Ensure the directory data/{today}/vacancies/ exists before writing.
          If there are no application questions, use an empty list [].
    5. After this company has been handled, use "Discovery Coverage Reporter" with:
       - run_date: {today}
       - company: {company}
       - career_page: {career_page}
       - status: "completed"
       - jobs_found: total open roles seen before profile filtering
       - matched_jobs: roles that passed the filtering step
       - notes: a short summary such as "Scraped successfully" or "No matching roles"
    6. Return a JSON list of vacancy IDs that were successfully saved for this company.
```

In `src/job_hunting/crews/discovery/config/agents.yaml`, reduce `vacancy_scout.max_iter` to a per-company budget:

```yaml
  max_iter: 30
```

- [ ] **Step 4: Run prompt tests**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_crew_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/job_hunting/crews/discovery/config/tasks.yaml src/job_hunting/crews/discovery/config/agents.yaml tests/test_discovery_crew_config.py
git commit -m "Limit discovery scout prompt to one company" -m "The discovery scout task now receives one company and career page per kickoff, reports company-specific coverage, and no longer instructs the agent to read or loop through knowledge/companies.csv." -m "Constraint: Company iteration belongs to DiscoveryFlow, not the LLM scout task.
Rejected: Keeping full-list prompt with higher max_iter | it still allows partial LLM-owned coverage.
Confidence: high
Scope-risk: narrow
Directive: Keep scout prompts scoped to one provided company unless the flow contract changes.
Tested: uv run --no-sync pytest tests/test_discovery_crew_config.py -q
Not-tested: Full suite deferred until final integration task.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 4: Integration Verification And Cleanup

**Files:**
- Review: `src/job_hunting/flows/discovery_flow.py`
- Review: `src/job_hunting/tools/discovery_coverage.py`
- Review: `src/job_hunting/crews/discovery/config/tasks.yaml`
- Review: `tests/test_discovery_flow.py`
- Review: `tests/test_discovery_coverage.py`
- Review: `tests/test_discovery_crew_config.py`

- [ ] **Step 1: Run targeted integration tests**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_flow.py tests/test_discovery_coverage.py tests/test_discovery_crew_config.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the full prepared-environment suite**

Run:

```bash
uv run --no-sync pytest
```

Expected: PASS.

- [ ] **Step 3: Run the requested full command**

Run:

```bash
uv run pytest
```

Expected on platforms with compatible `onnxruntime`: PASS. Expected on this macOS x86_64 environment if the resolver issue persists: FAIL before tests start with an `onnxruntime==1.26.0` wheel compatibility message. Record the exact result in the final report.

- [ ] **Step 4: Inspect final diff**

Run:

```bash
git diff --check
git status --short
git diff -- src/job_hunting/flows/discovery_flow.py src/job_hunting/tools/discovery_coverage.py src/job_hunting/crews/discovery/config/tasks.yaml src/job_hunting/crews/discovery/config/agents.yaml tests/test_discovery_flow.py tests/test_discovery_coverage.py tests/test_discovery_crew_config.py
```

Expected: `git diff --check` prints no output. `git status --short` shows only the intended modified files before the final commit.

- [ ] **Step 5: Commit final verification metadata if cleanup changed files**

If Step 4 leads to cleanup edits, commit them:

```bash
git add src/job_hunting/flows/discovery_flow.py src/job_hunting/tools/discovery_coverage.py src/job_hunting/crews/discovery/config/tasks.yaml src/job_hunting/crews/discovery/config/agents.yaml tests/test_discovery_flow.py tests/test_discovery_coverage.py tests/test_discovery_crew_config.py
git commit -m "Verify deterministic discovery coverage flow" -m "Final cleanup keeps the per-company discovery flow, coverage validation, and prompt contract aligned after targeted and full-suite verification." -m "Constraint: Acceptance requires discovery coverage to be deterministic and test-backed.
Rejected: Leaving verification-only changes uncommitted | later work would not know which checks backed the final state.
Confidence: high
Scope-risk: narrow
Directive: Preserve targeted tests for flow orchestration, failed notes, and prompt scope.
Tested: uv run --no-sync pytest tests/test_discovery_flow.py tests/test_discovery_coverage.py tests/test_discovery_crew_config.py -q
Tested: uv run --no-sync pytest
Not-tested: uv run pytest may be blocked by macOS x86_64 onnxruntime wheel resolution.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

