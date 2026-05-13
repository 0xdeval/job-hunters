from __future__ import annotations

import json
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError

from job_hunting.tools.career_page_resolver import CareerPageResolver
from job_hunting.tools.company_candidate_store import CompanyCandidate, CompanyCandidateStore
from job_hunting.tools.company_public_search import PublicCompanySearch
from job_hunting.tools.company_query_planner import CompanyQueryPlanner
from job_hunting.tools.search_result import SearchResult
from job_hunting.utils import company_candidates_file


class CompanyQueryPlannerToolInput(BaseModel):
    roles: list[str] = Field(description="Target roles to include in query planning.")
    seniorities: list[str] = Field(
        description="Target seniority levels to include in query planning."
    )
    industries: list[str] = Field(
        description="Target industries to include in query planning."
    )


class CompanyQueryPlannerTool(BaseTool):
    name: str = "Company Query Planner"
    description: str = (
        "Generate deterministic company sourcing queries from role/seniority/industry inputs."
    )
    args_schema: type[BaseModel] = CompanyQueryPlannerToolInput

    def _run(self, roles: list[str], seniorities: list[str], industries: list[str]) -> str:
        planner = CompanyQueryPlanner()
        queries = planner.plan_queries(
            roles=roles,
            seniorities=seniorities,
            industries=industries,
        )
        return json.dumps(queries)


class PublicCompanySearchToolInput(BaseModel):
    query: str = Field(description="Web query used to discover company career pages.")
    max_results: int = Field(default=10, description="Maximum number of results to return.")


class PublicCompanySearchTool(BaseTool):
    name: str = "Public Company Search"
    description: str = (
        "Run deterministic public web search and return normalized title/url results."
    )
    args_schema: type[BaseModel] = PublicCompanySearchToolInput

    def _run(self, query: str, max_results: int = 10) -> str:
        results = PublicCompanySearch().search(query=query, max_results=max_results)
        payload = [{"title": result.title, "url": result.url} for result in results]
        return json.dumps(payload)


class SearchResultPayload(BaseModel):
    title: str = Field(description="Search result title.")
    url: str = Field(description="Search result URL.")


class CareerPageResolverToolInput(BaseModel):
    company: str = Field(description="Company name to resolve an official career page for.")
    results: list[SearchResultPayload] = Field(
        description="Search results list with title and url keys."
    )


class CareerPageResolverTool(BaseTool):
    name: str = "Career Page Resolver"
    description: str = (
        "Resolve the best-matching career page URL for a company from search results."
    )
    args_schema: type[BaseModel] = CareerPageResolverToolInput

    def _run(
        self,
        company: str,
        results: list[SearchResultPayload | dict[str, str]],
    ) -> str:
        parsed_results = []
        for item in results:
            payload = (
                item
                if isinstance(item, SearchResultPayload)
                else SearchResultPayload.model_validate(item)
            )
            parsed_results.append(SearchResult(title=payload.title, url=payload.url))

        return CareerPageResolver().resolve(company=company, results=parsed_results)


class CompanyCandidateToolPayload(BaseModel):
    company: str = Field(description="Company name.")
    career_page: str = Field(description="Resolved company career page URL.")
    website: str = Field(description="Company website URL.")
    description: str = Field(
        description="Short neutral company description for Telegram review."
    )
    source: str = Field(description="Discovery source for the candidate.")
    industry: str = Field(description="Company industry or segment.")
    match_score: int = Field(
        ge=0,
        le=100,
        description="Profile fit score from 0 to 100.",
    )
    match_reason: str = Field(description="Short reason this company fits the profile.")
    status: str = Field(description="Candidate review status.")
    discovered_at: str = Field(description="Discovery timestamp.")


def _parse_candidates(
    candidates: list[CompanyCandidateToolPayload | dict[str, Any]],
) -> tuple[list[CompanyCandidate], list[dict[str, Any]]]:
    parsed_candidates: list[CompanyCandidate] = []
    errors: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        try:
            if isinstance(candidate, CompanyCandidateToolPayload):
                payload = candidate
            else:
                payload = CompanyCandidateToolPayload.model_validate(candidate)
        except ValidationError as exc:
            errors.append({"index": index, "errors": exc.errors()})
            continue

        parsed_candidates.append(CompanyCandidate(**payload.model_dump()))

    return parsed_candidates, errors


class CompanyCandidateDedupToolInput(BaseModel):
    run_date: str = Field(description="Run date (YYYY-MM-DD) for dedupe context.")
    candidates: list[CompanyCandidateToolPayload] = Field(
        description="Candidate objects to validate against known companies and prior candidates."
    )


class CompanyCandidateDedupTool(BaseTool):
    name: str = "Company Candidate Dedup"
    description: str = (
        "Validate candidate rows and return which companies are new without writing files."
    )
    args_schema: type[BaseModel] = CompanyCandidateDedupToolInput

    def _run(
        self,
        run_date: str,
        candidates: list[CompanyCandidateToolPayload | dict[str, Any]],
    ) -> str:
        parsed_candidates, validation_errors = _parse_candidates(candidates)
        store = CompanyCandidateStore(run_date=run_date)
        new_candidates, skipped_candidates = store.evaluate_candidates(parsed_candidates)

        return json.dumps(
            {
                "new_candidates": [
                    {
                        "company": candidate.company,
                        "career_page": candidate.career_page,
                        "website": candidate.website,
                        "description": candidate.description,
                        "source": candidate.source,
                        "industry": candidate.industry,
                        "match_score": candidate.match_score,
                        "match_reason": candidate.match_reason,
                        "status": candidate.status,
                        "discovered_at": candidate.discovered_at,
                    }
                    for candidate in new_candidates
                ],
                "skipped_candidates": skipped_candidates,
                "validation_errors": validation_errors,
            }
        )


class CompanyCandidateWriterToolInput(BaseModel):
    run_date: str = Field(description="Run date (YYYY-MM-DD) to write candidate output into.")
    candidates: list[CompanyCandidateToolPayload] = Field(
        description=(
            "List of company candidate objects with fields: company, career_page, website, "
            "description, source, industry, match_score, match_reason, status, discovered_at."
        )
    )


class CompanyCandidateWriterTool(BaseTool):
    name: str = "Company Candidate Writer"
    description: str = (
        "Validate and write deduplicated company candidates to the run CSV, creating header-only files for valid empty runs."
    )
    args_schema: type[BaseModel] = CompanyCandidateWriterToolInput

    def _run(
        self,
        run_date: str,
        candidates: list[CompanyCandidateToolPayload | dict[str, Any]],
    ) -> str:
        parsed_candidates, validation_errors = _parse_candidates(candidates)
        if validation_errors:
            return json.dumps(
                {
                    "written_count": 0,
                    "output_path": str(company_candidates_file(run_date)),
                    "validation_errors": validation_errors,
                }
            )

        store = CompanyCandidateStore(run_date=run_date)

        if parsed_candidates:
            written_count = store.write_candidates(parsed_candidates)
        else:
            store.ensure_output_file()
            written_count = 0

        return json.dumps(
            {
                "written_count": written_count,
                "output_path": str(company_candidates_file(run_date)),
                "validation_errors": [],
            }
        )
