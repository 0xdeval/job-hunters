# Prep Vacancy Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/prep_vacancy` so an authorized Telegram user can send one vacancy URL and receive generated application artifacts back in the same conversation.

**Command note:** Telegram bot command names cannot contain hyphens. `/prep_vacancy` is the single supported command.

**Architecture:** Keep normal company discovery unchanged. Add a direct-vacancy prep flow that creates the existing vacancy/score files, then calls `ApplicationFlow`. Extend Telegram bot handling with a small per `(chat_id, user_id)` pending URL state and extend the notifier so final document attachments can target the originating chat.

**Tech Stack:** Python 3.10+, CrewAI Flow/Crew, python-telegram-bot 22.x, pytest, existing local file artifacts under `data/<date>/`.

---

## File Structure

- Create `src/job_hunting/flows/prep_vacancy_flow.py`
  - Owns direct-vacancy URL preparation.
  - Finds existing vacancy records by URL.
  - Runs a direct extraction crew adapter.
  - Writes normal vacancy and score JSON files.
  - Calls `ApplicationFlow`.
  - Sends progress/failure/final notifications through an injected notifier.
- Create `tests/test_prep_vacancy_flow.py`
  - Verifies file contracts, duplicate reuse, no score gating, progress routing, and failure behavior.
- Modify `src/job_hunting/tools/telegram_notifier.py`
  - Add optional `chat_id` support to `_run()` and `_send()`.
  - Add a lightweight `send_text()` helper for progress/failure messages.
  - Keep existing default `TELEGRAM_CHAT_ID` behavior for discovery approvals and normal completions.
- Modify `tests/test_telegram_notifier.py`
  - Verify completion attachments can target a supplied chat id.
  - Verify progress text can target a supplied chat id.
- Modify `src/job_hunting/bot/telegram_bot.py`
  - Add command and message handlers.
  - Add authorization helper shared by callbacks and commands.
  - Add URL validation.
  - Add in-memory pending state keyed by `(chat_id, user_id)`.
  - Start `PrepVacancyFlow` in a background thread after a valid URL.
- Create `tests/test_telegram_bot_prep_vacancy.py`
  - Verifies direct/group command state, repeated command reset, invalid URL handling, user binding, and background flow start.
- Modify `src/job_hunting/flows/__init__.py`
  - Export `PrepVacancyFlow` if the package already follows this pattern.

## Task 1: Notifier Can Target Originating Chat

**Files:**
- Modify: `src/job_hunting/tools/telegram_notifier.py`
- Test: `tests/test_telegram_notifier.py`

- [ ] **Step 1: Write failing tests for target chat attachments and text progress**

Append these tests to `tests/test_telegram_notifier.py`:

```python
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
```

- [ ] **Step 2: Run failing notifier tests**

Run:

```bash
uv run --no-sync pytest tests/test_telegram_notifier.py::test_send_completion_message_uses_supplied_chat_id tests/test_telegram_notifier.py::test_send_text_uses_supplied_chat_id -q
```

Expected: fails because `_send()` does not accept `chat_id` and `send_text()` does not exist.

- [ ] **Step 3: Implement target chat support**

In `src/job_hunting/tools/telegram_notifier.py`, update signatures and chat selection:

```python
from typing import Literal
```

Keep the existing import and update methods:

```python
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
            self._send(message_type, company, title, url, score, vacancy_id, date, chat_id=chat_id)
        )
        return f"Telegram notification sent for {vacancy_id}"

    def send_text(self, text: str, chat_id: int | str | None = None) -> str:
        asyncio.run(self._send_text(text=text, chat_id=chat_id))
        return "Telegram message sent"

    async def _send_text(self, text: str, chat_id: int | str | None = None) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=chat_id or TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=None,
        )
```

Update `_send()` signature:

```python
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
```

Then replace every `chat_id=TELEGRAM_CHAT_ID` inside `_send()` with:

```python
chat_id=target_chat_id
```

- [ ] **Step 4: Run notifier tests**

Run:

