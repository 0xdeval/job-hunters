import json
from pathlib import Path

from job_hunting.flows import prep_vacancy_flow as prep_module
from job_hunting.flows.prep_vacancy_flow import PreparedVacancy, PrepVacancyFlow


class _Notifier:
    def __init__(self):
        self.texts: list[tuple[str, int]] = []
        self.completions: list[dict] = []

    def send_text(self, text: str, chat_id: int | str | None = None) -> str:
        self.texts.append((text, int(chat_id)))
        return "sent"

    def _run(self, **kwargs) -> str:
        self.completions.append(kwargs)
        return "completion sent"


def test_prep_vacancy_flow_writes_files_and_runs_application(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    application_calls: list[tuple[str, str, object]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str, notifier):
            self.vacancy_id = vacancy_id
            self.date = date
            self.notifier = notifier

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date, self.notifier))
            app_dir = Path("data") / self.date / "applications" / self.vacancy_id
            app_dir.mkdir(parents=True, exist_ok=True)
            (app_dir / "Acme-SeniorPM-QA.md").write_text("answers", encoding="utf-8")
            (app_dir / "Acme-SeniorPM-CV.pdf").write_text("cv", encoding="utf-8")
            (app_dir / "Acme-SeniorPM-CoverLetter.pdf").write_text(
                "letter", encoding="utf-8"
            )

    notifier = _Notifier()
    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/senior-pm",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: PreparedVacancy(
            company="Acme",
            title="Senior PM",
            description="Build product systems.",
            questions=["Why Acme?"],
            requires_cover_letter=True,
        ),
        application_flow_factory=_ApplicationFlow,
        notifier=notifier,
    )

    result = flow.kickoff()

    assert result["vacancy_id"] == "acme--senior-pm"
    vacancy = json.loads(Path("data/2026-05-13/vacancies/acme--senior-pm.json").read_text())
    assert vacancy["company"] == "Acme"
    assert vacancy["title"] == "Senior PM"
    assert vacancy["url"] == "https://acme.com/jobs/senior-pm"
    assert vacancy["questions"] == ["Why Acme?"]

    score = json.loads(Path("data/2026-05-13/scores/acme--senior-pm.json").read_text())
    assert score["score"] == 100
    assert score["status"] == "approved"
    assert score["requires_cover_letter"] is True
    assert application_calls == [("acme--senior-pm", "2026-05-13", None)]
    assert notifier.completions[0]["chat_id"] == 12345
    assert any("Vacancy details extracted" in text for text, _ in notifier.texts)
    assert any("CV created" in text for text, _ in notifier.texts)


def test_prep_vacancy_flow_does_not_fail_when_completion_notification_times_out(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-14")
    application_calls: list[tuple[str, str, object]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str, notifier):
            self.vacancy_id = vacancy_id
            self.date = date
            self.notifier = notifier

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date, self.notifier))
            app_dir = Path("data") / self.date / "applications" / self.vacancy_id
            app_dir.mkdir(parents=True, exist_ok=True)
            (app_dir / "qa-answers.md").write_text("answers", encoding="utf-8")
            (app_dir / "cv.pdf").write_text("cv", encoding="utf-8")

    class _TimeoutNotifier(_Notifier):
        def _run(self, **kwargs) -> str:
            self.completions.append(kwargs)
            raise TimeoutError("Timed out")

    notifier = _TimeoutNotifier()
    flow = PrepVacancyFlow(
        url="https://xolo.example/jobs/product-marketing-manager",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: PreparedVacancy(
            company="Xolo",
            title="Product Marketing Manager",
            description="Own product marketing.",
            questions=[],
            requires_cover_letter=False,
        ),
        application_flow_factory=_ApplicationFlow,
        notifier=notifier,
    )

    result = flow.kickoff()

    assert result == {
        "status": "completed",
        "vacancy_id": "xolo--product-marketing-manager",
        "date": "2026-05-14",
        "notification_error": "Timed out",
    }
    assert application_calls == [
        ("xolo--product-marketing-manager", "2026-05-14", None)
    ]
    assert any("CV created" in text for text, _ in notifier.texts)
    assert any("completion notification failed" in text for text, _ in notifier.texts)
    assert not any("Application generation failed" in text for text, _ in notifier.texts)


