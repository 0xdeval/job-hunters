from types import SimpleNamespace
from unittest.mock import MagicMock

from job_hunting.bot import telegram_bot


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs):
        self.replies.append(text)


def _update(text: str, chat_id: int = 12345, user_id: int = 777):
    message = _Message(text)
    user = SimpleNamespace(id=user_id)
    chat = SimpleNamespace(id=chat_id)
    return SimpleNamespace(
        message=message,
        effective_message=message,
        effective_user=user,
        effective_chat=chat,
    )


def test_prep_vacancy_command_enters_waiting_state(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    update = _update("/prep_vacancy")

    import asyncio

    asyncio.run(telegram_bot.handle_prep_vacancy_command(update, SimpleNamespace()))

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {
        "status": "waiting_for_url"
    }
    assert "Send the vacancy URL" in update.message.replies[-1]


def test_repeating_prep_vacancy_resets_same_user_state(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {
        "status": "waiting_for_url",
        "old": "state",
    }
    update = _update("/prep_vacancy")

    import asyncio

    asyncio.run(telegram_bot.handle_prep_vacancy_command(update, SimpleNamespace()))

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {
        "status": "waiting_for_url"
    }


def test_group_url_from_different_user_is_ignored(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {"status": "waiting_for_url"}
    update = _update("https://acme.com/jobs/pm", chat_id=12345, user_id=888)

    import asyncio

    asyncio.run(telegram_bot.handle_prep_vacancy_url(update, SimpleNamespace()))

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {
        "status": "waiting_for_url"
    }
    assert update.message.replies == []


def test_invalid_url_keeps_waiting_state(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {"status": "waiting_for_url"}
    update = _update("not a url")

    import asyncio

    asyncio.run(telegram_bot.handle_prep_vacancy_url(update, SimpleNamespace()))

    assert (12345, 777) in telegram_bot.PENDING_PREP_VACANCY
    assert "valid HTTP(S) URL" in update.message.replies[-1]


def test_valid_url_starts_background_flow_and_clears_state(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {"status": "waiting_for_url"}
    calls: list[dict] = []

    class _Thread:
        def __init__(self, target, args, daemon):
            calls.append({"target": target, "args": args, "daemon": daemon})

        def start(self):
            calls[-1]["started"] = True

    monkeypatch.setattr(telegram_bot.threading, "Thread", _Thread)
    update = _update("https://acme.com/jobs/pm")

    import asyncio

    asyncio.run(telegram_bot.handle_prep_vacancy_url(update, SimpleNamespace()))

    assert (12345, 777) not in telegram_bot.PENDING_PREP_VACANCY
    assert calls[0]["args"] == ("https://acme.com/jobs/pm", 12345, 777)
    assert calls[0]["daemon"] is True
    assert calls[0]["started"] is True
    assert "Started preparing" in update.message.replies[-1]


def test_run_registers_valid_command_handlers(monkeypatch):
    app = MagicMock()
    builder = MagicMock()
    builder.token.return_value = builder
    builder.build.return_value = app
    monkeypatch.setattr(telegram_bot.Application, "builder", lambda: builder)

    telegram_bot.run()

    registered_handler_types = [
        type(call.args[0]).__name__ for call in app.add_handler.call_args_list
    ]
    assert registered_handler_types == [
        "CommandHandler",
        "MessageHandler",
        "CallbackQueryHandler",
    ]
    app.run_polling.assert_called_once_with(drop_pending_updates=True)
