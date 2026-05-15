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


def test_send_company_candidate_review_uses_html_links_and_buttons():
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=45))

    candidate = {
        "candidate_id": "acme-12345678",
        "company": "Acme <Labs>",
        "career_page": "https://acme.example/jobs?team=product&remote=true",
        "website": "https://acme.example",
        "description": "Builds workflow tools for finance teams.",
        "industry": "FinTech",
    }

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot):
        result = tool.send_company_candidate_review(
            run_date="2026-05-13",
            candidate=candidate,
        )

    assert result == "Company candidate review notification sent for acme-12345678"
    _, kwargs = mock_bot.send_message.call_args
    assert kwargs["parse_mode"] == "HTML"
    assert "Acme &lt;Labs&gt;" in kwargs["text"]
    assert "href=\"https://acme.example\"" in kwargs["text"]
    assert "href=\"https://acme.example/jobs?team=product&amp;remote=true\"" in kwargs["text"]
    assert "Builds workflow tools for finance teams." in kwargs["text"]
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Approve"
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == (
        "company_approve:acme-12345678:2026-05-13"
    )
    assert kwargs["reply_markup"].inline_keyboard[0][1].text == "Decline"
    assert kwargs["reply_markup"].inline_keyboard[0][1].callback_data == (
        "company_decline:acme-12345678:2026-05-13"
    )


def test_send_company_candidate_review_truncates_callback_data_to_64_bytes():
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=46))

    candidate = {
        "candidate_id": "acme-" + ("x" * 80),
        "company": "Acme Labs",
        "career_page": "https://acme.example/jobs",
        "website": "https://acme.example",
        "description": "Builds tools.",
        "industry": "FinTech",
    }

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot):
        tool.send_company_candidate_review(
            run_date="2026-05-13",
            candidate=candidate,
        )

    _, kwargs = mock_bot.send_message.call_args
    approve_cb = kwargs["reply_markup"].inline_keyboard[0][0].callback_data
    decline_cb = kwargs["reply_markup"].inline_keyboard[0][1].callback_data
    assert len(approve_cb.encode("utf-8")) <= 64
    assert len(decline_cb.encode("utf-8")) <= 64
    assert approve_cb.startswith("company_approve:")
    assert decline_cb.startswith("company_decline:")
    assert approve_cb.endswith(":2026-05-13")
    assert decline_cb.endswith(":2026-05-13")


def test_build_company_link_line_handles_missing_url():
    assert TelegramNotifierTool._build_company_link_line("Website", "") == "Website unavailable"


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


def test_send_company_candidates_message_has_no_inline_keyboard(tmp_path: Path):
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=45))
    mock_bot.send_document = AsyncMock()

    csv_path = tmp_path / "company_candidates.csv"
    csv_path.write_text("company,status\nAcme,pending\n")

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot):
        result = tool.send_company_candidates_review(
            run_date="2026-05-11",
            candidate_count=7,
            path=csv_path,
        )

    assert result == "Company candidates review notification sent for 2026-05-11"
    _, kwargs = mock_bot.send_message.call_args
    assert kwargs["parse_mode"] == "HTML"
    assert kwargs["reply_markup"] is None
    assert "Candidates: <b>7</b>" in kwargs["text"]
    assert str(csv_path) in kwargs["text"]
    assert "status=approved" in kwargs["text"]
    mock_bot.send_document.assert_not_called()