def test_prep_vacancy_flow_reuses_existing_complete_record(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    vacancy_dir = Path("data/2026-05-12/vacancies")
    score_dir = Path("data/2026-05-12/scores")
    vacancy_dir.mkdir(parents=True)
    score_dir.mkdir(parents=True)
    (vacancy_dir / "acme--senior-pm.json").write_text(
        json.dumps(
            {
                "id": "acme--senior-pm",
                "company": "Acme",
                "title": "Senior PM",
                "url": "https://acme.com/jobs/senior-pm",
                "description": "Existing description",
                "questions": [],
                "scraped_at": "2026-05-12T10:00:00",
            }
        ),
        encoding="utf-8",
    )
    (score_dir / "acme--senior-pm.json").write_text(
        json.dumps(
            {
                "vacancy_id": "acme--senior-pm",
                "date": "2026-05-12",
                "company": "Acme",
                "title": "Senior PM",
                "score": 80,
                "reasoning": "Existing score",
                "status": "approved",
                "requires_cover_letter": False,
            }
        ),
        encoding="utf-8",
    )
    application_calls: list[tuple[str, str, object]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str, notifier):
            self.vacancy_id = vacancy_id
            self.date = date
            self.notifier = notifier

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date, self.notifier))

    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/senior-pm",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: (_ for _ in ()).throw(AssertionError("extractor should not run")),
        application_flow_factory=_ApplicationFlow,
        notifier=_Notifier(),
    )

    result = flow.kickoff()

    assert result["vacancy_id"] == "acme--senior-pm"
    assert result["date"] == "2026-05-12"
    assert application_calls == [("acme--senior-pm", "2026-05-12", None)]


def test_prep_vacancy_flow_ignores_existing_record_without_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    vacancy_dir = Path("data/2026-05-12/vacancies")
    score_dir = Path("data/2026-05-12/scores")
    vacancy_dir.mkdir(parents=True)
    score_dir.mkdir(parents=True)
    (vacancy_dir / "typeform--none.json").write_text(
        json.dumps(
            {
                "id": "typeform--none",
                "company": "Typeform",
                "title": None,
                "url": "https://job-boards.greenhouse.io/typeform/jobs/7905221",
                "description": "Existing description",
                "questions": [],
            }
        ),
        encoding="utf-8",
    )
    (score_dir / "typeform--none.json").write_text(
        json.dumps(
            {
                "vacancy_id": "typeform--none",
                "date": "2026-05-12",
                "company": "Typeform",
                "title": None,
                "score": 80,
                "status": "approved",
                "requires_cover_letter": False,
            }
        ),
        encoding="utf-8",
    )
    application_calls: list[tuple[str, str, object]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str, notifier):
            self.vacancy_id = vacancy_id
            self.date = date
            self.notifier = notifier

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date, self.notifier))

    flow = PrepVacancyFlow(
        url="https://job-boards.greenhouse.io/typeform/jobs/7905221",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: PreparedVacancy(
            company="Typeform",
            title="Senior Product Manager - Growth",
            description="Own growth.",
            questions=[],
            requires_cover_letter=False,
        ),
        application_flow_factory=_ApplicationFlow,
        notifier=_Notifier(),
    )

    result = flow.kickoff()

    assert result["vacancy_id"] == "typeform--senior-product-manager-growth"
    assert result["date"] == "2026-05-13"
    assert application_calls == [
        ("typeform--senior-product-manager-growth", "2026-05-13", None)
    ]


def test_prep_vacancy_flow_reports_extraction_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    notifier = _Notifier()

    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/broken",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: (_ for _ in ()).throw(ValueError("could not extract title")),
        application_flow_factory=lambda *args, **kwargs: None,
        notifier=notifier,
    )

    result = flow.kickoff()

    assert result["status"] == "failed"
    assert "could not extract title" in notifier.texts[-1][0]
    assert not Path("data/2026-05-13/applications").exists()


def test_parse_direct_vacancy_result_accepts_json_payload():
    payload = json.dumps(
        {
            "company": "Acme",
            "title": "Senior PM",
            "description": "Own product strategy.",
            "questions": ["Why this role?"],
            "requires_cover_letter": False,
        }
    )

    result = prep_module.parse_direct_vacancy_result(payload)

    assert result == PreparedVacancy(
        company="Acme",
        title="Senior PM",
        description="Own product strategy.",
        questions=["Why this role?"],
        requires_cover_letter=False,
    )


def test_parse_direct_vacancy_result_rejects_null_title():
    payload = json.dumps(
        {
            "company": "Typeform",
            "title": None,
            "description": "Own product growth.",
            "questions": [],
            "requires_cover_letter": False,
        }
    )

    try:
        prep_module.parse_direct_vacancy_result(payload)
    except ValueError as exc:
        assert "could not extract title" in str(exc)
    else:
        raise AssertionError("Expected null title to be rejected")
