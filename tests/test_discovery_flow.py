import csv
import json
from pathlib import Path

from job_hunting.flows import discovery_flow as discovery_flow_module
from job_hunting.tools.discovery_coverage import DiscoveryCoverageStore

DiscoveryFlow = discovery_flow_module.DiscoveryFlow


def _read_coverage_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_run_discovery_crew_invokes_one_crew_per_company(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-12")
    kickoff_inputs: list[dict[str, str]] = []

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            kickoff_inputs.append(inputs)

    flow = DiscoveryFlow(crew_factory=lambda: _Crew())

    result = flow.run_discovery_crew()

    assert result == []
    assert kickoff_inputs == [
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


def test_successful_company_run_preserves_completed_coverage(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-12")

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            DiscoveryCoverageStore(inputs["today"]).record(
                company=inputs["company"],
                career_page=inputs["career_page"],
                status="completed",
                jobs_found=3,
                matched_jobs=1,
                notes="Found one strong match",
            )

    flow = DiscoveryFlow(crew_factory=lambda: _Crew())
    flow.run_discovery_crew()

    rows = _read_coverage_rows(Path("data/2026-05-12/discovery_coverage.csv"))
    assert rows[0]["status"] == "completed"
    assert rows[0]["jobs_found"] == "3"
    assert rows[0]["matched_jobs"] == "1"
    assert rows[0]["notes"] == "Found one strong match"


def test_company_exception_records_failed_reason_and_continues(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-12")
    called = {"count": 0}

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            called["count"] += 1
            if called["count"] == 1:
                raise TimeoutError("Selenium timed out")
            DiscoveryCoverageStore(inputs["today"]).record(
                company=inputs["company"],
                career_page=inputs["career_page"],
                status="completed",
                jobs_found=2,
                matched_jobs=1,
                notes="Second company done",
            )

    flow = DiscoveryFlow(crew_factory=lambda: _Crew())
    flow.run_discovery_crew()

    rows = _read_coverage_rows(Path("data/2026-05-12/discovery_coverage.csv"))
    assert rows[0]["status"] == "failed"
    assert rows[0]["notes"] == "Crew kickoff failed: TimeoutError: Selenium timed out"
    assert rows[1]["status"] == "completed"


def test_missing_companies_csv_creates_header_only_coverage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-12")
    called = {"value": False}

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            called["value"] = True

    flow = DiscoveryFlow(crew_factory=lambda: _Crew())

    result = flow.run_discovery_crew()

    assert result == []
    assert called["value"] is False
    coverage_path = Path("data/2026-05-12/discovery_coverage.csv")
    assert coverage_path.exists()
    assert coverage_path.read_text(encoding="utf-8").strip() == (
        "company,career_page,status,jobs_found,matched_jobs,notes,scraped_at"
    )


def test_run_discovery_crew_still_returns_historical_pending_scores(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-12")
    historical_score = {
        "company": "Acme",
        "title": "Staff Engineer",
        "url": "https://acme.com/jobs/123",
        "score": 90,
        "status": "pending_approval",
        "vacancy_id": "acme-123",
        "date": "2026-05-11",
    }
    score_path = Path("data/2026-05-11/scores")
    score_path.mkdir(parents=True, exist_ok=True)
    (score_path / "acme-123.json").write_text(json.dumps(historical_score), encoding="utf-8")

    flow = DiscoveryFlow(crew_factory=lambda: None)

    result = flow.run_discovery_crew()

    assert result == [historical_score]
