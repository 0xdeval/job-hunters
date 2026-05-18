import json
import csv
import re
import time
from crewai.flow.flow import Flow, listen, start
from telegram.error import RetryAfter
from job_hunting.crews.discovery.crew import DiscoveryCrew
from job_hunting.config import MIN_SCORE
from job_hunting.profile_context import build_discovery_context
from job_hunting.tools.discovery_coverage import DiscoveryCoverageStore
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import (
    all_score_files,
    scores_dir,
    today,
    vacancies_dir,
)


class DiscoveryFlow(Flow):
    def __init__(
        self,
        *args,
        crew_factory=None,
        notifier_factory=None,
        sleep=None,
        approval_send_delay_seconds: float = 1.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._crew_factory = crew_factory or (lambda: DiscoveryCrew().crew())
        self._notifier_factory = notifier_factory or TelegramNotifierTool
        self._sleep = sleep or time.sleep
        self._approval_send_delay_seconds = approval_send_delay_seconds

    @start()
    def run_discovery_crew(self) -> list[dict]:
        today_str = today()
        profile_context = build_discovery_context()

        # Ensure today's directories exist so agents can write to them
        vacancies_dir(today_str).mkdir(parents=True, exist_ok=True)
        scores_dir(today_str).mkdir(parents=True, exist_ok=True)
        companies = self._load_companies()
        coverage_store = DiscoveryCoverageStore(today_str)
        coverage_store.initialize_from_companies(companies=companies)

        for company, career_page in companies:
            try:
                self._crew_factory().kickoff(
                    inputs={
                        "today": today_str,
                        "company": company,
                        "career_page": career_page,
                        "discovery_filter_context": profile_context.filter_context,
                        "candidate_scoring_context": profile_context.scoring_context,
                    }
                )
            except Exception as exc:
                coverage_store.record(
                    company=company,
                    career_page=career_page,
                    status="failed",
                    jobs_found=0,
                    matched_jobs=0,
                    notes=self._format_failure_note(exc),
                )

        # 2. Scan ALL historical data for any vacancies that are still 'pending_approval'
        qualifying = []
        for score_file in all_score_files():
            try:
                data = json.loads(score_file.read_text())
                if data.get("score", 0) >= MIN_SCORE and data.get("status") == "pending_approval":
                    qualifying.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return qualifying

    @listen(run_discovery_crew)
    def send_approval_requests(self, qualifying_vacancies: list[dict]) -> None:
        if not qualifying_vacancies:
            print("No qualifying vacancies found today.")
            return

        notifier = self._notifier_factory()
        for index, vacancy in enumerate(qualifying_vacancies):
            self._send_approval_request_with_retry(notifier, vacancy)
            print(f"Sent approval request for {vacancy['vacancy_id']}")
            if index < len(qualifying_vacancies) - 1 and self._approval_send_delay_seconds > 0:
                self._sleep(self._approval_send_delay_seconds)

    def _send_approval_request_with_retry(self, notifier, vacancy: dict) -> None:
        while True:
            try:
                notifier._run(
                    message_type="approval",
                    company=vacancy["company"],
                    title=vacancy["title"],
                    url=vacancy.get("url", ""),
                    score=vacancy["score"],
                    vacancy_id=vacancy["vacancy_id"],
                    date=vacancy["date"],
                )
                return
            except RetryAfter as exc:
                self._sleep(_retry_after_seconds(exc))

    @staticmethod
    def _format_failure_note(exc: Exception) -> str:
        return f"Crew kickoff failed: {type(exc).__name__}: {exc}"

    @staticmethod
    def _load_companies() -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        companies_path = "knowledge/companies.csv"
        try:
            with open(companies_path, newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    company = (row.get("Company") or row.get("company") or "").strip()
                    career_page = (
                        row.get("Career page") or row.get("career_page") or ""
                    ).strip()
                    if not (company or career_page):
                        continue
                    dedupe_key = (
                        _normalize_company_key(company),
                        career_page.rstrip("/").casefold(),
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    rows.append((company, career_page))
        except FileNotFoundError:
            pass
        return rows


def _retry_after_seconds(exc: RetryAfter) -> float:
    retry_after = exc.retry_after
    if hasattr(retry_after, "total_seconds"):
        return retry_after.total_seconds()
    return float(retry_after)


def _normalize_company_key(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name.strip().casefold())
    normalized = re.sub(r"[,.]", "", normalized)
    return re.sub(r"\b(inc|incorporated|ltd|llc|gmbh|sa|plc)\b$", "", normalized).strip()
