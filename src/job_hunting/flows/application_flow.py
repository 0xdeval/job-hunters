import json
from crewai.flow.flow import Flow, listen, start
from job_hunting.crews.application.crew import ApplicationCrew
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import vacancies_dir, scores_dir

_DEFAULT_NOTIFIER = object()


class ApplicationFlow(Flow):

    def __init__(self, vacancy_id: str, date: str, notifier=_DEFAULT_NOTIFIER):
        super().__init__()
        self._vacancy_id = vacancy_id
        self._date = date
        self._notifier = (
            TelegramNotifierTool() if notifier is _DEFAULT_NOTIFIER else notifier
        )

    @start()
    def run_application_crew(self) -> dict:
        vacancy_path = vacancies_dir(self._date) / f"{self._vacancy_id}.json"
        score_path = scores_dir(self._date) / f"{self._vacancy_id}.json"

        vacancy = json.loads(vacancy_path.read_text())
        score = json.loads(score_path.read_text())

        score["status"] = "approved"
        score_path.write_text(json.dumps(score, indent=2))

        ApplicationCrew().crew().kickoff(
            inputs={
                "company": vacancy["company"],
                "title": vacancy["title"],
                "url": vacancy["url"],
                "description": vacancy["description"],
                "questions": "\n".join(vacancy.get("questions", [])),
                "vacancy_id": self._vacancy_id,
                "date": self._date,
                "requires_cover_letter": str(score.get("requires_cover_letter", False)).lower(),
            }
        )
        return {"vacancy": vacancy, "score": score}

    @listen(run_application_crew)
    def notify_completion(self, result: dict) -> None:
        vacancy = result["vacancy"]
        score = result["score"]

        score_path = scores_dir(self._date) / f"{self._vacancy_id}.json"
        score["status"] = "documents_ready"
        score_path.write_text(json.dumps(score, indent=2))

        if self._notifier is None:
            return

        self._notifier._run(
            message_type="completion",
            company=vacancy["company"],
            title=vacancy["title"],
            url=vacancy["url"],
            score=score["score"],
            vacancy_id=self._vacancy_id,
            date=self._date,
        )
