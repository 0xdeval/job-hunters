import csv
import re
from dataclasses import dataclass
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

_COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(?:inc|ltd|llc|limited|corp|corporation)\b", re.IGNORECASE
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


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
    normalized = normalized.replace(",", " ").replace(".", " ")
    normalized = _COMPANY_SUFFIX_PATTERN.sub(" ", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


class CompanyCandidateStore:
    def __init__(self, run_date: str) -> None:
        self.run_date = run_date

    def write_candidates(self, candidates: list[CompanyCandidate]) -> int:
        existing_keys = self._load_existing_company_keys()
        rows_to_write: list[dict[str, str]] = []
        batch_keys: set[str] = set()

        for candidate in candidates:
            key = normalize_company_key(candidate.company)
            if not key or key in existing_keys or key in batch_keys:
                continue

            batch_keys.add(key)
            rows_to_write.append(
                {
                    "company": candidate.company,
                    "career_page": candidate.career_page,
                    "website": candidate.website,
                    "source": candidate.source,
                    "industry": candidate.industry,
                    "match_score": str(candidate.match_score),
                    "match_reason": candidate.match_reason,
                    "status": candidate.status,
                    "discovered_at": candidate.discovered_at,
                }
            )

        if not rows_to_write:
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

    def _load_existing_company_keys(self) -> set[str]:
        keys = set()

        knowledge_file = self._knowledge_companies_file()
        keys.update(self._load_company_keys_from_csv(knowledge_file, encoding="utf-8-sig"))

        for candidate_file in all_company_candidate_files():
            keys.update(self._load_company_keys_from_csv(candidate_file, encoding="utf-8-sig"))

        return keys

    @staticmethod
    def _knowledge_companies_file():
        return Path("knowledge/companies.csv")

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
