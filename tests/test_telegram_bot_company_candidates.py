import asyncio
import csv
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from job_hunting.bot.telegram_bot import handle_callback
from job_hunting.tools.telegram_notifier import TelegramNotifierTool


def _update(callback_data: str):
    query = MagicMock()
    query.data = callback_data
    query.from_user.id = 123
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_chat.id = 123
    return update, query


def test_company_approve_updates_candidate_and_appends_approved_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    Path("knowledge").mkdir()
    Path("knowledge/companies.csv").write_text("Company,Career page\n", encoding="utf-8")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "acme-id,Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    update, query = _update("company_approve:acme-id:2026-05-13")

    asyncio.run(handle_callback(update, MagicMock()))

    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "approved"
    assert rows[0]["reviewed_at"]
    approved_rows = list(
        csv.DictReader(Path("knowledge/approved-company-candidates.csv").open())
    )
    assert approved_rows == [{"Company": "Acme", "Career page": "https://acme.example/jobs"}]
    query.edit_message_text.assert_awaited_once()
    assert "Approved company" in query.edit_message_text.await_args.args[0]


def test_company_decline_updates_candidate_without_approved_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "acme-id,Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    update, query = _update("company_decline:acme-id:2026-05-13")

    asyncio.run(handle_callback(update, MagicMock()))

    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "declined"
    assert rows[0]["reviewed_at"]
    assert not Path("knowledge/approved-company-candidates.csv").exists()
    assert "Declined company" in query.edit_message_text.await_args.args[0]


def test_invalid_company_callback_does_not_create_approved_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    update, query = _update("company_approve:missing-id:2026-05-13")

    asyncio.run(handle_callback(update, MagicMock()))

    assert not Path("knowledge/approved-company-candidates.csv").exists()
    assert "Could not find company candidate" in query.edit_message_text.await_args.args[0]


def test_company_approve_with_truncated_callback_id_resolves_unique_candidate(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    Path("knowledge").mkdir()
    Path("knowledge/companies.csv").write_text("Company,Career page\n", encoding="utf-8")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    long_candidate_id = "very-long-company-candidate-id-that-was-truncated"
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        f"{long_candidate_id},Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    callback = TelegramNotifierTool._build_company_callback_data(
        "company_approve", long_candidate_id, "2026-05-13"
    )
    update, query = _update(callback)

    asyncio.run(handle_callback(update, MagicMock()))

    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "approved"
    approved_rows = list(
        csv.DictReader(Path("knowledge/approved-company-candidates.csv").open())
    )
    assert approved_rows == [{"Company": "Acme", "Career page": "https://acme.example/jobs"}]
    assert "Approved company" in query.edit_message_text.await_args.args[0]


def test_repeated_click_on_truncated_company_callback_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    Path("knowledge").mkdir()
    Path("knowledge/companies.csv").write_text("Company,Career page\n", encoding="utf-8")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    long_candidate_id = "very-long-company-candidate-id-that-was-truncated"
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        f"{long_candidate_id},Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    callback = TelegramNotifierTool._build_company_callback_data(
        "company_approve", long_candidate_id, "2026-05-13"
    )
    first_update, first_query = _update(callback)
    second_update, second_query = _update(callback)

    asyncio.run(handle_callback(first_update, MagicMock()))
    asyncio.run(handle_callback(second_update, MagicMock()))

    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "approved"
    approved_rows = list(
        csv.DictReader(Path("knowledge/approved-company-candidates.csv").open())
    )
    assert approved_rows == [{"Company": "Acme", "Career page": "https://acme.example/jobs"}]
    assert "Approved company" in first_query.edit_message_text.await_args.args[0]
    assert "Could not find company candidate" not in second_query.edit_message_text.await_args.args[0]


def test_ambiguous_truncated_company_prefix_returns_error_without_file_update(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "shared-prefix-aaaa,Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n"
        "shared-prefix-bbbb,Bravo,https://bravo.example/jobs,https://bravo.example,Description,SaaS,search,88,Fit,pending_review,2026-05-13T09:01:00Z,\n",
        encoding="utf-8",
    )
    update, query = _update("company_approve:shared-prefix-:2026-05-13")

    asyncio.run(handle_callback(update, MagicMock()))

    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "pending_review"
    assert rows[1]["status"] == "pending_review"
    assert not Path("knowledge/approved-company-candidates.csv").exists()
    assert "Ambiguous company candidate" in query.edit_message_text.await_args.args[0]


def test_unauthorized_company_callback_is_rejected_without_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "999")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    candidate_file = Path("data/2026-05-13/company_candidates.csv")
    candidate_file.parent.mkdir(parents=True)
    candidate_file.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "acme-id,Acme,https://acme.example/jobs,https://acme.example,Description,FinTech,search,90,Fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )
    update, query = _update("company_approve:acme-id:2026-05-13")

    asyncio.run(handle_callback(update, MagicMock()))

    query.answer.assert_awaited_once_with(
        "You are not authorized to perform this action.", show_alert=True
    )
    rows = list(csv.DictReader(candidate_file.open()))
    assert rows[0]["status"] == "pending_review"
    assert not Path("knowledge/approved-company-candidates.csv").exists()


def test_vacancy_approve_callback_still_uses_vacancy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("job_hunting.bot.telegram_bot.TELEGRAM_ALLOWED_USERS", "")
    update, query = _update("approve:vacancy-id:2026-05-13")
    update_status = MagicMock(return_value="full-vacancy-id")
    thread_mock = MagicMock()
    thread_instance = MagicMock()
    thread_mock.return_value = thread_instance
    monkeypatch.setattr("job_hunting.bot.telegram_bot._update_status", update_status)
    monkeypatch.setattr("job_hunting.bot.telegram_bot.threading.Thread", thread_mock)

    asyncio.run(handle_callback(update, MagicMock()))

    update_status.assert_called_once_with("vacancy-id", "2026-05-13", "approved")
    thread_mock.assert_called_once()
    thread_instance.start.assert_called_once()
    assert thread_mock.call_args.kwargs["args"] == (
        "full-vacancy-id",
        "2026-05-13",
        123,
    )
    assert "Approved" in query.edit_message_text.await_args.args[0]
