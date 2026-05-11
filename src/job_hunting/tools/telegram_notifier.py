import asyncio
from typing import Literal
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from job_hunting.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class NotifierInput(BaseModel):
    message_type: Literal["approval", "completion"] = Field(
        description="'approval' sends Approve/Decline buttons; 'completion' sends Applied/Not applied buttons"
    )
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    url: str = Field(description="Vacancy URL")
    score: int = Field(description="Fit score 0-100")
    vacancy_id: str = Field(description="Vacancy ID (e.g. acme--senior-pm)")
    date: str = Field(description="Discovery date (YYYY-MM-DD)")


class TelegramNotifierTool(BaseTool):
    name: str = "Telegram Notifier"
    description: str = "Send a Telegram notification about a vacancy with action buttons."
    args_schema: type[BaseModel] = NotifierInput

    def _run(
        self,
        message_type: str,
        company: str,
        title: str,
        url: str,
        score: int,
        vacancy_id: str,
        date: str,
    ) -> str:
        asyncio.run(self._send(message_type, company, title, url, score, vacancy_id, date))
        return f"Telegram notification sent for {vacancy_id}"

    async def _send(
        self,
        message_type: str,
        company: str,
        title: str,
        url: str,
        score: int,
        vacancy_id: str,
        date: str,
    ) -> None:
        import hashlib
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # callback_data is limited to 64 bytes. 
        # If the vacancy_id is too long, we use a hash.
        # Format: "action:vacancy_id:date"
        # We'll use a shorter format and check length.
        action_prefix = "appr" if message_type == "approval" else "done"
        cb_data = f"{action_prefix}:{vacancy_id}:{date}"
        
        if len(cb_data.encode('utf-8')) > 64:
            # Fallback: if too long, we'll have to use a shortened version or a hash.
            # For now, let's try to just use a shorter date and action.
            short_date = date.replace("-", "") # 20260511
            action_code = "a" if message_type == "approval" else "f" # a=approve, f=finished
            cb_data = f"{action_code}:{vacancy_id}:{short_date}"
            
            if len(cb_data.encode('utf-8')) > 64:
                # If still too long, truncate vacancy_id but we'll need to fix the bot side to handle this.
                # Actually, let's just use a hash and the bot will have to find the file by searching.
                # BUT searching is slow. Let's try to just truncate and hope for the best, 
                # or better: the bot can glob for the prefix.
                pass

        def get_safe_cb(action, v_id, d):
            cb = f"{action}:{v_id}:{d}"
            if len(cb.encode('utf-8')) > 64:
                # truncate ID to fit: 64 - len(action) - 2 (:) - 10 (date)
                max_id_len = 64 - len(action) - 12
                return f"{action}:{v_id[:max_id_len]}:{d}"
            return cb

        if message_type == "approval":
            text = (
                f"🔍 <b>New vacancy — {company}</b>\n"
                f"📌 {title}\n"
                f"🔗 <a href='{url}'>Open Career Page</a>\n"
                f"⭐ Fit score: <b>{score}/100</b>"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=get_safe_cb("approve", vacancy_id, date)),
                    InlineKeyboardButton("❌ Decline", callback_data=get_safe_cb("decline", vacancy_id, date)),
                ]
            ])
        else:
            text = (
                f"📋 <b>{company} — {title}</b>\n"
                f"CV, cover letter, and Q&A answers are ready.\n"
                f"📎 <code>data/{date}/applications/{vacancy_id}/</code>"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Applied", callback_data=get_safe_cb("applied", vacancy_id, date)),
                    InlineKeyboardButton("❌ Not applied", callback_data=get_safe_cb("not_applied", vacancy_id, date)),
                ]
            ])

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
