import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from job_hunting.tools.discovery_coverage import (
    DiscoveryCoverageInput,
    DiscoveryCoverageStore,
    DiscoveryCoverageTool,
)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_initialize_creates_one_not_attempted_row_per_company(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    path = DiscoveryCoverageStore("2026-05-12").initialize_from_companies()

    assert path == Path("data/2026-05-12/discovery_coverage.csv")
    assert _read_rows(path) == [
        {
            "company": "Acme",
            "career_page": "https://acme.com/careers",
            "status": "not_attempted",
            "jobs_found": "0",
            "matched_jobs": "0",
            "notes": "",
            "scraped_at": "",
        },
        {
            "company": "Beta",
            "career_page": "https://beta.com/jobs",
            "status": "not_attempted",
            "jobs_found": "0",
            "matched_jobs": "0",
            "notes": "",
            "scraped_at": "",
        },
    ]


def test_initialize_accepts_company_csv_with_utf8_bom(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "\ufeffCompany,Career page\nAcme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    path = DiscoveryCoverageStore("2026-05-12").initialize_from_companies()

    assert _read_rows(path)[0]["company"] == "Acme"


def test_record_updates_existing_company_row(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nAcme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    store = DiscoveryCoverageStore("2026-05-12")
    store.initialize_from_companies()

    store.record(
        company="Acme",
        career_page="https://acme.com/careers",
        status="completed",
        jobs_found=5,
        matched_jobs=2,
        notes="Found product roles",
        scraped_at="2026-05-12T10:00:00Z",
    )

    rows = _read_rows(Path("data/2026-05-12/discovery_coverage.csv"))
    assert rows[0] == {
        "company": "Acme",
        "career_page": "https://acme.com/careers",
        "status": "completed",
        "jobs_found": "5",
        "matched_jobs": "2",
        "notes": "Found product roles",
        "scraped_at": "2026-05-12T10:00:00Z",
    }


def test_tool_records_coverage_and_returns_report_path(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nAcme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    DiscoveryCoverageStore("2026-05-12").initialize_from_companies()

    result = DiscoveryCoverageTool()._run(
        run_date="2026-05-12",
        company="Acme",
        career_page="https://acme.com/careers",
        status="failed",
        jobs_found=0,
        matched_jobs=0,
        notes="Timeout",
        scraped_at="2026-05-12T10:01:00Z",
    )

    assert result == "Coverage recorded in data/2026-05-12/discovery_coverage.csv"
    assert _read_rows(Path("data/2026-05-12/discovery_coverage.csv"))[0]["status"] == "failed"


def test_tool_input_rejects_not_attempted_status():
    with pytest.raises(ValidationError):
        DiscoveryCoverageInput(
            run_date="2026-05-12",
            company="Acme",
            career_page="https://acme.com/careers",
            status="not_attempted",
        )


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
