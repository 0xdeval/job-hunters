import asyncio
import json
from html import escape
from pathlib import Path
from typing import Literal
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from job_hunting.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from job_hunting.utils import applications_dir, vacancies_dir


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

    def send_company_candidates_review(self, run_date: str, candidate_count: int, path: Path) -> str:
        asyncio.run(self._send_company_candidates_review(run_date, candidate_count, path))
        return f"Company candidates review notification sent for {run_date}"

    async def _send_company_candidates_review(
        self, run_date: str, candidate_count: int, path: Path
    ) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        text = (
            f"🏢 <b>Company candidates ready for review ({escape(run_date)})</b>\n"
            f"📊 Candidates: <b>{candidate_count}</b>\n"
            f"📄 CSV: <code>{escape(str(path))}</code>\n"
            "✅ Set <code>status=approved</code> for companies discovery should monitor."
        )
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )

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
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        def get_safe_cb(action, v_id, d):
            cb = f"{action}:{v_id}:{d}"
            if len(cb.encode("utf-8")) > 64:
                # truncate ID to fit: 64 - len(action) - 2 (:) - 10 (date)
                max_id_len = 64 - len(action) - 12
                return f"{action}:{v_id[:max_id_len]}:{d}"
            return cb

        if message_type == "approval":
            resolved_url = self._resolve_vacancy_url(url=url, date=date, vacancy_id=vacancy_id)
            safe_company = escape(company)
            safe_title = escape(title)
            text = (
                f"🔍 <b>New vacancy — {safe_company}</b>\n"
                f"📌 {safe_title}\n"
                f"🔗 {self._build_vacancy_link_line(resolved_url)}\n"
                f"⭐ Fit score: <b>{score}/100</b>"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=get_safe_cb("approve", vacancy_id, date)),
                    InlineKeyboardButton("❌ Decline", callback_data=get_safe_cb("decline", vacancy_id, date)),
                ]
            ])
        else:
            resolved_url = self._resolve_vacancy_url(url=url, date=date, vacancy_id=vacancy_id)
            safe_company = escape(company)
            safe_title = escape(title)
            docs = self._collect_application_documents(date=date, vacancy_id=vacancy_id)
            for _, label, doc_path in docs:
                await bot.send_document(
                    chat_id=TELEGRAM_CHAT_ID,
                    document=doc_path,
                    caption=f"{label}: <code>{escape(doc_path.name)}</code>",
                    parse_mode="HTML",
                )

            attached_files = ", ".join(label for _, label, _ in docs) if docs else "none found"
            text = (
                f"📋 <b>{safe_company} — {safe_title}</b>\n"
                f"🔗 {self._build_vacancy_link_line(resolved_url)}\n"
                f"📎 Attached files: <b>{escape(attached_files)}</b>"
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

    @staticmethod
    def _build_vacancy_link_line(url: str) -> str:
        if not url:
            return "Vacancy URL unavailable"
        return f"<a href=\"{escape(url, quote=True)}\">Open vacancy</a>"

    @staticmethod
    def _resolve_vacancy_url(url: str, date: str, vacancy_id: str) -> str:
        if url:
            return url
        vacancy_file = vacancies_dir(date) / f"{vacancy_id}.json"
        try:
            data = json.loads(vacancy_file.read_text())
        except (OSError, json.JSONDecodeError):
            return ""
        return data.get("url", "")

    @staticmethod
    def _collect_application_documents(date: str, vacancy_id: str) -> list[tuple[str, str, Path]]:
        app_dir = applications_dir(date, vacancy_id)
        if not app_dir.exists():
            return []

        docs: list[tuple[str, str, Path]] = []
        required_patterns = [
            ("cv", "CV", ["cv.pdf", "cv.tex"]),
            ("qa", "Q&A", ["qa-answers.md"]),
        ]
        optional_patterns = [
            ("cover_letter", "Cover letter", ["cover-letter.pdf", "cover-letter.tex"]),
        ]

        for key, label, candidates in required_patterns + optional_patterns:
            for candidate in candidates:
                path = app_dir / candidate
                if path.exists():
                    docs.append((key, label, path))
                    break

        return docs