```bash
uv run --no-sync pytest tests/test_telegram_notifier.py -q
```

Expected: all notifier tests pass.

- [ ] **Step 5: Commit notifier support**

```bash
git add src/job_hunting/tools/telegram_notifier.py tests/test_telegram_notifier.py
git commit -m "Route Telegram notifications to source chats" \
  -m "Allow completion attachments and progress messages to target the chat that started manual vacancy prep while preserving the configured default chat for existing flows." \
  -m "Constraint: /prep_vacancy must return generated files in the originating conversation." \
  -m "Rejected: Hardcode TELEGRAM_CHAT_ID for manual prep | It would send group/direct command results to the wrong chat." \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Directive: Keep chat_id optional so discovery approvals and normal completions retain current behavior." \
  -m "Tested: uv run --no-sync pytest tests/test_telegram_notifier.py -q" \
  -m "Not-tested: Live Telegram API delivery." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 2: Prep Vacancy Flow Writes Artifacts and Runs ApplicationFlow

**Files:**
- Create: `src/job_hunting/flows/prep_vacancy_flow.py`
- Modify: `src/job_hunting/flows/__init__.py`
- Test: `tests/test_prep_vacancy_flow.py`

- [ ] **Step 1: Write failing tests for new flow**

Create `tests/test_prep_vacancy_flow.py`:

```python
import json
from pathlib import Path

from job_hunting.flows import prep_vacancy_flow as prep_module
from job_hunting.flows.prep_vacancy_flow import PrepVacancyFlow, PreparedVacancy


class _Notifier:
    def __init__(self):
        self.texts: list[tuple[str, int]] = []
        self.completions: list[dict] = []

    def send_text(self, text: str, chat_id: int | str | None = None) -> str:
        self.texts.append((text, int(chat_id)))
        return "sent"

    def _run(self, **kwargs) -> str:
        self.completions.append(kwargs)
        return "completion sent"


def test_prep_vacancy_flow_writes_files_and_runs_application(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    application_calls: list[tuple[str, str]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str):
            self.vacancy_id = vacancy_id
            self.date = date

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date))
            app_dir = Path("data") / self.date / "applications" / self.vacancy_id
            app_dir.mkdir(parents=True, exist_ok=True)
            (app_dir / "qa-answers.md").write_text("answers", encoding="utf-8")
            (app_dir / "cv.pdf").write_text("cv", encoding="utf-8")
            (app_dir / "cover-letter.pdf").write_text("letter", encoding="utf-8")

    notifier = _Notifier()
    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/senior-pm",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: PreparedVacancy(
            company="Acme",
            title="Senior PM",
            description="Build product systems.",
            questions=["Why Acme?"],
            requires_cover_letter=True,
        ),
        application_flow_factory=_ApplicationFlow,
        notifier=notifier,
    )

    result = flow.kickoff()

    assert result["vacancy_id"] == "acme--senior-pm"
    vacancy = json.loads(Path("data/2026-05-13/vacancies/acme--senior-pm.json").read_text())
    assert vacancy["company"] == "Acme"
    assert vacancy["title"] == "Senior PM"
    assert vacancy["url"] == "https://acme.com/jobs/senior-pm"
    assert vacancy["questions"] == ["Why Acme?"]

    score = json.loads(Path("data/2026-05-13/scores/acme--senior-pm.json").read_text())
    assert score["score"] == 100
    assert score["status"] == "approved"
    assert score["requires_cover_letter"] is True
    assert application_calls == [("acme--senior-pm", "2026-05-13")]
    assert notifier.completions[0]["chat_id"] == 12345
    assert any("Vacancy details extracted" in text for text, _ in notifier.texts)
    assert any("CV created" in text for text, _ in notifier.texts)


