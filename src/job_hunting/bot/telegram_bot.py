import csv
import json
import logging
import threading
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from job_hunting.config import TELEGRAM_ALLOWED_USERS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from job_hunting.tools.company_candidate_store import CompanyCandidateStore
from job_hunting.utils import company_candidates_file, scores_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PENDING_PREP_VACANCY: dict[tuple[int, int], dict[str, str]] = {}


def _authorized_ids() -> list[str]:
    authorized_ids = [str(TELEGRAM_CHAT_ID)]
    if TELEGRAM_ALLOWED_USERS:
        authorized_ids.extend([i.strip() for i in TELEGRAM_ALLOWED_USERS.split(",")])
    return authorized_ids


def _is_authorized(user_id: int | str, chat_id: int | str) -> bool:
    authorized_ids = _authorized_ids()
    return str(user_id) in authorized_ids or str(chat_id) in authorized_ids


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        logger.info("Received Telegram update without message: %s", update.update_id)
        return

    logger.info(
        "Received Telegram message update_id=%s chat_id=%s chat_type=%s user_id=%s text=%r entities=%s",
        update.update_id,
        update.effective_chat.id if update.effective_chat else None,
        update.effective_chat.type if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
        message.text,
        [(entity.type, entity.offset, entity.length) for entity in (message.entities or [])],
    )


async def log_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled Telegram bot error while processing update %s", update, exc_info=context.error)


def _update_status(vacancy_id: str, date: str, status: str) -> None:
    score_dir = scores_dir(date)
    if not score_dir.exists():
        logger.warning(f"Score directory not found: {score_dir}")
        return

    score_path = score_dir / f"{vacancy_id}.json"

    # Handle truncated ID if the exact file isn't found
    if not score_path.exists():
        matches = list(score_dir.glob(f"{vacancy_id}*.json"))
        if len(matches) == 1:
            score_path = matches[0]
            logger.info(f"Found match for truncated ID: {score_path}")
        elif len(matches) > 1:
            logger.error(f"Multiple matches found for {vacancy_id} in {score_dir}")
            return
        else:
            logger.warning(f"No match found for vacancy_id: {vacancy_id}")
            return

    data = json.loads(score_path.read_text())
    # Important: capture the FULL vacancy_id from the file if we're using a truncated one
    full_vacancy_id = data.get("vacancy_id", vacancy_id)
    data["status"] = status
    score_path.write_text(json.dumps(data, indent=2))
    return full_vacancy_id


def _parse_callback(data: str) -> tuple[str, str, str]:
    """Parse 'action:vacancy_id:date' → (action, vacancy_id, date)."""
    parts = data.split(":", 2)
    return parts[0], parts[1], parts[2]


def _resolve_company_candidate_id(
    store: CompanyCandidateStore, candidate_id_or_prefix: str
) -> tuple[str | None, str | None]:
    output_file = company_candidates_file(store.run_date)
    if not output_file.exists():
        return None, f"Could not find company candidate {candidate_id_or_prefix}"

    with output_file.open("r", newline="", encoding="utf-8-sig") as f:
        candidate_ids = [
            row.get("candidate_id", "").strip()
            for row in csv.DictReader(f)
            if row.get("candidate_id", "").strip()
        ]

    if candidate_id_or_prefix in candidate_ids:
        return candidate_id_or_prefix, None

    matches = [cid for cid in candidate_ids if cid.startswith(candidate_id_or_prefix)]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, f"Ambiguous company candidate {candidate_id_or_prefix}"
    return None, f"Could not find company candidate {candidate_id_or_prefix}"


