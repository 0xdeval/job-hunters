# Prep Vacancy Telegram Command Design Spec

**Date:** 2026-05-13
**Status:** Pending user review

## Objective

Add a Telegram command that lets the user manually prepare application artifacts
for a single known vacancy URL.

The user should send `/prep_vacancy`, then send the vacancy URL as the next
message. The bot should scrape that vacancy, create the same local vacancy and
score artifacts that `ApplicationFlow` already expects, run the existing
application crew, and send the generated files back in the same Telegram
conversation. Telegram bot command names cannot contain hyphens, so
`/prep_vacancy` is the single supported command.

This is a manual override path. The user has already checked the vacancy
manually, so fit score must not gate artifact generation.

## Scope

In scope:

- Add `/prep_vacancy` as a Telegram command.
- Support both direct bot chats and group chats where the bot is present.
- Ask for the vacancy URL as the second message in the conversation.
- Bind pending group-chat URL requests to the initiating `chat_id` and
  `user_id`.
- Validate that the submitted URL is HTTP or HTTPS.
- Add a direct-vacancy preparation flow that writes normal vacancy and score
  JSON files.
- Reuse the existing `ApplicationFlow` after the vacancy and score files exist.
- Send interim Telegram progress messages during processing.
- Send a final Telegram message with generated application files attached.

Out of scope:

- Changing the normal discovery flow for company career pages.
- Asking Telegram users for company, title, or description as extra fields.
- Using score or `MIN_SCORE` to decide whether to generate artifacts.
- Adding a web UI for manual vacancy preparation.
- Supporting multiple simultaneous `/prep_vacancy` sessions from the same user
  in the same chat.

## Telegram Conversation

The command works in two contexts:

- Direct chat with the bot.
- Group chat where the bot is present.

Conversation flow:

1. The user sends `/prep_vacancy`.
2. The bot verifies authorization using the same user/chat rules as existing
   callback buttons.
3. The bot clears any previous pending `/prep_vacancy` state for the initiating
   `(chat_id, user_id)`.
4. The bot stores fresh pending state for the initiating `(chat_id, user_id)`.
5. The bot replies asking the same user to send the vacancy URL.
6. The bot accepts only the next URL message from that same user in that same
   chat.
7. If the URL is invalid, the bot asks for a valid HTTP(S) URL and keeps the
   pending state.
8. If the URL is valid, the bot clears the pending state, sends a processing
   started message, and launches the preparation flow in a background worker.

If the same user sends `/prep_vacancy` again in the same chat while a URL is
pending, the previous pending state is discarded and replaced with a fresh
request. The bot should then ask for the new vacancy URL.

In group chats, another user must not be able to satisfy someone else's pending
`/prep_vacancy` request by sending a URL.

## Direct Vacancy Preparation Flow

Add a new `PrepVacancyFlow` for the direct URL path.

Inputs:

- `url`
- `chat_id`
- `user_id`
- `date`, defaulting to today

Responsibilities:

1. Ensure `data/<date>/vacancies/` and `data/<date>/scores/` exist.
2. Scrape exactly the submitted vacancy URL.
3. Extract:
   - company
   - title
   - full job description
   - explicit application questions
   - whether a cover letter is requested
4. Generate a stable `vacancy_id` from company and title.
5. Write `data/<date>/vacancies/<vacancy_id>.json` using the normal vacancy
   schema:

   ```json
   {
     "id": "<vacancy_id>",
     "company": "<company>",
     "title": "<title>",
     "url": "<submitted_url>",
     "description": "<full_job_description>",
     "questions": ["<question1>"],
     "scraped_at": "<ISO8601 timestamp>"
   }
   ```

6. Write `data/<date>/scores/<vacancy_id>.json` using the normal score schema,
   with `status` set to `approved` so the existing `ApplicationFlow` contract
   remains unchanged:

   ```json
   {
     "vacancy_id": "<vacancy_id>",
     "date": "<date>",
     "company": "<company>",
     "title": "<title>",
     "score": 100,
     "reasoning": "Manual prep requested by Telegram command.",
     "status": "approved",
     "requires_cover_letter": true
   }
   ```

7. Run `ApplicationFlow(vacancy_id=<vacancy_id>, date=<date>)`.
8. Send progress and final completion messages to the originating Telegram chat.

The score value is metadata only in this flow. It must not control whether
application artifacts are generated.

## Crew Boundary

