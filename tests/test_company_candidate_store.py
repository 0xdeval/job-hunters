import csv
import importlib
from pathlib import Path

import pytest

import job_hunting.tools as tools_module
from job_hunting.tools.company_candidate_store import (
    CompanyCandidate,
    CompanyCandidateStore,
    FIELDNAMES,
    build_candidate_id,
    normalize_company_key,
)


def _candidate(company: str) -> CompanyCandidate:
    return CompanyCandidate(
        company=company,
        career_page="https://example.com/careers",
        website="https://example.com",
        industry="fintech",
        source="manual",
        match_score=85,
        match_reason="Strong overlap with PM requirements",
        status="pending_review",
        discovered_at="2026-05-11T09:00:00Z",
        description="",
    )


def _assert_header_only_candidate_file(path: Path) -> None:
    assert path.exists()
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows == []


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
    _assert_header_only_candidate_file(
        tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    )


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
    _assert_header_only_candidate_file(
        tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    )


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
    _assert_header_only_candidate_file(
        tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    )


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
            "candidate_id": build_candidate_id("Mercury", "https://example.com/careers"),
            "company": "Mercury",
            "career_page": "https://example.com/careers",
            "website": "https://example.com",
            "description": "",
            "industry": "fintech",
            "source": "manual",
            "match_score": "85",
            "match_reason": "Strong overlap with PM requirements",
            "status": "pending_review",
            "discovered_at": "2026-05-11T09:00:00Z",
            "reviewed_at": "",
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


def test_store_writes_candidate_id_description_and_reviewed_at(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    written = store.write_candidates(
        [
            CompanyCandidate(
                company="Mercury",
                career_page="https://mercury.com/jobs",
                website="https://mercury.com",
                description="Banking platform for startups.",
                source="public_search",
                industry="FinTech",
                match_score=85,
                match_reason="Strong overlap with PM requirements",
                status="pending_review",
                discovered_at="2026-05-13T09:00:00Z",
                reviewed_at="",
            )
        ]
    )
    assert written == 1

    output = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    with output.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["candidate_id"] == "mercury-a39ab75f"
    assert rows[0]["description"] == "Banking platform for startups."
    assert rows[0]["reviewed_at"] == ""


def test_store_lists_new_pending_candidates_by_candidate_id(tmp_path, monkeypatch):
    candidate_file = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "old-id,OldCo,https://old.example/jobs,https://old.example,Old description,FinTech,public_search,75,Old reason,pending_review,2026-05-13T08:00:00Z,\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,SaaS,public_search,90,New reason,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    rows = store.list_pending_candidates(exclude_ids={"old-id"})
    assert rows == [
        {
            "candidate_id": "new-id",
            "company": "NewCo",
            "career_page": "https://new.example/jobs",
            "website": "https://new.example",
            "description": "New description",
            "industry": "SaaS",
            "source": "public_search",
            "match_score": "90",
            "match_reason": "New reason",
            "status": "pending_review",
            "discovered_at": "2026-05-13T09:00:00Z",
            "reviewed_at": "",
        }
    ]


def test_approve_candidate_updates_rich_row_and_appends_lean_file(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        "Company,Career page\nCurated,https://curated.example/jobs\n", encoding="utf-8"
    )
    candidate_file = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,SaaS,public_search,90,New reason,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    row = store.review_candidate(
        candidate_id="new-id",
        status="approved",
        reviewed_at="2026-05-13T10:00:00+00:00",
    )
    appended = store.append_approved_company(row)
    assert appended is True

    with candidate_file.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["status"] == "approved"
    assert rows[0]["reviewed_at"] == "2026-05-13T10:00:00+00:00"

    approved_file = tmp_path / "knowledge" / "approved-company-candidates.csv"
    with approved_file.open("r", newline="", encoding="utf-8") as f:
        approved_rows = list(csv.DictReader(f))
    assert approved_rows == [
        {"Company": "NewCo", "Career page": "https://new.example/jobs"}
    ]


def test_append_approved_company_is_idempotent_against_curated_and_approved(
    tmp_path, monkeypatch
):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        "Company,Career page\nCurated,https://curated.example/jobs\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    store = CompanyCandidateStore(run_date="2026-05-13")

    assert (
        store.append_approved_company(
            {"company": "Curated", "career_page": "https://curated.example/jobs"}
        )
        is False
    )
    assert (
        store.append_approved_company(
            {"company": "NewCo", "career_page": "https://new.example/jobs"}
        )
        is True
    )
    assert (
        store.append_approved_company(
            {"company": "NewCo", "career_page": "https://new.example/jobs"}
        )
        is False
    )

    approved_file = tmp_path / "knowledge" / "approved-company-candidates.csv"
    with approved_file.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"Company": "NewCo", "Career page": "https://new.example/jobs"}]


def test_decline_candidate_updates_only_rich_row(tmp_path, monkeypatch):
    candidate_file = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,SaaS,public_search,90,New reason,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    row = store.review_candidate(
        candidate_id="new-id",
        status="declined",
        reviewed_at="2026-05-13T10:30:00+00:00",
    )
    assert row["status"] == "declined"
    assert row["reviewed_at"] == "2026-05-13T10:30:00+00:00"

    with candidate_file.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["status"] == "declined"
    assert rows[0]["reviewed_at"] == "2026-05-13T10:30:00+00:00"
    assert not (tmp_path / "knowledge" / "approved-company-candidates.csv").exists()


def test_list_pending_candidates_supports_utf8_bom_current_run_file(
    tmp_path, monkeypatch
):
    candidate_file = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,SaaS,public_search,90,New reason,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8-sig",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    rows = store.list_pending_candidates()
    assert [row["candidate_id"] for row in rows] == ["new-id"]


def test_review_candidate_supports_utf8_bom_current_run_file(tmp_path, monkeypatch):
    candidate_file = tmp_path / "data" / "2026-05-13" / "company_candidates.csv"
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,SaaS,public_search,90,New reason,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8-sig",
    )
    monkeypatch.chdir(tmp_path)

    store = CompanyCandidateStore(run_date="2026-05-13")
    row = store.review_candidate(
        candidate_id="new-id",
        status="approved",
        reviewed_at="2026-05-13T11:00:00+00:00",
    )
    assert row["status"] == "approved"
    assert row["reviewed_at"] == "2026-05-13T11:00:00+00:00"
