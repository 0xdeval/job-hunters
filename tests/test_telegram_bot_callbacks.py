import asyncio
from unittest.mock import AsyncMock, MagicMock

from job_hunting.bot.telegram_bot import handle_callback


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
    assert "Approved" in query.edit_message_text.await_args.args[0]

