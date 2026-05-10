import re
from enum import Enum
from typing import TypedDict


class VacancyStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DECLINED = "declined"
    DOCUMENTS_READY = "documents_ready"
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    SKIPPED = "skipped"


class VacancyData(TypedDict):
    id: str
    company: str
    title: str
    url: str
    description: str
    questions: list[str]
    scraped_at: str


class ScoreData(TypedDict):
    vacancy_id: str
    date: str
    company: str
    title: str
    score: int
    reasoning: str
    status: str
    requires_cover_letter: bool


def vacancy_id_from(company: str, title: str) -> str:
    def slugify(text: str) -> str:
        text = text.lower()
        # Replace each individual non-alphanumeric with a dash
        text = re.sub(r"[^a-z0-9]", "-", text)
        # Collapse 3+ consecutive dashes to 2
        text = re.sub(r"-{3,}", "--", text)
        return text.strip("-")

    return f"{slugify(company)}--{slugify(title)}"
