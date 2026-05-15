import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_hunting.flows.application_flow import ApplicationFlow
from job_hunting.profile_context import ApplicationProfileContext


def test_application_flow_passes_prepared_profile_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vacancy_dir = Path("data/2026-05-14/vacancies")
    score_dir = Path("data/2026-05-14/scores")
    vacancy_dir.mkdir(parents=True)
    score_dir.mkdir(parents=True)
    (vacancy_dir / "acme--pm.json").write_text(
        json.dumps(
            {
                "id": "acme--pm",
                "company": "Acme",
                "title": "Senior PM",
                "url": "https://acme.example/jobs/pm",
                "description": "Build product workflows.",
                "questions": ["Why Acme?"],
            }
        ),
        encoding="utf-8",
    )
    (score_dir / "acme--pm.json").write_text(
        json.dumps(
            {
                "vacancy_id": "acme--pm",
                "date": "2026-05-14",
                "company": "Acme",
                "title": "Senior PM",
                "score": 90,
                "status": "pending_approval",
                "requires_cover_letter": True,
            }
        ),
        encoding="utf-8",
    )

    crew = MagicMock()
    crew.kickoff.return_value = None
    app_crew = MagicMock()
    app_crew.crew.return_value = crew

    with patch(
        "job_hunting.flows.application_flow.ApplicationCrew", return_value=app_crew
    ), patch(
        "job_hunting.flows.application_flow.build_application_context",
        return_value=ApplicationProfileContext(
            identity_context="identity context",
            profile_sections_context="profile sections context",
            section_keys=("summary", "skills"),
        ),
    ):
        ApplicationFlow(
            vacancy_id="acme--pm", date="2026-05-14", notifier=None
        ).run_application_crew()

    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["identity_context"] == "identity context"
    assert inputs["profile_sections_context"] == "profile sections context"
    assert inputs["profile_section_keys"] == "summary, skills"
    assert inputs["artifact_filename_base"] == "Acme-SeniorPM"


def test_notify_completion_does_not_fail_when_telegram_completion_times_out(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    score_dir = Path("data/2026-05-14/scores")
    score_dir.mkdir(parents=True)
    score_path = score_dir / "acme--pm.json"
    score = {
        "vacancy_id": "acme--pm",
        "date": "2026-05-14",
        "company": "Acme",
        "title": "Senior PM",
        "score": 90,
        "status": "approved",
    }
    score_path.write_text(json.dumps(score), encoding="utf-8")
    notifier = MagicMock()
    notifier._run.side_effect = TimeoutError("Timed out")
    flow = ApplicationFlow(
        vacancy_id="acme--pm",
        date="2026-05-14",
        notifier=notifier,
    )

    try:
        flow.notify_completion(
            {
                "vacancy": {
                    "company": "Acme",
                    "title": "Senior PM",
                    "url": "https://acme.example/jobs/pm",
                },
                "score": score,
            }
        )
    except TimeoutError as exc:
        pytest.fail(f"completion notification timeout should be non-fatal: {exc}")

    updated_score = json.loads(score_path.read_text(encoding="utf-8"))
    assert updated_score["status"] == "documents_ready"
    assert updated_score["notification_error"] == "Timed out"
