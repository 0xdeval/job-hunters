import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from crewai import Agent, Crew, Process, Task
from crewai.flow.flow import Flow, start

from job_hunting.config import get_llm
from job_hunting.flows.application_flow import ApplicationFlow
from job_hunting.tools import SafeSeleniumScrapingTool
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import all_vacancy_files, scores_dir, today, vacancies_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedVacancy:
    company: str
    title: str
    description: str
    questions: list[str]
    requires_cover_letter: bool


class Notifier(Protocol):
    def send_text(self, text: str, chat_id: int | str | None = None) -> str: ...

    def _run(self, **kwargs) -> str: ...


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def make_vacancy_id(company: str, title: str) -> str:
    return f"{_slugify(company)}--{_slugify(title)}"


def parse_direct_vacancy_result(raw: object) -> PreparedVacancy:
    if hasattr(raw, "raw"):
        raw = raw.raw
    if not isinstance(raw, str):
        raw = str(raw)

    data = json.loads(raw)
    company = str(data.get("company", "")).strip()
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    questions = data.get("questions") or []

    if not isinstance(questions, list):
        questions = []
    if not company:
        raise ValueError("could not extract company")
    if not title:
        raise ValueError("could not extract title")
    if not description:
        raise ValueError("could not extract description")

    return PreparedVacancy(
        company=company,
        title=title,
        description=description,
        questions=[
            str(question).strip()
            for question in questions
            if str(question).strip()
        ],
        requires_cover_letter=bool(data.get("requires_cover_letter", False)),
    )


def extract_direct_vacancy(url: str) -> PreparedVacancy:
    agent = Agent(
        role="Direct Vacancy Extractor",
        goal="Extract structured application preparation data from one vacancy URL.",
        backstory=(
            "You read one known job posting URL and return only the structured fields "
            "needed by the application generation flow."
        ),
        llm=get_llm(),
        tools=[SafeSeleniumScrapingTool()],
        verbose=True,
        allow_delegation=False,
    )
    task = Task(
        description=(
            "Scrape exactly this vacancy URL, which is already the job posting: {url}\n"
            "Do not search the broader career page and do not discover other jobs.\n"
            "Extract company, title, full job description, explicit application questions, "
            "and whether the job explicitly asks for a cover letter.\n"
            "Return strict JSON with keys: company, title, description, questions, "
            "requires_cover_letter."
        ),
        expected_output=(
            '{"company":"Acme","title":"Senior PM","description":"Full job text",'
            '"questions":["Why this role?"],"requires_cover_letter":false}'
        ),
        agent=agent,
    )
    result = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    ).kickoff(inputs={"url": url})
    return parse_direct_vacancy_result(result)


class PrepVacancyFlow(Flow):
    def __init__(
        self,
        url: str,
        chat_id: int | str,
        user_id: int | str,
        date: str | None = None,
        extractor: Callable[[str], PreparedVacancy] | None = None,
        application_flow_factory=ApplicationFlow,
        notifier: Notifier | None = None,
    ):
        super().__init__()
        self._url = url
        self._chat_id = chat_id
        self._user_id = user_id
        self._date = date
        self._extractor = extractor or extract_direct_vacancy
        self._application_flow_factory = application_flow_factory
        self._notifier = notifier or TelegramNotifierTool()

    @start()
    def run(self) -> dict:
        existing = self._find_existing_complete_record()
        if existing:
            run_date, vacancy_id, vacancy, score = existing
            self._notify(
                f"Reusing existing vacancy record: <b>{vacancy['company']} — {vacancy['title']}</b>"
            )
            return self._run_application(run_date, vacancy_id, vacancy, score)

        run_date = self._date or today()
        try:
            prepared = self._extractor(self._url)
        except Exception as exc:
            self._notify(
                f"Failed to extract vacancy details: {type(exc).__name__}: {exc}"
            )
            return {"status": "failed", "error": str(exc)}

        vacancy_id = make_vacancy_id(prepared.company, prepared.title)
        self._notify(
            f"Vacancy details extracted: <b>{prepared.company} — {prepared.title}</b>"
        )

        vacancies_dir(run_date).mkdir(parents=True, exist_ok=True)
        scores_dir(run_date).mkdir(parents=True, exist_ok=True)

        vacancy = {
            "id": vacancy_id,
            "company": prepared.company,
            "title": prepared.title,
            "url": self._url,
            "description": prepared.description,
            "questions": prepared.questions,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        score = {
            "vacancy_id": vacancy_id,
            "date": run_date,
            "company": prepared.company,
            "title": prepared.title,
            "score": 100,
            "reasoning": "Manual prep requested by Telegram command.",
            "status": "approved",
            "requires_cover_letter": prepared.requires_cover_letter,
        }

        (vacancies_dir(run_date) / f"{vacancy_id}.json").write_text(
            json.dumps(vacancy, indent=2), encoding="utf-8"
        )
        (scores_dir(run_date) / f"{vacancy_id}.json").write_text(
            json.dumps(score, indent=2), encoding="utf-8"
        )
        return self._run_application(run_date, vacancy_id, vacancy, score)

    def _find_existing_complete_record(self):
        for vacancy_file in all_vacancy_files():
            try:
                vacancy = json.loads(vacancy_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if vacancy.get("url") != self._url:
                continue
            run_date = vacancy_file.parents[1].name
            vacancy_id = vacancy.get("id") or vacancy_file.stem
            score_file = scores_dir(run_date) / f"{vacancy_id}.json"
            if not score_file.exists():
                continue
            try:
                score = json.loads(score_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            return run_date, vacancy_id, vacancy, score
        return None

    def _run_application(
        self, run_date: str, vacancy_id: str, vacancy: dict, score: dict
    ) -> dict:
        try:
            self._notify("Application generation started.")
            self._application_flow_factory(
                vacancy_id=vacancy_id,
                date=run_date,
                notifier=None,
            ).kickoff()
            self._send_artifact_progress(run_date, vacancy_id, score)
            self._notifier._run(
                message_type="completion",
                company=vacancy["company"],
                title=vacancy["title"],
                url=vacancy.get("url", self._url),
                score=score.get("score", 100),
                vacancy_id=vacancy_id,
                date=run_date,
                chat_id=self._chat_id,
            )
            return {"status": "completed", "vacancy_id": vacancy_id, "date": run_date}
        except Exception as exc:
            self._notify(
                f"Application generation failed for <code>{vacancy_id}</code> "
                f"on <code>{run_date}</code>: {type(exc).__name__}: {exc}"
            )
            return {
                "status": "failed",
                "vacancy_id": vacancy_id,
                "date": run_date,
                "error": str(exc),
            }

    def _send_artifact_progress(self, run_date: str, vacancy_id: str, score: dict) -> None:
        app_dir = Path("data") / run_date / "applications" / vacancy_id
        if (app_dir / "qa-answers.md").exists():
            self._notify("Q&amp;A answers created.")
        if (app_dir / "cv.pdf").exists() or (app_dir / "cv.tex").exists():
            self._notify("CV created.")
        if (app_dir / "cover-letter.pdf").exists() or (
            app_dir / "cover-letter.tex"
        ).exists():
            self._notify("Cover letter created.")
        elif not score.get("requires_cover_letter", False):
            self._notify("Cover letter not required.")

    def _notify(self, text: str) -> None:
        try:
            self._notifier.send_text(text, chat_id=self._chat_id)
        except Exception as exc:
            logger.warning("Failed to send prep vacancy progress message: %s", exc)
