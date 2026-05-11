from pathlib import Path
from unittest.mock import MagicMock

import pytest

from job_hunting.flows.company_sourcing_flow import CompanySourcingFlow


def test_run_company_sourcing_crew_and_notify(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.today", lambda: "2026-05-11")

    output = Path("data/2026-05-11/company_candidates.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "company,career_page,website,source,industry,match_score,match_reason,status,discovered_at\n"
        "Acme,https://acme.com/careers,https://acme.com,public_search,FinTech,85,Strong fit,pending_review,2026-05-11T09:00:00Z\n"
        "Beta,https://beta.com/careers,https://beta.com,public_search,SaaS,70,Weak fit,skipped,2026-05-11T09:00:00Z\n"
        "Gamma,https://gamma.com/jobs,https://gamma.com,public_search,AI,92,Excellent fit,pending_review,2026-05-11T09:00:00Z\n",
        encoding="utf-8",
    )

    kickoff = MagicMock()
    crew_obj = MagicMock()
    crew_obj.kickoff = kickoff
    crew_cls = MagicMock()
    crew_cls.return_value.crew.return_value = crew_obj
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.CompanySourcingCrew", crew_cls)

    notifier = MagicMock()
    notifier_cls = MagicMock(return_value=notifier)
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.TelegramNotifierTool", notifier_cls)

    flow = CompanySourcingFlow()
    result = flow.run_company_sourcing_crew()

    assert result == {
        "run_date": "2026-05-11",
        "candidate_count": 2,
        "path": output,
    }
    kickoff.assert_called_once_with(inputs={"today": "2026-05-11"})

    flow.send_review_notification(result)
    notifier.send_company_candidates_review.assert_called_once_with(
        run_date="2026-05-11",
        candidate_count=2,
        path=output,
    )


def test_send_review_notification_skips_when_no_pending(monkeypatch, capsys):
    notifier = MagicMock()
    notifier_cls = MagicMock(return_value=notifier)
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.TelegramNotifierTool", notifier_cls)

    flow = CompanySourcingFlow()
    flow.send_review_notification(
        {
            "run_date": "2026-05-11",
            "candidate_count": 0,
            "path": Path("data/2026-05-11/company_candidates.csv"),
        }
    )

    captured = capsys.readouterr()
    assert "No company candidates pending review." in captured.out
    notifier.send_company_candidates_review.assert_not_called()


def test_run_company_sourcing_crew_raises_when_output_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.today", lambda: "2026-05-11")

    kickoff = MagicMock()
    crew_obj = MagicMock()
    crew_obj.kickoff = kickoff
    crew_cls = MagicMock()
    crew_cls.return_value.crew.return_value = crew_obj
    monkeypatch.setattr("job_hunting.flows.company_sourcing_flow.CompanySourcingCrew", crew_cls)

    flow = CompanySourcingFlow()

    with pytest.raises(FileNotFoundError, match="Company sourcing completed without creating"):
        flow.run_company_sourcing_crew()

    kickoff.assert_called_once_with(inputs={"today": "2026-05-11"})


def test_count_pending_candidates_returns_zero_for_missing_file(tmp_path):
    missing = tmp_path / "missing.csv"
    assert CompanySourcingFlow._count_pending_candidates(missing) == 0
