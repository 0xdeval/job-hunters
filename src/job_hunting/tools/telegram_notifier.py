import asyncio
import json
from html import escape
from pathlib import Path
from typing import Literal
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from job_hunting.application_artifacts import artifact_filename_candidates
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
        chat_id: int | str | None = None,
    ) -> str:
        asyncio.run(
            self._send(
                message_type,
                company,
                title,
                url,
                score,
                vacancy_id,
                date,
                chat_id=chat_id,
            )
        )
        return f"Telegram notification sent for {vacancy_id}"

    def send_text(self, text: str, chat_id: int | str | None = None) -> str:
        asyncio.run(self._send_text(text=text, chat_id=chat_id))
        return "Telegram message sent"

    def send_company_candidates_review(self, run_date: str, candidate_count: int, path: Path) -> str:
        asyncio.run(self._send_company_candidates_review(run_date, candidate_count, path))
        return f"Company candidates review notification sent for {run_date}"

    def send_company_candidate_review(self, run_date: str, candidate: dict[str, str]) -> str:
        asyncio.run(self._send_company_candidate_review(run_date, candidate))
        candidate_id = candidate.get("candidate_id", "")
        return f"Company candidate review notification sent for {candidate_id}"

    async def _send_text(self, text: str, chat_id: int | str | None = None) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=chat_id or TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )

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

    async def _send_company_candidate_review(self, run_date: str, candidate: dict[str, str]) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        candidate_id = candidate.get("candidate_id", "")
        safe_company = escape(candidate.get("company", ""))
        safe_description = escape(candidate.get("description", ""))
        safe_industry = escape(candidate.get("industry", ""))
        website_line = self._build_company_link_line("Website", candidate.get("website", ""))
        careers_line = self._build_company_link_line("Careers", candidate.get("career_page", ""))
        text = (
            "<b>New company candidate</b>\n"
            f"Company: <b>{safe_company}</b>\n"
            f"{website_line}\n"
            f"{careers_line}\n"
            f"Industry: <b>{safe_industry}</b>\n"
            f"Description: {safe_description}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Approve",
                    callback_data=self._build_company_callback_data(
                        "company_approve", candidate_id, run_date
                    ),
                ),
                InlineKeyboardButton(
                    "Decline",
                    callback_data=self._build_company_callback_data(
                        "company_decline", candidate_id, run_date
                    ),
                ),
            ]
        ])
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
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
        chat_id: int | str | None = None,
    ) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        target_chat_id = chat_id or TELEGRAM_CHAT_ID

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
            docs = self._collect_application_documents(
                date=date,
                vacancy_id=vacancy_id,
                company=company,
                title=title,
            )
            for _, label, doc_path in docs:
                await bot.send_document(
                    chat_id=target_chat_id,
                    document=doc_path,
                    caption=f"{label}: <code>{escape(doc_path.name)}</code>",
                    parse_mode="HTML",
                )

            attached_files = ", ".join(label for _, label, _ in docs) if docs else "none found"
            text = (
                "📋 Here are all necessary files for applying to "
                f"<b>{safe_company} — {safe_title}</b>\n"
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
            chat_id=target_chat_id,
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
    def _build_company_link_line(label: str, url: str) -> str:
        safe_label = escape(label)
        if not url:
            return f"{safe_label} unavailable"
        return (
            f"{safe_label}: "
            f"<a href=\"{escape(url, quote=True)}\">Open {safe_label.lower()}</a>"
        )

    @staticmethod
    def _build_company_callback_data(action: str, candidate_id: str, run_date: str) -> str:
        callback_data = f"{action}:{candidate_id}:{run_date}"
        if len(callback_data.encode("utf-8")) <= 64:
            return callback_data
        max_id_len = 64 - len(action) - 12
        return f"{action}:{candidate_id[:max_id_len]}:{run_date}"

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
    def _collect_application_documents(
        date: str, vacancy_id: str, company: str, title: str
    ) -> list[tuple[str, str, Path]]:
        app_dir = applications_dir(date, vacancy_id)
        if not app_dir.exists():
            return []

        docs: list[tuple[str, str, Path]] = []
        required_patterns = [
            (
                "cv",
                "CV",
                artifact_filename_candidates(
                    company, title, "CV", [".pdf", ".tex"], ["cv.pdf", "cv.tex"]
                ),
            ),
            (
                "qa",
                "Q&A",
                artifact_filename_candidates(
                    company, title, "QA", [".md"], ["qa-answers.md"]
                ),
            ),
        ]
        optional_patterns = [
            (
                "cover_letter",
                "Cover letter",
                artifact_filename_candidates(
                    company,
                    title,
                    "CoverLetter",
                    [".pdf", ".tex"],
                    ["cover-letter.pdf", "cover-letter.tex"],
                ),
            ),
        ]

        for key, label, candidates in required_patterns + optional_patterns:
            for candidate in candidates:
                path = app_dir / candidate
                if path.exists():
                    docs.append((key, label, path))
                    break

        return docs
