import csv
import importlib
from pathlib import Path

import pytest

import job_hunting.tools as tools_module
from job_hunting.tools.company_candidate_store import (
    CompanyCandidate,
    CompanyCandidateStore,
    FIELDNAMES,
    normalize_company_key,
)


def _candidate(company: str) -> CompanyCandidate:
    return CompanyCandidate(
        company=company,
        career_page="https://example.com/careers",
        website="https://example.com",
        source="manual",
        industry="fintech",
        match_score=85,
        match_reason="Strong overlap with PM requirements",
        status="pending_review",
        discovered_at="2026-05-11T09:00:00Z",
    )


def test_normalize_company_key_removes_case_and_suffix_noise():
    assert normalize_company_key("Ramp, Inc.") == "ramp"
    assert normalize_company_key("  ACME Labs Ltd  ") == "acme labs"


def test_store_skips_companies_already_in_knowledge_csv(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        "Company,Career page\nRamp,https://ramp.com/careers\n", encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    written = store.write_candidates([_candidate("Ramp")])

    assert written == 0
    assert not (tmp_path / "data" / "2026-05-11" / "company_candidates.csv").exists()


def test_store_skips_companies_already_in_historical_candidates(tmp_path, monkeypatch):
    historical = tmp_path / "data" / "2026-05-10" / "company_candidates.csv"
    historical.parent.mkdir(parents=True)
    with historical.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(
            {
                "company": "Ramp",
                "career_page": "https://ramp.com/careers",
                "website": "https://ramp.com",
                "source": "historical",
                "industry": "fintech",
                "match_score": "90",
                "match_reason": "Existing",
                "status": "pending_review",
                "discovered_at": "2026-05-10T08:00:00Z",
            }
        )

    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    written = store.write_candidates([_candidate("Ramp")])

    assert written == 0
    assert not (tmp_path / "data" / "2026-05-11" / "company_candidates.csv").exists()


def test_store_skips_companies_already_in_historical_candidates_with_utf8_bom(
    tmp_path, monkeypatch
):
    historical = tmp_path / "data" / "2026-05-10" / "company_candidates.csv"
    historical.parent.mkdir(parents=True)
    with historical.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(
            {
                "company": "Ramp",
                "career_page": "https://ramp.com/careers",
                "website": "https://ramp.com",
                "source": "historical",
                "industry": "fintech",
                "match_score": "90",
                "match_reason": "Existing",
                "status": "pending_review",
                "discovered_at": "2026-05-10T08:00:00Z",
            }
        )

    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    written = store.write_candidates([_candidate("Ramp")])

    assert written == 0
    assert not (tmp_path / "data" / "2026-05-11" / "company_candidates.csv").exists()


def test_store_writes_new_pending_review_candidates(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    written = store.write_candidates([_candidate("Mercury")])

    assert written == 1

    output = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    assert output.exists()

    with output.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            "company": "Mercury",
            "career_page": "https://example.com/careers",
            "website": "https://example.com",
            "source": "manual",
            "industry": "fintech",
            "match_score": "85",
            "match_reason": "Strong overlap with PM requirements",
            "status": "pending_review",
            "discovered_at": "2026-05-11T09:00:00Z",
        }
    ]


def test_store_deduplicates_within_same_input_batch(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-11")
    written = store.write_candidates([_candidate("Ramp, Inc."), _candidate("ramp")])

    assert written == 1

    output = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    with output.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["company"] == "Ramp, Inc."


def test_tools_module_lazy_export_matches_direct_import():
    module = importlib.reload(tools_module)

    from job_hunting.tools import CompanyCandidateStore as lazy_exported

    assert lazy_exported is CompanyCandidateStore
    assert lazy_exported is module.CompanyCandidateStore


def test_tools_module_missing_tool_raises_attribute_error():
    module = importlib.reload(tools_module)

    with pytest.raises(AttributeError):
        getattr(module, "MissingTool")
