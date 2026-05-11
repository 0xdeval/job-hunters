import json
from datetime import date
from crewai.flow.flow import Flow, listen, start
from job_hunting.crews.discovery.crew import DiscoveryCrew
from job_hunting.config import MIN_SCORE
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import scores_dir


class DiscoveryFlow(Flow):

    @start()
    def run_discovery_crew(self) -> list[dict]:
        today_str = date.today().isoformat()
        
        # Ensure today's directories exist so agents can write to them
        from job_hunting.utils import vacancies_dir, scores_dir
        vacancies_dir(today_str).mkdir(parents=True, exist_ok=True)
        scores_dir(today_str).mkdir(parents=True, exist_ok=True)

        # 1. Run the crew to find NEW vacancies
        DiscoveryCrew().crew().kickoff(inputs={"today": today_str})

        # 2. Scan ALL historical data for any vacancies that are still 'pending_approval'
        qualifying = []
        from pathlib import Path
        data_root = Path("data")
        
        # Look in all date directories (e.g., data/2026-05-11/scores/*.json)
        if data_root.exists():
            for score_file in data_root.glob("*/scores/*.json"):
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

        notifier = TelegramNotifierTool()
        for vacancy in qualifying_vacancies:
            notifier._run(
                message_type="approval",
                company=vacancy["company"],
                title=vacancy["title"],
                url=vacancy.get("url", ""),
                score=vacancy["score"],
                vacancy_id=vacancy["vacancy_id"],
                date=vacancy["date"],
            )
            print(f"Sent approval request for {vacancy['vacancy_id']}")