def test_prep_vacancy_flow_reuses_existing_complete_record(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    vacancy_dir = Path("data/2026-05-12/vacancies")
    score_dir = Path("data/2026-05-12/scores")
    vacancy_dir.mkdir(parents=True)
    score_dir.mkdir(parents=True)
    (vacancy_dir / "acme--senior-pm.json").write_text(
        json.dumps(
            {
                "id": "acme--senior-pm",
                "company": "Acme",
                "title": "Senior PM",
                "url": "https://acme.com/jobs/senior-pm",
                "description": "Existing description",
                "questions": [],
                "scraped_at": "2026-05-12T10:00:00",
            }
        ),
        encoding="utf-8",
    )
    (score_dir / "acme--senior-pm.json").write_text(
        json.dumps(
            {
                "vacancy_id": "acme--senior-pm",
                "date": "2026-05-12",
                "company": "Acme",
                "title": "Senior PM",
                "score": 80,
                "reasoning": "Existing score",
                "status": "approved",
                "requires_cover_letter": False,
            }
        ),
        encoding="utf-8",
    )
    application_calls: list[tuple[str, str]] = []

    class _ApplicationFlow:
        def __init__(self, vacancy_id: str, date: str):
            self.vacancy_id = vacancy_id
            self.date = date

        def kickoff(self) -> None:
            application_calls.append((self.vacancy_id, self.date))

    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/senior-pm",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: (_ for _ in ()).throw(AssertionError("extractor should not run")),
        application_flow_factory=_ApplicationFlow,
        notifier=_Notifier(),
    )

    result = flow.kickoff()

    assert result["vacancy_id"] == "acme--senior-pm"
    assert result["date"] == "2026-05-12"
    assert application_calls == [("acme--senior-pm", "2026-05-12")]


def test_prep_vacancy_flow_reports_extraction_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(prep_module, "today", lambda: "2026-05-13")
    notifier = _Notifier()

    flow = PrepVacancyFlow(
        url="https://acme.com/jobs/broken",
        chat_id=12345,
        user_id=777,
        extractor=lambda url: (_ for _ in ()).throw(ValueError("could not extract title")),
        application_flow_factory=lambda *args, **kwargs: None,
        notifier=notifier,
    )

    result = flow.kickoff()

    assert result["status"] == "failed"
    assert "could not extract title" in notifier.texts[-1][0]
    assert not Path("data/2026-05-13/applications").exists()
```

- [ ] **Step 2: Run failing flow tests**

Run:

```bash
uv run --no-sync pytest tests/test_prep_vacancy_flow.py -q
```

Expected: fails because `prep_vacancy_flow.py` does not exist.

- [ ] **Step 3: Implement `PrepVacancyFlow`**

Create `src/job_hunting/flows/prep_vacancy_flow.py`:

```python
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from crewai.flow.flow import Flow, start

from job_hunting.flows.application_flow import ApplicationFlow
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import all_vacancy_files, scores_dir, today, vacancies_dir


@dataclass(frozen=True)
class PreparedVacancy:
    company: str
    title: str
    description: str
    questions: list[str]
    requires_cover_letter: bool


class Notifier(Protocol):
    def send_text(self, text: str, chat_id: int | str | None = None) -> str: ...

    def _run(self, **kwargs) -> str: ...


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def make_vacancy_id(company: str, title: str) -> str:
    return f"{_slugify(company)}--{_slugify(title)}"


def extract_direct_vacancy(url: str) -> PreparedVacancy:
    raise NotImplementedError("Direct vacancy extraction crew is added in Task 3.")


