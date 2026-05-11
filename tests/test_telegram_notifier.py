import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from job_hunting.tools.telegram_notifier import TelegramNotifierTool


def test_send_approval_message_resolves_url_from_vacancy_file(tmp_path: Path):
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=42))
    mock_bot.send_document = AsyncMock()

    vacancy_dir = tmp_path / "vacancies"
    vacancy_dir.mkdir(parents=True)
    (vacancy_dir / "acme--senior-pm.json").write_text(
        json.dumps({"url": "https://acme.com/jobs/pm"})
    )

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot), patch(
        "job_hunting.tools.telegram_notifier.vacancies_dir",
        return_value=vacancy_dir,
    ):
        asyncio.run(
            tool._send(
                message_type="approval",
                company="Acme",
                title="Senior PM",
                url="",
                score=85,
                vacancy_id="acme--senior-pm",
                date="2026-05-10",
            )
        )

    _, kwargs = mock_bot.send_message.call_args
    assert kwargs["parse_mode"] == "HTML"
    assert "href=\"https://acme.com/jobs/pm\"" in kwargs["text"]
    mock_bot.send_document.assert_not_called()


def test_send_completion_message_attaches_generated_documents(tmp_path: Path):
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=43))
    mock_bot.send_document = AsyncMock(return_value=MagicMock(message_id=44))

    app_dir = tmp_path / "applications" / "acme--senior-pm"
    app_dir.mkdir(parents=True)
    (app_dir / "cv.pdf").write_text("fake cv")
    (app_dir / "qa-answers.md").write_text("fake qa")
    (app_dir / "cover-letter.pdf").write_text("fake letter")

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot), patch(
        "job_hunting.tools.telegram_notifier.applications_dir",
        return_value=app_dir,
    ):
        asyncio.run(
            tool._send(
                message_type="completion",
                company="Acme",
                title="Senior PM",
                url="https://acme.com/jobs/pm",
                score=85,
                vacancy_id="acme--senior-pm",
                date="2026-05-10",
            )
        )

    assert mock_bot.send_document.call_count == 3
    sent_paths = [call.kwargs["document"] for call in mock_bot.send_document.call_args_list]
    assert app_dir / "cv.pdf" in sent_paths
    assert app_dir / "qa-answers.md" in sent_paths
    assert app_dir / "cover-letter.pdf" in sent_paths

    _, message_kwargs = mock_bot.send_message.call_args
    assert message_kwargs["parse_mode"] == "HTML"
    assert "Attached files" in message_kwargs["text"]
