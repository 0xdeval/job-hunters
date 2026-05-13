import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from job_hunting.utils import (
    all_company_candidate_files,
    approved_company_candidates_file,
    company_candidates_file,
)

FIELDNAMES = [
    "candidate_id",
    "company",
    "career_page",
    "website",
    "description",
    "industry",
    "source",
    "match_score",
    "match_reason",
    "status",
    "discovered_at",
    "reviewed_at",
]
APPROVED_FIELDNAMES = ["Company", "Career page"]

_COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(?:inc|ltd|llc|limited|corp|corporation)\b", re.IGNORECASE
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class CompanyCandidate:
    company: str
    career_page: str
    website: str
    industry: str
    source: str
    match_score: int
    match_reason: str
    status: str
    discovered_at: str
    description: str = ""
    reviewed_at: str = ""
    candidate_id: str = ""


def normalize_company_key(name: str) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace(",", " ").replace(".", " ")
    normalized = _COMPANY_SUFFIX_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def normalize_url_key(url: str) -> str:
    return url.strip().rstrip("/").casefold()


def build_candidate_id(company: str, career_page: str) -> str:
    company_key = normalize_company_key(company)
    url_key = normalize_url_key(career_page)
    digest = hashlib.sha1(f"{company_key}|{url_key}".encode("utf-8")).hexdigest()[:8]

    base_company = re.sub(r"[^a-z0-9]+", "-", company_key).strip("-")
    if not base_company:
        base_company = "company"
    base_company = base_company[:32].strip("-")
    if not base_company:
        base_company = "company"
    return f"{base_company}-{digest}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class CompanyCandidateStore:
    def __init__(self, run_date: str) -> None:
        self.run_date = run_date

    def ensure_output_file(self) -> None:
        output_file = company_candidates_file(self.run_date)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists():
            return

        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

    def evaluate_candidates(
        self, candidates: list[CompanyCandidate]
    ) -> tuple[list[CompanyCandidate], list[dict[str, str]]]:
        existing_keys = self._load_existing_company_keys()
        new_candidates: list[CompanyCandidate] = []
        skipped_candidates: list[dict[str, str]] = []
        batch_keys: set[str] = set()

        for candidate in candidates:
            key = normalize_company_key(candidate.company)
            reason: Literal[
                "missing_company",
                "already_known",
                "duplicate_in_batch",
            ] | None = None
            if not key:
                reason = "missing_company"
            elif key in existing_keys:
                reason = "already_known"
            elif key in batch_keys:
                reason = "duplicate_in_batch"

            if reason is not None:
                skipped_candidates.append(
                    {
                        "company": candidate.company,
                        "reason": reason,
                    }
                )
                continue

            batch_keys.add(key)
            new_candidates.append(candidate)

        return new_candidates, skipped_candidates

    def write_candidates(self, candidates: list[CompanyCandidate]) -> int:
        new_candidates, _ = self.evaluate_candidates(candidates)
        rows_to_write = [self._candidate_to_row(candidate) for candidate in new_candidates]

        if not rows_to_write:
            self.ensure_output_file()
            return 0

        output_file = company_candidates_file(self.run_date)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = output_file.exists()

        with output_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows_to_write)

        return len(rows_to_write)

    def list_pending_candidate_ids(self) -> set[str]:
        return {
            row["candidate_id"]
            for row in self._read_candidate_rows()
            if row.get("status") == "pending_review" and row.get("candidate_id")
        }

    def list_pending_candidates(
        self, exclude_ids: set[str] | None = None
    ) -> list[dict[str, str]]:
        excluded = exclude_ids or set()
        return [
            row
            for row in self._read_candidate_rows()
            if row.get("status") == "pending_review"
            and row.get("candidate_id")
            and row["candidate_id"] not in excluded
        ]

    def review_candidate(
        self,
        candidate_id: str,
        status: Literal["approved", "declined"],
        reviewed_at: str | None = None,
    ) -> dict[str, str]:
        rows = self._read_candidate_rows()
        review_time = reviewed_at or utc_now()
        for row in rows:
            if row.get("candidate_id") == candidate_id:
                row["status"] = status
                row["reviewed_at"] = review_time
                self._write_candidate_rows(rows)
                return row
        raise ValueError(f"candidate not found: {candidate_id}")

    def append_approved_company(self, candidate: dict[str, str]) -> bool:
        company = (candidate.get("company") or "").strip()
        career_page = (candidate.get("career_page") or "").strip()
        if not company or not career_page:
            raise ValueError("company and career_page are required")

        if self._approved_company_exists(company):
            return False

        output = self._approved_companies_file()
        output.parent.mkdir(parents=True, exist_ok=True)
        exists = output.exists()
        with output.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=APPROVED_FIELDNAMES)
            if not exists:
                writer.writeheader()
            writer.writerow({"Company": company, "Career page": career_page})
        return True

    @staticmethod
    def _candidate_to_row(candidate: CompanyCandidate) -> dict[str, str]:
        candidate_id = candidate.candidate_id or build_candidate_id(
            candidate.company, candidate.career_page
        )
        return {
            "candidate_id": candidate_id,
            "company": candidate.company,
            "career_page": candidate.career_page,
            "website": candidate.website,
            "description": candidate.description,
            "industry": candidate.industry,
            "source": candidate.source,
            "match_score": str(candidate.match_score),
            "match_reason": candidate.match_reason,
            "status": candidate.status,
            "discovered_at": candidate.discovered_at,
            "reviewed_at": candidate.reviewed_at,
        }

    def _read_candidate_rows(self) -> list[dict[str, str]]:
        output_file = company_candidates_file(self.run_date)
        if not output_file.exists():
            return []
        with output_file.open("r", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def _write_candidate_rows(self, rows: list[dict[str, str]]) -> None:
        output_file = company_candidates_file(self.run_date)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    def _load_existing_company_keys(self) -> set[str]:
        keys = set()

        knowledge_file = self._knowledge_companies_file()
        keys.update(self._load_company_keys_from_csv(knowledge_file, encoding="utf-8-sig"))
        keys.update(
            self._load_company_keys_from_csv(
                approved_company_candidates_file(), encoding="utf-8-sig"
            )
        )

        for candidate_file in all_company_candidate_files():
            keys.update(self._load_company_keys_from_csv(candidate_file, encoding="utf-8-sig"))

        return keys

    @staticmethod
    def _knowledge_companies_file():
        return Path("knowledge/companies.csv")

    @staticmethod
    def _approved_companies_file() -> Path:
        return approved_company_candidates_file()

    def _approved_company_exists(self, company: str) -> bool:
        key = normalize_company_key(company)
        if not key:
            return False
        knowledge_file = self._knowledge_companies_file()
        if key in self._load_company_keys_from_csv(knowledge_file, encoding="utf-8-sig"):
            return True
        approved_file = self._approved_companies_file()
        if key in self._load_company_keys_from_csv(approved_file, encoding="utf-8-sig"):
            return True
        return False

    @staticmethod
    def _load_company_keys_from_csv(path, encoding: str) -> set[str]:
        if not path.exists():
            return set()

        keys = set()
        with path.open("r", newline="", encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                company_name = (
                    row.get("company") or row.get("Company") or ""
                ).strip()
                key = normalize_company_key(company_name)
                if key:
                    keys.add(key)

        return keys