class PrepVacancyFlow(Flow):
    def __init__(
        self,
        url: str,
        chat_id: int | str,
        user_id: int | str,
        date: str | None = None,
        extractor: Callable[[str], PreparedVacancy] | None = None,
        application_flow_factory=ApplicationFlow,
        notifier: Notifier | None = None,
    ):
        super().__init__()
        self._url = url
        self._chat_id = chat_id
        self._user_id = user_id
        self._date = date
        self._extractor = extractor or extract_direct_vacancy
        self._application_flow_factory = application_flow_factory
        self._notifier = notifier or TelegramNotifierTool()

    @start()
    def run(self) -> dict:
        existing = self._find_existing_complete_record()
        if existing:
            run_date, vacancy_id, vacancy, score = existing
            self._notify(f"Reusing existing vacancy record: <b>{vacancy['company']} — {vacancy['title']}</b>")
            return self._run_application(run_date, vacancy_id, vacancy, score)

        run_date = self._date or today()
        try:
            prepared = self._extractor(self._url)
        except Exception as exc:
            self._notify(f"Failed to extract vacancy details: {type(exc).__name__}: {exc}")
            return {"status": "failed", "error": str(exc)}

        vacancy_id = make_vacancy_id(prepared.company, prepared.title)
        self._notify(f"Vacancy details extracted: <b>{prepared.company} — {prepared.title}</b>")

        vacancies_dir(run_date).mkdir(parents=True, exist_ok=True)
        scores_dir(run_date).mkdir(parents=True, exist_ok=True)

        vacancy = {
            "id": vacancy_id,
            "company": prepared.company,
            "title": prepared.title,
            "url": self._url,
            "description": prepared.description,
            "questions": prepared.questions,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        score = {
            "vacancy_id": vacancy_id,
            "date": run_date,
            "company": prepared.company,
            "title": prepared.title,
            "score": 100,
            "reasoning": "Manual prep requested by Telegram command.",
            "status": "approved",
            "requires_cover_letter": prepared.requires_cover_letter,
        }

        (vacancies_dir(run_date) / f"{vacancy_id}.json").write_text(
            json.dumps(vacancy, indent=2), encoding="utf-8"
        )
        (scores_dir(run_date) / f"{vacancy_id}.json").write_text(
            json.dumps(score, indent=2), encoding="utf-8"
        )
        return self._run_application(run_date, vacancy_id, vacancy, score)

    def _find_existing_complete_record(self):
        for vacancy_file in all_vacancy_files():
            try:
                vacancy = json.loads(vacancy_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if vacancy.get("url") != self._url:
                continue
            run_date = vacancy_file.parents[1].name
            vacancy_id = vacancy.get("id") or vacancy_file.stem
            score_file = scores_dir(run_date) / f"{vacancy_id}.json"
            if not score_file.exists():
                continue
            try:
                score = json.loads(score_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            return run_date, vacancy_id, vacancy, score
        return None

    def _run_application(self, run_date: str, vacancy_id: str, vacancy: dict, score: dict) -> dict:
        try:
            self._notify("Application generation started.")
            self._application_flow_factory(vacancy_id=vacancy_id, date=run_date).kickoff()
            self._send_artifact_progress(run_date, vacancy_id, score)
            self._notifier._run(
                message_type="completion",
                company=vacancy["company"],
                title=vacancy["title"],
                url=vacancy.get("url", self._url),
                score=score.get("score", 100),
                vacancy_id=vacancy_id,
                date=run_date,
                chat_id=self._chat_id,
            )
            return {"status": "completed", "vacancy_id": vacancy_id, "date": run_date}
        except Exception as exc:
            self._notify(f"Application generation failed for <code>{vacancy_id}</code> on <code>{run_date}</code>: {type(exc).__name__}: {exc}")
            return {"status": "failed", "vacancy_id": vacancy_id, "date": run_date, "error": str(exc)}

    def _send_artifact_progress(self, run_date: str, vacancy_id: str, score: dict) -> None:
        app_dir = Path("data") / run_date / "applications" / vacancy_id
        if (app_dir / "qa-answers.md").exists():
            self._notify("Q&amp;A answers created.")
        if (app_dir / "cv.pdf").exists() or (app_dir / "cv.tex").exists():
            self._notify("CV created.")
        if (app_dir / "cover-letter.pdf").exists() or (app_dir / "cover-letter.tex").exists():
            self._notify("Cover letter created.")
        elif not score.get("requires_cover_letter", False):
            self._notify("Cover letter not required.")

    def _notify(self, text: str) -> None:
        try:
            self._notifier.send_text(text, chat_id=self._chat_id)
        except Exception:
            return
```

Update `src/job_hunting/flows/__init__.py` if it contains exports:

```python
from job_hunting.flows.prep_vacancy_flow import PrepVacancyFlow, PreparedVacancy
```

- [ ] **Step 4: Run flow tests**

Run:

```bash
uv run --no-sync pytest tests/test_prep_vacancy_flow.py -q
```

Expected: all prep flow tests pass.

- [ ] **Step 5: Commit prep flow**

```bash
git add src/job_hunting/flows/prep_vacancy_flow.py src/job_hunting/flows/__init__.py tests/test_prep_vacancy_flow.py
git commit -m "Prepare manual vacancy artifacts from one URL" \
  -m "Add a direct prep flow that writes the normal vacancy and score files, reuses complete historical records, and then runs the existing application flow without score gating." \
  -m "Constraint: /prep_vacancy is a manual override path and must not depend on MIN_SCORE." \
  -m "Rejected: Route direct URLs through DiscoveryFlow | That flow owns company career-page discovery and coverage reporting." \
  -m "Confidence: medium" \
  -m "Scope-risk: moderate" \
  -m "Directive: Keep direct vacancy extraction isolated from normal company discovery." \
  -m "Tested: uv run --no-sync pytest tests/test_prep_vacancy_flow.py -q" \
  -m "Not-tested: Real vacancy scraping and live Telegram delivery." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 3: Direct Vacancy Extraction Crew Adapter

**Files:**
- Modify: `src/job_hunting/flows/prep_vacancy_flow.py`
- Test: `tests/test_prep_vacancy_flow.py`

- [ ] **Step 1: Add tests for extraction result parsing**

Append this test to `tests/test_prep_vacancy_flow.py`:

```python
def test_parse_direct_vacancy_result_accepts_json_payload():
    payload = json.dumps(
        {
            "company": "Acme",
            "title": "Senior PM",
            "description": "Own product strategy.",
            "questions": ["Why this role?"],
            "requires_cover_letter": False,
        }
    )

    result = prep_module.parse_direct_vacancy_result(payload)

    assert result == PreparedVacancy(
        company="Acme",
        title="Senior PM",
        description="Own product strategy.",
        questions=["Why this role?"],
        requires_cover_letter=False,
    )
```

- [ ] **Step 2: Run failing parser test**

Run:

```bash
uv run --no-sync pytest tests/test_prep_vacancy_flow.py::test_parse_direct_vacancy_result_accepts_json_payload -q
```

Expected: fails because `parse_direct_vacancy_result` does not exist.

- [ ] **Step 3: Implement parser and extraction crew**

In `src/job_hunting/flows/prep_vacancy_flow.py`, add imports:

```python
from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool

from job_hunting.config import get_llm
from job_hunting.tools import SafeSeleniumScrapingTool
```

Add:

```python
def parse_direct_vacancy_result(raw: object) -> PreparedVacancy:
    if hasattr(raw, "raw"):
        raw = raw.raw
    if not isinstance(raw, str):
        raw = str(raw)
    data = json.loads(raw)
    company = str(data.get("company", "")).strip()
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    questions = data.get("questions") or []
    if not isinstance(questions, list):
        questions = []
    if not company:
        raise ValueError("could not extract company")
    if not title:
        raise ValueError("could not extract title")
    if not description:
        raise ValueError("could not extract description")
    return PreparedVacancy(
        company=company,
        title=title,
        description=description,
        questions=[str(question).strip() for question in questions if str(question).strip()],
        requires_cover_letter=bool(data.get("requires_cover_letter", False)),
    )
```

Replace the Task 2 placeholder `extract_direct_vacancy()` with:

```python
def extract_direct_vacancy(url: str) -> PreparedVacancy:
    agent = Agent(
        role="Direct Vacancy Extractor",
        goal="Extract structured application preparation data from one vacancy URL.",
        backstory=(
            "You read one known job posting URL and return only the structured fields "
            "needed by the application generation flow."
        ),
        llm=get_llm(),
        tools=[SafeSeleniumScrapingTool()],
        verbose=True,
        allow_delegation=False,
    )
    task = Task(
        description=(
            "Scrape exactly this vacancy URL, which is already the job posting: {url}\n"
            "Do not search the broader career page and do not discover other jobs.\n"
            "Extract company, title, full job description, explicit application questions, "
            "and whether the job explicitly asks for a cover letter.\n"
            "Return strict JSON with keys: company, title, description, questions, "
            "requires_cover_letter."
        ),
        expected_output=(
            '{"company":"Acme","title":"Senior PM","description":"Full job text",'
            '"questions":["Why this role?"],"requires_cover_letter":false}'
        ),
        agent=agent,
    )
    result = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True).kickoff(
        inputs={"url": url}
    )
    return parse_direct_vacancy_result(result)
```

If `ScrapeWebsiteTool` import is unused after implementation, remove it.

- [ ] **Step 4: Run parser and flow tests**

Run:

```bash
uv run --no-sync pytest tests/test_prep_vacancy_flow.py -q
```

Expected: all prep flow tests pass.

- [ ] **Step 5: Commit extraction adapter**

```bash
git add src/job_hunting/flows/prep_vacancy_flow.py tests/test_prep_vacancy_flow.py
git commit -m "Extract one submitted vacancy URL for prep" \
  -m "Add the direct-vacancy CrewAI adapter and strict JSON parsing used by the manual prep flow." \
  -m "Constraint: The submitted URL is already the target vacancy, not a career page to search." \
  -m "Rejected: Reuse the multi-job discovery prompt | It can discover extra roles and mix in coverage behavior." \
  -m "Confidence: medium" \
  -m "Scope-risk: moderate" \
  -m "Directive: Keep parser validation strict so missing company, title, or description fails before ApplicationFlow." \
  -m "Tested: uv run --no-sync pytest tests/test_prep_vacancy_flow.py -q" \
  -m "Not-tested: Live scraping against real ATS pages." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 4: Telegram Bot Conversation Command

**Files:**
- Modify: `src/job_hunting/bot/telegram_bot.py`
- Test: `tests/test_telegram_bot_prep_vacancy.py`

- [ ] **Step 1: Write failing bot conversation tests**

Create `tests/test_telegram_bot_prep_vacancy.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

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

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {"status": "waiting_for_url"}
    assert "Send the vacancy URL" in update.message.replies[-1]


def test_repeating_prep_vacancy_resets_same_user_state(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {"status": "waiting_for_url", "old": "state"}
    update = _update("/prep_vacancy")

    import asyncio
    asyncio.run(telegram_bot.handle_prep_vacancy_command(update, SimpleNamespace()))

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {"status": "waiting_for_url"}


def test_group_url_from_different_user_is_ignored(monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CHAT_ID", "12345")
    telegram_bot.PENDING_PREP_VACANCY.clear()
    telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] = {"status": "waiting_for_url"}
    update = _update("https://acme.com/jobs/pm", chat_id=12345, user_id=888)

    import asyncio
    asyncio.run(telegram_bot.handle_prep_vacancy_url(update, SimpleNamespace()))

    assert telegram_bot.PENDING_PREP_VACANCY[(12345, 777)] == {"status": "waiting_for_url"}
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
```

- [ ] **Step 2: Run failing bot tests**

Run:

```bash
uv run --no-sync pytest tests/test_telegram_bot_prep_vacancy.py -q
```

Expected: fails because handlers and state do not exist.

- [ ] **Step 3: Implement bot handlers**

In `src/job_hunting/bot/telegram_bot.py`, update imports:

```python
from urllib.parse import urlparse
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
```

Add state and helper functions near logger setup:

```python
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
```

In `handle_callback()`, replace inline auth list building with:

```python
    if not _is_authorized(user_id, chat_id):
```

Add handlers:

```python
async def handle_prep_vacancy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not _is_authorized(user_id, chat_id):
        await update.effective_message.reply_text("You are not authorized to use this command.")
        return
    key = (int(chat_id), int(user_id))
    PENDING_PREP_VACANCY.pop(key, None)
    PENDING_PREP_VACANCY[key] = {"status": "waiting_for_url"}
    await update.effective_message.reply_text("Send the vacancy URL.")


async def handle_prep_vacancy_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = (int(chat_id), int(user_id))
    if key not in PENDING_PREP_VACANCY:
        return
    url = update.effective_message.text.strip()
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
```

Add:

```python
def _run_prep_vacancy_flow(url: str, chat_id: int, user_id: int) -> None:
    from job_hunting.flows.prep_vacancy_flow import PrepVacancyFlow
    try:
        PrepVacancyFlow(url=url, chat_id=chat_id, user_id=user_id).kickoff()
    except Exception as e:
        logger.error(f"PrepVacancyFlow failed for {url}: {e}")
```

In `run()`, register command before generic message handler:

```python
    app.add_handler(CommandHandler("prep_vacancy", handle_prep_vacancy_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prep_vacancy_url))
```

Keep `CallbackQueryHandler(handle_callback)` registered.

- [ ] **Step 4: Run bot tests**

Run:

```bash
uv run --no-sync pytest tests/test_telegram_bot_prep_vacancy.py -q
```

Expected: all bot command tests pass.

- [ ] **Step 5: Commit bot conversation**

```bash
git add src/job_hunting/bot/telegram_bot.py tests/test_telegram_bot_prep_vacancy.py
git commit -m "Collect manual vacancy URLs in Telegram" \
  -m "Add /prep_vacancy conversation handling with per-user chat state, repeated-command reset, URL validation, and background prep flow execution." \
  -m "Constraint: The command must work in private chats and authorized groups without letting another user satisfy the pending URL request." \
  -m "Rejected: Add a separate cancellation command | Repeating /prep_vacancy is the requested reset behavior." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Keep pending state keyed by chat and initiating user." \
  -m "Tested: uv run --no-sync pytest tests/test_telegram_bot_prep_vacancy.py -q" \
  -m "Not-tested: Live Telegram polling." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 5: Integration Verification and Cleanup

**Files:**
- Modify only if verification exposes defects.

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run --no-sync pytest tests/test_telegram_notifier.py tests/test_prep_vacancy_flow.py tests/test_telegram_bot_prep_vacancy.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
uv run --no-sync pytest
```

Expected: all tests pass. The current baseline is `82 passed, 3 warnings` before feature tests are added.

- [ ] **Step 3: Inspect changed files**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended files are modified.

- [ ] **Step 4: Commit any verification fixes**

If verification required fixes after Task 4, commit with:

```bash
git add <fixed-files>
git commit -m "Stabilize prep vacancy command verification" \
  -m "Resolve issues found during focused and full-suite validation for the manual vacancy prep command." \
  -m "Constraint: Final behavior must preserve document attachments in the originating Telegram conversation." \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Directive: Keep verification fixes limited to prep-vacancy behavior." \
  -m "Tested: uv run --no-sync pytest" \
  -m "Not-tested: Live Telegram API and real vacancy scraping." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Self-Review

Spec coverage:

- Telegram command and two-message conversation: Task 4.
- Direct and group chat support with `(chat_id, user_id)` binding: Task 4.
- Repeating `/prep_vacancy` clears prior state: Task 4.
- HTTP(S) URL validation: Task 4.
- Direct-vacancy flow and normal artifact files: Task 2.
- Score does not gate generation: Task 2.
- Dedicated direct-vacancy extraction path: Task 3.
- Duplicate complete URL reuse: Task 2.
- Progress messages: Task 2.
- Final file attachments to originating chat: Task 1 and Task 2.
- Focused and full verification: Task 5.

Placeholder scan:

- The plan contains no placeholder markers or unspecified test steps.
- Each implementation task includes exact files, test commands, and expected outcomes.

Type consistency:

- `PreparedVacancy`, `PrepVacancyFlow`, `parse_direct_vacancy_result`, and `make_vacancy_id` are introduced before use.
- `chat_id` remains optional in notifier methods and required for prep flow construction.
- Bot background args are `(url, chat_id, user_id)`, matching `_run_prep_vacancy_flow()`.
