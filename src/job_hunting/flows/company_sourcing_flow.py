import csv
from pathlib import Path

from crewai.flow.flow import Flow, listen, start

from job_hunting.crews.company_sourcing.crew import CompanySourcingCrew
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import company_candidates_file, today


class CompanySourcingFlow(Flow):

    @start()
    def run_company_sourcing_crew(self) -> dict:
        run_date = today()
        output = company_candidates_file(run_date)
        output.parent.mkdir(parents=True, exist_ok=True)

        CompanySourcingCrew().crew().kickoff(inputs={"today": run_date})
        if not output.exists():
            raise FileNotFoundError(
                f"Company sourcing completed without creating expected output: {output}"
            )

        return {
            "run_date": run_date,
            "candidate_count": self._count_pending_candidates(output),
            "path": output,
        }

    @listen(run_company_sourcing_crew)
    def send_review_notification(self, result: dict) -> None:
        if result["candidate_count"] <= 0:
            print("No company candidates pending review.")
            return

        TelegramNotifierTool().send_company_candidates_review(
            run_date=result["run_date"],
            candidate_count=result["candidate_count"],
            path=result["path"],
        )

    @staticmethod
    def _count_pending_candidates(path: Path) -> int:
        if not path.exists():
            return 0

        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return sum(1 for row in reader if row.get("status") == "pending_review")