def _handle_company_review(action: str, candidate_id: str, run_date: str) -> tuple[str, bool]:
    store = CompanyCandidateStore(run_date=run_date)
    resolved_candidate_id, resolve_error = _resolve_company_candidate_id(store, candidate_id)
    if resolve_error is not None or resolved_candidate_id is None:
        return resolve_error or f"Could not find company candidate {candidate_id}", False

    if action == "company_approve":
        status = "approved"
    elif action == "company_decline":
        status = "declined"
    else:
        return f"Unsupported company action: {action}", False

    try:
        reviewed_row = store.review_candidate(resolved_candidate_id, status=status)
    except ValueError:
        return f"Could not find company candidate {candidate_id}", False

    if action == "company_decline":
        return f"❌ Declined company: {reviewed_row.get('company', resolved_candidate_id)}", True

    appended = store.append_approved_company(reviewed_row)
    company_name = reviewed_row.get("company", resolved_candidate_id)
    if appended:
        return (
            f"✅ Approved company: {company_name} (added to approved sourced companies)",
            True,
        )
    return f"✅ Approved company: {company_name} (already approved or known)", True


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    logger.info(f"Received callback from user {user_id} in chat {chat_id}")

    if not _is_authorized(user_id, chat_id):
        logger.warning(f"Ignoring unauthorized click from user {user_id} in chat {chat_id}")
        await query.answer("You are not authorized to perform this action.", show_alert=True)
        return

    await query.answer()

    try:
        action, vacancy_id, date = _parse_callback(query.data)

        if action in {"company_approve", "company_decline"}:
            message, ok = _handle_company_review(action, vacancy_id, date)
            if not ok:
                await query.edit_message_text(f"❌ Error: {message}")
                return
            await query.edit_message_text(message)
            return

        if action == "approve":
            full_id = _update_status(vacancy_id, date, "approved")
            if not full_id:
                await query.edit_message_text(f"❌ Error: Could not find record for {vacancy_id}")
                return
            await query.edit_message_text(f"✅ Approved — starting application for {full_id}…")
            threading.Thread(
                target=_run_application_flow,
                args=(full_id, date, chat_id),
                daemon=True,
            ).start()

        elif action == "decline":
            full_id = _update_status(vacancy_id, date, "declined")
            if full_id:
                await query.edit_message_text(f"❌ Declined: {full_id}")

        elif action == "applied":
            full_id = _update_status(vacancy_id, date, "applied")
            if full_id:
                await query.edit_message_text(f"✅ Marked as applied: {full_id}")

        elif action == "not_applied":
            full_id = _update_status(vacancy_id, date, "not_applied")
            if full_id:
                await query.edit_message_text(f"📝 Noted — not applied: {full_id}")

    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.edit_message_text(f"❌ Error processing click: {str(e)}")


def _run_application_flow(
    vacancy_id: str, date: str, chat_id: int | str | None = None
) -> None:
    from job_hunting.flows.application_flow import ApplicationFlow

    try:
        ApplicationFlow(vacancy_id=vacancy_id, date=date, chat_id=chat_id).kickoff()
    except Exception as e:
        logger.error(f"ApplicationFlow failed for {vacancy_id}: {e}")


async def handle_prep_vacancy_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info("Received prep_vacancy command from user %s in chat %s", user_id, chat_id)
    if not _is_authorized(user_id, chat_id):
        logger.warning("Ignoring unauthorized prep_vacancy command from user %s in chat %s", user_id, chat_id)
        await update.effective_message.reply_text(
            "You are not authorized to use this command."
        )
        return

    key = (int(chat_id), int(user_id))
    PENDING_PREP_VACANCY.pop(key, None)
    PENDING_PREP_VACANCY[key] = {"status": "waiting_for_url"}
    await update.effective_message.reply_text("Send the vacancy URL.")
    logger.info("Waiting for prep vacancy URL from user %s in chat %s", user_id, chat_id)


async def handle_prep_vacancy_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_message or not update.effective_message.text:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = (int(chat_id), int(user_id))
    if key not in PENDING_PREP_VACANCY:
        logger.debug("Ignoring non-prep message from user %s in chat %s", user_id, chat_id)
        return

    url = update.effective_message.text.strip()
    logger.info("Received prep vacancy URL candidate from user %s in chat %s", user_id, chat_id)
    if url.startswith("/prep_vacancy"):
        await handle_prep_vacancy_command(update, context)
        return

    if not _is_http_url(url):
        await update.effective_message.reply_text("Please send a valid HTTP(S) URL.")
        return

    PENDING_PREP_VACANCY.pop(key, None)
    await update.effective_message.reply_text(f"Started preparing application for: {url}")
    threading.Thread(
        target=_run_prep_vacancy_flow,
        args=(url, int(chat_id), int(user_id)),
        daemon=True,
    ).start()


def _run_prep_vacancy_flow(url: str, chat_id: int, user_id: int) -> None:
    from job_hunting.flows.prep_vacancy_flow import PrepVacancyFlow

    try:
        PrepVacancyFlow(url=url, chat_id=chat_id, user_id=user_id).kickoff()
    except Exception as e:
        logger.error(f"PrepVacancyFlow failed for {url}: {e}")


def run() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(TypeHandler(Update, log_update), group=-1)
    app.add_handler(CommandHandler("prep_vacancy", handle_prep_vacancy_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prep_vacancy_url)
    )
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(log_error)
    logger.info("Bot started. Listening for callbacks and commands…")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
