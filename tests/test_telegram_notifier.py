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
    assert "Here are all necessary files for applying to" in message_kwargs["text"]
    assert "Attached files" in message_kwargs["text"]


def test_send_completion_message_prefers_company_title_document_names(tmp_path: Path):
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=43))
    mock_bot.send_document = AsyncMock(return_value=MagicMock(message_id=44))

    app_dir = tmp_path / "applications" / "kraken--senior-product-manager"
    app_dir.mkdir(parents=True)
    (app_dir / "Kraken-SeniorProductManager-CV.pdf").write_text("fake cv")
    (app_dir / "Kraken-SeniorProductManager-QA.md").write_text("fake qa")
    (app_dir / "Kraken-SeniorProductManager-CoverLetter.pdf").write_text("fake letter")
    (app_dir / "cv.pdf").write_text("old fake cv")
    (app_dir / "qa-answers.md").write_text("old fake qa")
    (app_dir / "cover-letter.pdf").write_text("old fake letter")

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot), patch(
        "job_hunting.tools.telegram_notifier.applications_dir",
        return_value=app_dir,
    ):
        asyncio.run(
            tool._send(
                message_type="completion",
                company="Kraken",
                title="Senior Product Manager",
                url="https://kraken.com/jobs/pm",
                score=85,
                vacancy_id="kraken--senior-product-manager",
                date="2026-05-10",
            )
        )

    sent_paths = [call.kwargs["document"] for call in mock_bot.send_document.call_args_list]
    assert sent_paths == [
        app_dir / "Kraken-SeniorProductManager-CV.pdf",
        app_dir / "Kraken-SeniorProductManager-QA.md",
        app_dir / "Kraken-SeniorProductManager-CoverLetter.pdf",
    ]


def test_send_completion_message_uses_supplied_chat_id(tmp_path: Path):
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=46))
    mock_bot.send_document = AsyncMock(return_value=MagicMock(message_id=47))

    app_dir = tmp_path / "applications" / "acme--senior-pm"
    app_dir.mkdir(parents=True)
    (app_dir / "cv.pdf").write_text("fake cv")
    (app_dir / "qa-answers.md").write_text("fake qa")

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
                score=100,
                vacancy_id="acme--senior-pm",
                date="2026-05-13",
                chat_id=98765,
            )
        )

    for call in mock_bot.send_document.call_args_list:
        assert call.kwargs["chat_id"] == 98765
    _, message_kwargs = mock_bot.send_message.call_args
    assert message_kwargs["chat_id"] == 98765


def test_send_text_uses_supplied_chat_id():
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=48))

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot):
        result = tool.send_text("Working on it", chat_id=98765)

    assert result == "Telegram message sent"
    _, kwargs = mock_bot.send_message.call_args
    assert kwargs["chat_id"] == 98765
    assert kwargs["text"] == "Working on it"
    assert kwargs["parse_mode"] == "HTML"
    assert kwargs["reply_markup"] is None

