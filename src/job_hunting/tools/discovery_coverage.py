import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, model_validator

from job_hunting.utils import discovery_coverage_file


FIELDNAMES = [
    "company",
    "career_page",
    "status",
    "jobs_found",
    "matched_jobs",
    "notes",
    "scraped_at",
]

CoverageStatus = Literal["not_attempted", "completed", "failed", "skipped"]
RecordableCoverageStatus = Literal["completed", "failed", "skipped"]


class DiscoveryCoverageStore:
    def __init__(self, run_date: str):
        self.run_date = run_date
        self.path = discovery_coverage_file(run_date)

    def initialize_from_companies(
        self, companies_path: Path = Path("knowledge/companies.csv")
    ) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        if companies_path.exists():
            with companies_path.open(newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    company = row.get("Company") or row.get("company") or ""
                    career_page = row.get("Career page") or row.get("career_page") or ""
                    if company.strip() or career_page.strip():
                        rows.append(
                            {
                                "company": company.strip(),
                                "career_page": career_page.strip(),
                                "status": "not_attempted",
                                "jobs_found": "0",
                                "matched_jobs": "0",
                                "notes": "",
                                "scraped_at": "",
                            }
                        )

        self._write_rows(rows)
        return self.path

    def record(
        self,
        company: str,
        career_page: str,
        status: CoverageStatus,
        jobs_found: int,
        matched_jobs: int,
        notes: str = "",
        scraped_at: str = "",
    ) -> Path:
        rows = self._read_rows()
        normalized_company = company.strip().casefold()
        normalized_career_page = career_page.strip().rstrip("/")
        replacement = {
            "company": company.strip(),
            "career_page": career_page.strip(),
            "status": status,
            "jobs_found": str(max(jobs_found, 0)),
            "matched_jobs": str(max(matched_jobs, 0)),
            "notes": notes.strip(),
            "scraped_at": scraped_at.strip() or _utc_now(),
        }

        for index, row in enumerate(rows):
            row_company = row.get("company", "").strip().casefold()
            row_career_page = row.get("career_page", "").strip().rstrip("/")
            if row_company == normalized_company or (
                normalized_career_page and row_career_page == normalized_career_page
            ):
                rows[index] = replacement
                break
        else:
            rows.append(replacement)

        self._write_rows(rows)
        return self.path

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)


class DiscoveryCoverageInput(BaseModel):
    run_date: str = Field(description="Discovery run date in YYYY-MM-DD format.")
    company: str = Field(description="Company name from knowledge/companies.csv.")
    career_page: str = Field(description="Career page URL from knowledge/companies.csv.")
    status: RecordableCoverageStatus = Field(
        description="One of: completed, failed, skipped."
    )
    jobs_found: int = Field(
        default=0,
        description="Total open jobs seen on the company career page before profile filtering.",
    )
    matched_jobs: int = Field(
        default=0,
        description="Jobs that matched the candidate criteria and were processed further.",
    )
    notes: str = Field(default="", description="Short error, skip reason, or summary.")
    scraped_at: str = Field(
        default="",
        description="Optional ISO8601 timestamp. Leave empty to use current UTC time.",
    )

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


class DiscoveryCoverageTool(BaseTool):
    name: str = "Discovery Coverage Reporter"
    description: str = (
        "Record whether a company from knowledge/companies.csv was scraped during "
        "the discovery run. Use once for every company row."
    )
    args_schema: type[BaseModel] = DiscoveryCoverageInput

    def _run(
        self,
        run_date: str,
        company: str,
        career_page: str,
        status: RecordableCoverageStatus,
        jobs_found: int = 0,
        matched_jobs: int = 0,
        notes: str = "",
        scraped_at: str = "",
    ) -> str:
        path = DiscoveryCoverageStore(run_date).record(
            company=company,
            career_page=career_page,
            status=status,
            jobs_found=jobs_found,
            matched_jobs=matched_jobs,
            notes=notes,
            scraped_at=scraped_at,
        )
        return f"Coverage recorded in {path}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
