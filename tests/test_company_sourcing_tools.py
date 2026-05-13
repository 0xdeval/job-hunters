from __future__ import annotations

import csv
import json
from pathlib import Path

from crewai.utilities.agent_utils import convert_tools_to_openai_schema

from job_hunting.crews.company_sourcing.crew import CompanySourcingCrew
from job_hunting.tools.company_public_search import SearchResult
from job_hunting.tools.company_sourcing_tools import (
    CareerPageResolverTool,
    CompanyCandidateDedupTool,
    CompanyCandidateWriterTool,
    CompanyQueryPlannerTool,
    PublicCompanySearchTool,
)


def test_company_query_planner_tool_returns_json_queries(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "company-source-queries.yaml").write_text(
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: true
    templates:
      - "site:{domain} {role} {seniority} {industry}"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    payload = CompanyQueryPlannerTool()._run(
        roles=["Product Manager"],
        seniorities=["Senior"],
        industries=["FinTech"],
    )

    assert json.loads(payload) == [
        "site:jobs.ashbyhq.com Product Manager Senior FinTech"
    ]


def test_public_company_search_tool_delegates_to_service(monkeypatch):
    captured = {}

    def _fake_search(self, query: str, max_results: int):
        captured["query"] = query
        captured["max_results"] = max_results
        return [SearchResult(title="Acme", url="https://acme.com/careers")]

    monkeypatch.setattr(
        "job_hunting.tools.company_public_search.PublicCompanySearch.search", _fake_search
    )

    payload = PublicCompanySearchTool()._run(
        query="acme careers",
        max_results=5,
    )

    assert captured == {"query": "acme careers", "max_results": 5}
    assert json.loads(payload) == [{"title": "Acme", "url": "https://acme.com/careers"}]


def test_career_page_resolver_tool_delegates_to_service(monkeypatch):
    captured = {}

    def _fake_resolve(self, company: str, results):
        captured["company"] = company
        captured["results"] = [(result.title, result.url) for result in results]
        return "https://acme.com/careers"

    monkeypatch.setattr(
        "job_hunting.tools.career_page_resolver.CareerPageResolver.resolve", _fake_resolve
    )

    payload = CareerPageResolverTool()._run(
        company="Acme",
        results=[{"title": "Acme Jobs", "url": "https://acme.com/jobs"}],
    )

    assert payload == "https://acme.com/careers"
    assert captured == {
        "company": "Acme",
        "results": [("Acme Jobs", "https://acme.com/jobs")],
    }


def test_career_page_resolver_tool_schema_uses_closed_search_result_items():
    openai_tools, _ = convert_tools_to_openai_schema([CareerPageResolverTool()])
    parameters = openai_tools[0]["function"]["parameters"]
    result_item_schema = parameters["properties"]["results"]["items"]

    assert parameters["required"] == ["company", "results"]
    assert result_item_schema["additionalProperties"] is False
    assert result_item_schema["required"] == ["title", "url"]
    assert set(result_item_schema["properties"]) == {"title", "url"}


def test_company_candidate_writer_tool_writes_candidates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")

    payload = CompanyCandidateWriterTool()._run(
        run_date="2026-05-11",
        candidates=[
                {
                    "company": "Acme",
                    "career_page": "https://acme.com/careers",
                    "website": "https://acme.com",
                    "description": "Builds workflow software.",
                    "source": "public_search",
                    "industry": "SaaS",
                    "match_score": 90,
                "match_reason": "Strong fit",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
            }
        ],
    )

    decoded = json.loads(payload)
    assert decoded["written_count"] == 1

    output = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    assert decoded["output_path"] == str(output.relative_to(tmp_path))
    with output.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["company"] == "Acme"


def test_company_candidate_writer_accepts_description(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("knowledge").mkdir()
    Path("knowledge/companies.csv").write_text("Company,Career page\n", encoding="utf-8")

    result = CompanyCandidateWriterTool()._run(
        run_date="2026-05-13",
        candidates=[
            {
                "company": "Acme",
                "career_page": "https://acme.example/jobs",
                "website": "https://acme.example",
                "description": "Builds workflow software for finance teams.",
                "source": "public_search",
                "industry": "FinTech",
                "match_score": 91,
                "match_reason": "Strong PM fit",
                "status": "pending_review",
                "discovered_at": "2026-05-13T09:00:00Z",
            }
        ],
    )

    assert json.loads(result)["written_count"] == 1
    rows = list(csv.DictReader(Path("data/2026-05-13/company_candidates.csv").open()))
    assert rows[0]["description"] == "Builds workflow software for finance teams."
    assert rows[0]["candidate_id"]


def test_company_candidate_dedup_tool_returns_new_and_skipped_without_writing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        "Company,Career page\nKnown Co,https://known.example/careers\n",
        encoding="utf-8",
    )

    payload = CompanyCandidateDedupTool()._run(
        run_date="2026-05-11",
        candidates=[
                {
                    "company": "Known Co",
                    "career_page": "https://known.example/careers",
                    "website": "https://known.example",
                    "description": "Known company description.",
                    "source": "public_search",
                    "industry": "SaaS",
                    "match_score": 80,
                "match_reason": "Already known",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
            },
                {
                    "company": "New Co",
                    "career_page": "https://new.example/careers",
                    "website": "https://new.example",
                    "description": "New company description.",
                    "source": "public_search",
                    "industry": "SaaS",
                    "match_score": 91,
                "match_reason": "Strong fit",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
            },
        ],
    )

    decoded = json.loads(payload)
    assert [candidate["company"] for candidate in decoded["new_candidates"]] == ["New Co"]
    assert decoded["skipped_candidates"] == [
        {"company": "Known Co", "reason": "already_known"}
    ]
    assert decoded["validation_errors"] == []
    assert not (tmp_path / "data" / "2026-05-11" / "company_candidates.csv").exists()


def test_company_candidate_writer_tool_returns_validation_errors_without_writing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    payload = CompanyCandidateWriterTool()._run(
        run_date="2026-05-11",
        candidates=[
            {
                "company": "Broken Co",
                "career_page": "https://broken.example/careers",
                "website": "https://broken.example",
                "source": "public_search",
                "industry": "SaaS",
                "match_score": 101,
                "match_reason": "Invalid score",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
            }
        ],
    )

    decoded = json.loads(payload)
    assert decoded["written_count"] == 0
    assert decoded["validation_errors"][0]["index"] == 0
    assert not (tmp_path / "data" / "2026-05-11" / "company_candidates.csv").exists()


def test_company_candidate_writer_tool_creates_header_only_output_for_empty_input(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    payload = CompanyCandidateWriterTool()._run(
        run_date="2026-05-11",
        candidates=[],
    )

    decoded = json.loads(payload)
    assert decoded["written_count"] == 0

    output = tmp_path / "data" / "2026-05-11" / "company_candidates.csv"
    assert output.exists()
    with output.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    assert len(lines) == 1
    assert lines[0] == (
        "candidate_id,company,career_page,website,description,industry,"
        "source,match_score,match_reason,status,discovered_at,reviewed_at"
    )


def test_company_sourcing_crew_agents_include_expected_tools():
    crew = CompanySourcingCrew()

    planner_tools = {type(tool).__name__ for tool in crew.source_planner().tools}
    researcher_tools = {type(tool).__name__ for tool in crew.company_researcher().tools}
    fit_tools = {type(tool).__name__ for tool in crew.fit_analyst().tools}
    writer_tools = {type(tool).__name__ for tool in crew.candidate_writer().tools}

    assert "CompanyQueryPlannerTool" in planner_tools
    assert "FileReadTool" in planner_tools

    assert "FileReadTool" in researcher_tools
    assert "PublicCompanySearchTool" in researcher_tools
    assert "CareerPageResolverTool" in researcher_tools
    assert "CompanyCandidateDedupTool" in researcher_tools
    assert "CompanyCandidateWriterTool" not in researcher_tools

    assert fit_tools == {"FileReadTool"}

    assert "FileReadTool" in writer_tools
    assert "CompanyCandidateWriterTool" in writer_tools
    assert "FileWriterTool" not in writer_tools