Do not alter the existing company-career-page discovery flow to support this
manual URL path. The normal `DiscoveryFlow` should remain responsible for
finding and scoring vacancies from company career pages.

The new prep flow should use a dedicated single-vacancy extraction prompt or
crew path that tells the scout: the submitted URL is already the job posting;
scrape exactly this vacancy and do not search the broader career page for other
jobs.

This avoids mixing two different responsibilities:

- Discovery: find matching roles from known company career pages.
- Prep vacancy: prepare application artifacts for one user-selected vacancy URL.

## Duplicate URL Behavior

If the submitted URL already exists in historical vacancy files:

- If both the vacancy file and corresponding score file exist, reuse the
  existing `vacancy_id` and date.
- If the existing record is incomplete, create or repair the missing artifacts
  for the current date before running `ApplicationFlow`.

Reusing complete existing records avoids duplicate local artifacts for the same
vacancy URL.

## Progress Messages

The bot should send concise progress messages to the same chat that started the
command:

- Prep started for the submitted URL.
- Vacancy details extracted: company and title.
- Application generation started.
- Q&A answers created when `qa-answers.md` exists.
- CV created when `cv.pdf` exists.
- Cover letter created when `cover-letter.pdf` exists.
- Cover letter not required when the flow skips it.

Progress messages should be best-effort. Failure to send one interim message
should be logged but should not stop artifact generation.

## Final Telegram Message

The final Telegram response must attach the generated application files in the
same conversation where `/prep_vacancy` was started.

Required attachment behavior:

- Attach the generated CV when `cv.pdf` exists.
- Attach `qa-answers.md` when it exists.
- Attach the generated cover letter when `cover-letter.pdf` exists.
- Never attach intermediate `.tex` files in Telegram completion messages.
- If no cover letter is required, do not attach a cover letter and state that it
  was not required.
- After attachments, send or update a final summary message with the company,
  title, vacancy URL, and available artifact labels.

The existing completion notification behavior already attaches application
documents for normal approvals. The prep-vacancy path may reuse that logic, but
it must allow sending to the originating chat instead of only the configured
default Telegram chat.

## Error Handling

Invalid URL:

- Send a message asking for a valid HTTP(S) URL.
- Keep waiting for the URL.
- Do not start background processing.

Unauthorized command:

- Send a short rejection message or silently ignore, matching the existing bot
  convention.
- Do not create conversation state.

Extraction failure:

- Send a failure message to the originating chat.
- Include enough detail to act on, such as "could not extract title" or
  "scraping failed".
- Do not run `ApplicationFlow`.

Application generation failure:

- Send a failure message to the originating chat with `vacancy_id` and `date`.
- Preserve any local files already created so they can be inspected.

Telegram send failure:

- Log the failure.
- Do not mark local artifact generation as failed solely because an interim
  progress message failed.
- If the final attachment send fails, log the exact document path and Telegram
  error.

## Testing

Use TDD for implementation.

Add or update tests proving:

- `/prep_vacancy` enters URL-waiting state for authorized private chats.
- `/prep_vacancy` enters URL-waiting state for authorized group chats.
- Group-chat pending state is bound to the initiating user.
- A different group member cannot satisfy the pending URL request.
- Repeating `/prep_vacancy` from the same user in the same chat clears the
  previous pending URL state and starts a fresh request.
- Invalid URLs are rejected without starting prep.
- Valid URLs start background prep and clear conversation state.
- `PrepVacancyFlow` writes normal vacancy and score JSON files.
- `PrepVacancyFlow` does not use score or `MIN_SCORE` to gate
  `ApplicationFlow`.
- Duplicate complete vacancy URLs reuse the existing vacancy record.
- Progress notifications are sent to the originating chat.
- Final notification sends generated files as Telegram attachments.
- Final notification can target the originating chat rather than only
  `TELEGRAM_CHAT_ID`.

Verification target:

```bash
uv run pytest
```

## Acceptance Criteria

- A user can send `/prep_vacancy`, then send a vacancy URL, in either direct bot
  chat or an authorized group chat.
- The bot starts processing in the background and sends interim progress
  messages.
- The submitted URL is treated as a direct vacancy URL, not as a company career
  page to search for multiple roles.
- Normal vacancy and score files are created or reused.
- Existing `ApplicationFlow` generates the application artifacts.
- Fit score never blocks artifact generation for this command.
- The final Telegram response attaches the generated files in the same
  conversation that started the command.
- The implementation is covered by focused tests and the full test suite passes.
