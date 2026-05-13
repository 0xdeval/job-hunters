# Company Sourcing Telegram Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `job_hunting_source_companies` send newly sourced company candidates to Telegram for approval, write approved companies to `knowledge/approved-company-candidates.csv`, and make discovery read that file alongside `knowledge/companies.csv`.

**Architecture:** Keep rich review/audit data in `data/<date>/company_candidates.csv` and keep discovery inputs lean under `knowledge/`. Add focused store methods for candidate IDs, review status updates, and approved-company appends; keep Telegram formatting in `TelegramNotifierTool`; keep callback orchestration in `telegram_bot.py`.

**Tech Stack:** Python 3.10+, CrewAI flows/tools, `python-telegram-bot`, CSV storage, `pytest`, `uv`.

---

## File Structure

- Modify `src/job_hunting/utils.py`: add `approved_company_candidates_file()` helper.
- Modify `src/job_hunting/tools/company_candidate_store.py`: expand rich candidate schema, generate stable candidate IDs, expose pending-row and review/update APIs, and append approved lean rows idempotently.
- Modify `src/job_hunting/tools/company_sourcing_tools.py`: add `description` to tool payloads and writer serialization.
- Modify `src/job_hunting/crews/company_sourcing/config/tasks.yaml`: require `description` and `candidate_id`-compatible rows from the writer task.
- Modify `src/job_hunting/tools/telegram_notifier.py`: replace summary-only company candidate notification with one HTML Telegram approval message per candidate.
- Modify `src/job_hunting/flows/company_sourcing_flow.py`: return new pending candidates and send review messages individually.
- Modify `src/job_hunting/bot/telegram_bot.py`: parse and handle company approval/decline callbacks separately from vacancy callbacks.
- Modify `src/job_hunting/flows/discovery_flow.py`: load curated plus approved sourced company CSVs and initialize coverage from the deduped list.
- Modify `src/job_hunting/tools/discovery_coverage.py`: let coverage initialization accept explicit company rows instead of only reading `knowledge/companies.csv`.
- Modify tests:
  - `tests/test_company_candidate_store.py`
  - `tests/test_company_sourcing_flow.py`
  - `tests/test_company_sourcing_tools.py`
  - `tests/test_telegram_notifier.py`
  - `tests/test_discovery_flow.py`
  - Add `tests/test_telegram_bot_company_candidates.py`

---

### Task 1: Rich Candidate Store Contract

**Files:**
- Modify: `src/job_hunting/utils.py`
- Modify: `src/job_hunting/tools/company_candidate_store.py`
- Test: `tests/test_company_candidate_store.py`

- [ ] **Step 1: Write failing tests for candidate IDs, description, new pending rows, and approved appends**

Add these tests to `tests/test_company_candidate_store.py`:

```python
from job_hunting.utils import approved_company_candidates_file


def test_store_writes_candidate_id_description_and_reviewed_at(tmp_path, monkeypatch):
    knowledge_file = tmp_path / "knowledge" / "companies.csv"
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text("Company,Career page\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    candidate = CompanyCandidate(
        company="Mercury",
        career_page="https://mercury.com/jobs",
        website="https://mercury.com",
        description="Banking platform for startups.",
        source="public_search",
        industry="FinTech",
        match_score=85,
        match_reason="Strong overlap with PM requirements",
        status="pending_review",
        discovered_at="2026-05-13T09:00:00Z",
        reviewed_at="",
    )

    written = CompanyCandidateStore(run_date="2026-05-13").write_candidates([candidate])

    assert written == 1
    rows = list(csv.DictReader(Path("data/2026-05-13/company_candidates.csv").open()))
    assert rows[0]["candidate_id"] == "mercury-a39ab75f"
    assert rows[0]["description"] == "Banking platform for startups."
    assert rows[0]["reviewed_at"] == ""


def test_store_lists_new_pending_candidates_by_candidate_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = Path("data/2026-05-13/company_candidates.csv")
    output.parent.mkdir(parents=True)
    output.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "old-id,OldCo,https://old.example/jobs,https://old.example,Old description,SaaS,search,75,Old fit,pending_review,2026-05-13T08:00:00Z,\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,AI,search,90,New fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )

    store = CompanyCandidateStore(run_date="2026-05-13")

    assert store.list_pending_candidates(exclude_ids={"old-id"}) == [
        {
            "candidate_id": "new-id",
            "company": "NewCo",
            "career_page": "https://new.example/jobs",
            "website": "https://new.example",
            "description": "New description",
            "industry": "AI",
            "source": "search",
            "match_score": "90",
            "match_reason": "New fit",
            "status": "pending_review",
            "discovered_at": "2026-05-13T09:00:00Z",
            "reviewed_at": "",
        }
    ]


def test_approve_candidate_updates_rich_row_and_appends_lean_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    knowledge = Path("knowledge")
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nCurated,https://curated.example/jobs\n",
        encoding="utf-8",
    )
    output = Path("data/2026-05-13/company_candidates.csv")
    output.parent.mkdir(parents=True)
    output.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,AI,search,90,New fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )

    store = CompanyCandidateStore(run_date="2026-05-13")
    row = store.review_candidate(
        candidate_id="new-id",
        status="approved",
        reviewed_at="2026-05-13T10:00:00+00:00",
    )
    appended = store.append_approved_company(row)

    assert appended is True
    rows = list(csv.DictReader(output.open()))
    assert rows[0]["status"] == "approved"
    assert rows[0]["reviewed_at"] == "2026-05-13T10:00:00+00:00"
    approved_rows = list(csv.DictReader(approved_company_candidates_file().open()))
    assert approved_rows == [{"Company": "NewCo", "Career page": "https://new.example/jobs"}]


def test_append_approved_company_is_idempotent_against_curated_and_approved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    knowledge = Path("knowledge")
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nCurated,https://curated.example/jobs\n",
        encoding="utf-8",
    )

    store = CompanyCandidateStore(run_date="2026-05-13")
    assert store.append_approved_company(
        {"company": "Curated", "career_page": "https://curated.example/jobs"}
    ) is False

    candidate = {"company": "NewCo", "career_page": "https://new.example/jobs"}
    assert store.append_approved_company(candidate) is True
    assert store.append_approved_company(candidate) is False

    approved_rows = list(csv.DictReader(approved_company_candidates_file().open()))
    assert approved_rows == [{"Company": "NewCo", "Career page": "https://new.example/jobs"}]


def test_decline_candidate_updates_only_rich_row(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = Path("data/2026-05-13/company_candidates.csv")
    output.parent.mkdir(parents=True)
    output.write_text(
        "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
        "new-id,NewCo,https://new.example/jobs,https://new.example,New description,AI,search,90,New fit,pending_review,2026-05-13T09:00:00Z,\n",
        encoding="utf-8",
    )

    row = CompanyCandidateStore(run_date="2026-05-13").review_candidate(
        candidate_id="new-id",
        status="declined",
        reviewed_at="2026-05-13T10:00:00+00:00",
    )

    assert row["company"] == "NewCo"
    rows = list(csv.DictReader(output.open()))
    assert rows[0]["status"] == "declined"
    assert not approved_company_candidates_file().exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py -v
```

Expected: failures mention missing `approved_company_candidates_file`, `description`, `reviewed_at`, `candidate_id`, `list_pending_candidates`, `review_candidate`, or `append_approved_company`.

- [ ] **Step 3: Implement utility and store changes**

Update `src/job_hunting/utils.py`:

```python
def approved_company_candidates_file() -> Path:
    return Path("knowledge/approved-company-candidates.csv")
```

Update `src/job_hunting/tools/company_candidate_store.py`:

```python
import hashlib
from datetime import datetime, timezone
```

Replace `FIELDNAMES` with:

```python
FIELDNAMES = [
    "candidate_id",
    "company",
    "career_page",
    "website",
    "description",
    "industry",
    "source",
    "match_score",
    "match_reason",
    "status",
    "discovered_at",
    "reviewed_at",
]

APPROVED_FIELDNAMES = ["Company", "Career page"]
```

Update `CompanyCandidate`:

```python
@dataclass(frozen=True)
class CompanyCandidate:
    company: str
    career_page: str
    website: str
    description: str
    source: str
    industry: str
    match_score: int
    match_reason: str
    status: str
    discovered_at: str
    reviewed_at: str = ""
    candidate_id: str = ""
```

Add helper functions:

```python
def normalize_url_key(url: str) -> str:
    return url.strip().rstrip("/").casefold()


def build_candidate_id(company: str, career_page: str) -> str:
    company_key = normalize_company_key(company)
    url_key = normalize_url_key(career_page)
    base = company_key.replace(" ", "-") or "company"
    digest = hashlib.sha1(f"{company_key}|{url_key}".encode("utf-8")).hexdigest()[:8]
    return f"{base[:32].strip('-')}-{digest}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
```

Update `_candidate_to_row`:

```python
    @staticmethod
    def _candidate_to_row(candidate: CompanyCandidate) -> dict[str, str]:
        candidate_id = candidate.candidate_id or build_candidate_id(
            candidate.company,
            candidate.career_page,
        )
        return {
            "candidate_id": candidate_id,
            "company": candidate.company,
            "career_page": candidate.career_page,
            "website": candidate.website,
            "description": candidate.description,
            "industry": candidate.industry,
            "source": candidate.source,
            "match_score": str(candidate.match_score),
            "match_reason": candidate.match_reason,
            "status": candidate.status,
            "discovered_at": candidate.discovered_at,
            "reviewed_at": candidate.reviewed_at,
        }
```

Add methods to `CompanyCandidateStore`:

```python
    def list_pending_candidate_ids(self) -> set[str]:
        return {
            row.get("candidate_id", "")
            for row in self._read_candidate_rows()
            if row.get("status") == "pending_review" and row.get("candidate_id")
        }

    def list_pending_candidates(
        self,
        exclude_ids: set[str] | None = None,
    ) -> list[dict[str, str]]:
        excluded = exclude_ids or set()
        return [
            row
            for row in self._read_candidate_rows()
            if row.get("status") == "pending_review"
            and row.get("candidate_id")
            and row["candidate_id"] not in excluded
        ]

    def review_candidate(
        self,
        candidate_id: str,
        status: Literal["approved", "declined"],
        reviewed_at: str | None = None,
    ) -> dict[str, str]:
        rows = self._read_candidate_rows()
        timestamp = reviewed_at or utc_now()
        for row in rows:
            if row.get("candidate_id") == candidate_id:
                row["status"] = status
                row["reviewed_at"] = timestamp
                self._write_candidate_rows(rows)
                return row
        raise ValueError(f"Company candidate not found: {candidate_id}")

    def append_approved_company(self, candidate: dict[str, str]) -> bool:
        company = (candidate.get("company") or "").strip()
        career_page = (candidate.get("career_page") or "").strip()
        if not company or not career_page:
            raise ValueError("approved company requires company and career_page")

        if self._approved_company_exists(company=company, career_page=career_page):
            return False

        approved_file = self._approved_companies_file()
        approved_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = approved_file.exists()
        with approved_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=APPROVED_FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            writer.writerow({"Company": company, "Career page": career_page})
        return True
```

Add internal CSV helpers:

```python
    def _read_candidate_rows(self) -> list[dict[str, str]]:
        output_file = company_candidates_file(self.run_date)
        if not output_file.exists():
            return []
        with output_file.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def _write_candidate_rows(self, rows: list[dict[str, str]]) -> None:
        output_file = company_candidates_file(self.run_date)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in FIELDNAMES})

    def _approved_company_exists(self, company: str, career_page: str) -> bool:
        target_company = normalize_company_key(company)
        target_url = normalize_url_key(career_page)
        for path in [self._knowledge_companies_file(), self._approved_companies_file()]:
            if not path.exists():
                continue
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_company = normalize_company_key(
                        row.get("Company") or row.get("company") or ""
                    )
                    row_url = normalize_url_key(
                        row.get("Career page") or row.get("career_page") or ""
                    )
                    if row_company == target_company or (
                        target_url and row_url == target_url
                    ):
                        return True
        return False

    @staticmethod
    def _approved_companies_file():
        from job_hunting.utils import approved_company_candidates_file

        return approved_company_candidates_file()
```

Update `_load_existing_company_keys` so it includes approved companies:

```python
        keys.update(
            self._load_company_keys_from_csv(
                self._approved_companies_file(),
                encoding="utf-8-sig",
            )
        )
```

- [ ] **Step 4: Run store tests**

Run:

```bash
uv run pytest tests/test_company_candidate_store.py -v
```

Expected: all `test_company_candidate_store.py` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/utils.py src/job_hunting/tools/company_candidate_store.py tests/test_company_candidate_store.py
git commit -m "Support reviewed company candidate storage" -m "Company sourcing needs durable Telegram callback targets, rich review rows, and idempotent approved-company appends before notification or bot callback behavior can be implemented.\n\nConstraint: Approved sourced companies must stay separate from manually curated knowledge/companies.csv.\nConfidence: high\nScope-risk: moderate\nDirective: Keep rich review state in data/<date>/company_candidates.csv and discovery-ready approved rows in knowledge/approved-company-candidates.csv.\nTested: uv run pytest tests/test_company_candidate_store.py -v\nNot-tested: Telegram callback handling and discovery integration are covered in later tasks." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 2: Sourcing Tool Schema and Prompt Contract

**Files:**
- Modify: `src/job_hunting/tools/company_sourcing_tools.py`
- Modify: `src/job_hunting/crews/company_sourcing/config/tasks.yaml`
- Test: `tests/test_company_sourcing_tools.py`

- [ ] **Step 1: Write failing tests for description passthrough**

Add to `tests/test_company_sourcing_tools.py`:

```python
import json

from job_hunting.tools.company_sourcing_tools import CompanyCandidateWriterTool


def test_company_candidate_writer_accepts_description(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("knowledge").mkdir()
    Path("knowledge/companies.csv").write_text("Company,Career page\n", encoding="utf-8")

    result = CompanyCandidateWriterTool()._run(
        run_date="2026-05-13",
        candidates=[
            {
                "company": "Acme",
                "career_page": "https://acme.example/jobs",
                "website": "https://acme.example",
                "description": "Builds workflow software for finance teams.",
                "source": "public_search",
                "industry": "FinTech",
                "match_score": 91,
                "match_reason": "Strong PM fit",
                "status": "pending_review",
                "discovered_at": "2026-05-13T09:00:00Z",
            }
        ],
    )

    assert json.loads(result)["written_count"] == 1
    rows = list(csv.DictReader(Path("data/2026-05-13/company_candidates.csv").open()))
    assert rows[0]["description"] == "Builds workflow software for finance teams."
    assert rows[0]["candidate_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_company_sourcing_tools.py::test_company_candidate_writer_accepts_description -v
```

Expected: FAIL because `description` is not part of `CompanyCandidateToolPayload` or serialized output.

- [ ] **Step 3: Implement schema updates**

In `src/job_hunting/tools/company_sourcing_tools.py`, add `description` to `CompanyCandidateToolPayload`:

```python
    description: str = Field(description="Short neutral company description for Telegram review.")
```

When returning `new_candidates`, include:

```python
                        "description": candidate.description,
```

Update `CompanyCandidateWriterToolInput` description to include `description`:

```python
                "List of company candidate objects with fields: company, career_page, website, "
                "description, source, industry, match_score, match_reason, status, discovered_at."
```

- [ ] **Step 4: Update sourcing task prompt**

In `src/job_hunting/crews/company_sourcing/config/tasks.yaml`, update the writer schema list to include:

```yaml
    - candidate_id (generated by the writer tool; do not invent this manually)
    - description
```

Clarify description in `score_company_fit_task`:

```yaml
    For each candidate, include a short neutral company description suitable for
    Telegram review. Keep match_reason separate as the profile-fit rationale.
```

- [ ] **Step 5: Run sourcing tool tests**

Run:

```bash
uv run pytest tests/test_company_sourcing_tools.py tests/test_company_candidate_store.py -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/company_sourcing_tools.py src/job_hunting/crews/company_sourcing/config/tasks.yaml tests/test_company_sourcing_tools.py
git commit -m "Capture company descriptions during sourcing" -m "Telegram review messages need neutral company descriptions distinct from profile-fit rationale, so the sourcing writer contract must persist that field.\n\nConstraint: Candidate IDs are generated by storage code, not invented by the LLM task.\nConfidence: high\nScope-risk: narrow\nDirective: Keep description user-facing and match_reason fit-focused.\nTested: uv run pytest tests/test_company_sourcing_tools.py tests/test_company_candidate_store.py -v\nNot-tested: Live CrewAI sourcing output." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 3: Telegram Candidate Review Messages

**Files:**
- Modify: `src/job_hunting/tools/telegram_notifier.py`
- Modify: `tests/test_telegram_notifier.py`

- [ ] **Step 1: Replace summary-message test with per-candidate message tests**

In `tests/test_telegram_notifier.py`, replace `test_send_company_candidates_message_has_no_inline_keyboard` with:

```python
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


def test_build_company_link_line_handles_missing_url():
    assert TelegramNotifierTool._build_company_link_line("Website", "") == "Website unavailable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_telegram_notifier.py -v
```

Expected: FAIL because `send_company_candidate_review` and `_build_company_link_line` do not exist.

- [ ] **Step 3: Implement company candidate message method**

In `src/job_hunting/tools/telegram_notifier.py`, add:

```python
    def send_company_candidate_review(self, run_date: str, candidate: dict[str, str]) -> str:
        asyncio.run(self._send_company_candidate_review(run_date, candidate))
        return (
            "Company candidate review notification sent for "
            f"{candidate.get('candidate_id', '')}"
        )

    async def _send_company_candidate_review(
        self,
        run_date: str,
        candidate: dict[str, str],
    ) -> None:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        candidate_id = candidate["candidate_id"]
        safe_company = escape(candidate.get("company", ""))
        safe_description = escape(candidate.get("description", ""))
        safe_industry = escape(candidate.get("industry", ""))
        website_line = self._build_company_link_line(
            "Website",
            candidate.get("website", ""),
        )
        career_line = self._build_company_link_line(
            "Careers",
            candidate.get("career_page", ""),
        )
        text = (
            "<b>New company candidate</b>\n"
            f"Company: <b>{safe_company}</b>\n"
            f"{website_line}\n"
            f"{career_line}\n"
            f"Industry: <b>{safe_industry}</b>\n"
            f"Description: {safe_description}"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Approve",
                        callback_data=f"company_approve:{candidate_id}:{run_date}",
                    ),
                    InlineKeyboardButton(
                        "Decline",
                        callback_data=f"company_decline:{candidate_id}:{run_date}",
                    ),
                ]
            ]
        )
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @staticmethod
    def _build_company_link_line(label: str, url: str) -> str:
        if not url:
            return f"{escape(label)} unavailable"
        return f"{escape(label)}: <a href=\"{escape(url, quote=True)}\">Open {escape(label.lower())}</a>"
```

Keep `send_company_candidates_review` temporarily if tests or code still reference it, or remove it after Task 4 updates the flow tests.

- [ ] **Step 4: Run notifier tests**

Run:

```bash
uv run pytest tests/test_telegram_notifier.py -v
```

Expected: all notifier tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/tools/telegram_notifier.py tests/test_telegram_notifier.py
git commit -m "Send Telegram review cards for company candidates" -m "Company candidates need clickable HTML review messages with compact callback data so approvals can happen from Telegram instead of manual CSV edits.\n\nConstraint: Telegram callback data must not contain raw names or URLs.\nConfidence: high\nScope-risk: narrow\nDirective: Escape all candidate text and URL attributes before sending HTML messages.\nTested: uv run pytest tests/test_telegram_notifier.py -v\nNot-tested: Live Telegram delivery." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 4: Company Sourcing Flow Sends Only New Pending Candidates

**Files:**
- Modify: `src/job_hunting/flows/company_sourcing_flow.py`
- Modify: `tests/test_company_sourcing_flow.py`

- [ ] **Step 1: Update flow tests for candidate lists and per-candidate sends**

In `tests/test_company_sourcing_flow.py`, update `test_run_company_sourcing_crew_and_notify` so the expected result contains `candidates`:

```python
    assert result == {
        "run_date": "2026-05-11",
        "candidate_count": 2,
        "path": output,
        "candidates": [
            {
                "candidate_id": "acme-id",
                "company": "Acme",
                "career_page": "https://acme.com/careers",
                "website": "https://acme.com",
                "description": "Builds tools for operators.",
                "industry": "FinTech",
                "source": "public_search",
                "match_score": "85",
                "match_reason": "Strong fit",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
                "reviewed_at": "",
            },
            {
                "candidate_id": "gamma-id",
                "company": "Gamma",
                "career_page": "https://gamma.com/jobs",
                "website": "https://gamma.com",
                "description": "Builds AI tools.",
                "industry": "AI",
                "source": "public_search",
                "match_score": "92",
                "match_reason": "Excellent fit",
                "status": "pending_review",
                "discovered_at": "2026-05-11T09:00:00Z",
                "reviewed_at": "",
            },
        ],
    }
```

Make `_write_candidates` write the new header:

```python
        output.write_text(
            "candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at\n"
            "acme-id,Acme,https://acme.com/careers,https://acme.com,Builds tools for operators.,FinTech,public_search,85,Strong fit,pending_review,2026-05-11T09:00:00Z,\n"
            "beta-id,Beta,https://beta.com/careers,https://beta.com,Builds beta tools.,SaaS,public_search,70,Weak fit,skipped,2026-05-11T09:00:00Z,\n"
            "gamma-id,Gamma,https://gamma.com/jobs,https://gamma.com,Builds AI tools.,AI,public_search,92,Excellent fit,pending_review,2026-05-11T09:00:00Z,\n",
            encoding="utf-8",
        )
```

Update notifier assertion:

```python
    assert notifier.send_company_candidate_review.call_count == 2
    notifier.send_company_candidate_review.assert_any_call(
        run_date="2026-05-11",
        candidate=result["candidates"][0],
    )
    notifier.send_company_candidate_review.assert_any_call(
        run_date="2026-05-11",
        candidate=result["candidates"][1],
    )
```

Update no-op tests to expect `candidates: []`.

- [ ] **Step 2: Run flow tests to verify they fail**

Run:

```bash
uv run pytest tests/test_company_sourcing_flow.py -v
```

Expected: FAIL because the flow returns no `candidates` and calls the summary notification method.

- [ ] **Step 3: Implement flow changes**

Update imports:

```python
from job_hunting.tools.company_candidate_store import CompanyCandidateStore
```

Update `run_company_sourcing_crew`:

```python
        store = CompanyCandidateStore(run_date=run_date)
        pending_before = store.list_pending_candidate_ids()

        CompanySourcingCrew().crew().kickoff(inputs={"today": run_date})
        if not output.exists():
            raise FileNotFoundError(
                f"Company sourcing completed without creating expected output: {output}"
            )

        candidates = store.list_pending_candidates(exclude_ids=pending_before)
        return {
            "run_date": run_date,
            "candidate_count": len(candidates),
            "path": output,
            "candidates": candidates,
        }
```

Replace `send_review_notification` body:

```python
        if result["candidate_count"] <= 0:
            print("No company candidates pending review.")
            return

        notifier = TelegramNotifierTool()
        for candidate in result["candidates"]:
            notifier.send_company_candidate_review(
                run_date=result["run_date"],
                candidate=candidate,
            )
```

Remove `_count_pending_candidates` if no tests still cover it. If keeping it for compatibility, mark it as unused and update it to read the new schema.

- [ ] **Step 4: Run flow and notifier tests**

Run:

```bash
uv run pytest tests/test_company_sourcing_flow.py tests/test_telegram_notifier.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/flows/company_sourcing_flow.py tests/test_company_sourcing_flow.py
git commit -m "Notify only new company candidates" -m "The sourcing flow should send Telegram review cards for newly written pending candidates without resending older pending rows from the same daily CSV.\n\nConstraint: Existing pending candidates must not be spammed on every sourcing run.\nConfidence: high\nScope-risk: narrow\nDirective: Compare candidate IDs before and after crew execution, not just pending counts.\nTested: uv run pytest tests/test_company_sourcing_flow.py tests/test_telegram_notifier.py -v\nNot-tested: Live Telegram rate limits." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 5: Telegram Bot Company Callback Handling

**Files:**
- Modify: `src/job_hunting/bot/telegram_bot.py`
- Add: `tests/test_telegram_bot_company_candidates.py`

- [ ] **Step 1: Add callback handler tests**

Create `tests/test_telegram_bot_company_candidates.py`:

```python
import asyncio
import csv
from pathlib import Path
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
    approved_rows = list(csv.DictReader(Path("knowledge/approved-company-candidates.csv").open()))
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_telegram_bot_company_candidates.py -v
```

Expected: FAIL because `company_approve` and `company_decline` are parsed as vacancy actions.

- [ ] **Step 3: Implement callback parsing and handlers**

In `src/job_hunting/bot/telegram_bot.py`, add imports:

```python
from job_hunting.tools.company_candidate_store import CompanyCandidateStore
```

Add helper:

```python
def _handle_company_review(action: str, candidate_id: str, run_date: str) -> tuple[str, bool]:
    store = CompanyCandidateStore(run_date=run_date)
    if action == "company_approve":
        row = store.review_candidate(candidate_id=candidate_id, status="approved")
        appended = store.append_approved_company(row)
        suffix = "added to approved sourced companies" if appended else "already approved or known"
        return f"Approved company: {row['company']} ({suffix})", True
    if action == "company_decline":
        row = store.review_candidate(candidate_id=candidate_id, status="declined")
        return f"Declined company: {row['company']}", True
    return f"Unsupported company action: {action}", False
```

In `handle_callback`, after parsing action:

```python
        if action in {"company_approve", "company_decline"}:
            try:
                message, _ = _handle_company_review(action, vacancy_id, date)
            except ValueError:
                await query.edit_message_text(
                    f"Error: Could not find company candidate {vacancy_id}"
                )
                return
            await query.edit_message_text(message)
            return
```

The existing `_parse_callback` can keep returning `(action, id, date)`; the local variable name `vacancy_id` can be renamed to `target_id` to avoid confusion.

- [ ] **Step 4: Run callback and existing bot-related tests**

Run:

```bash
uv run pytest tests/test_telegram_bot_company_candidates.py tests/test_telegram_notifier.py tests/test_discovery_flow.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/bot/telegram_bot.py tests/test_telegram_bot_company_candidates.py
git commit -m "Handle company candidate Telegram callbacks" -m "Telegram review buttons need to update rich candidate status and append approved companies to the separate discovery input file without affecting vacancy approval behavior.\n\nConstraint: Existing vacancy callback actions must continue to start application generation only for approved vacancies.\nConfidence: high\nScope-risk: moderate\nDirective: Keep company callback actions namespaced with company_ to avoid colliding with vacancy actions.\nTested: uv run pytest tests/test_telegram_bot_company_candidates.py tests/test_telegram_notifier.py tests/test_discovery_flow.py -v\nNot-tested: Live Telegram polling." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 6: Discovery Loads Curated and Approved Sourced Companies

**Files:**
- Modify: `src/job_hunting/flows/discovery_flow.py`
- Modify: `src/job_hunting/tools/discovery_coverage.py`
- Modify: `tests/test_discovery_flow.py`

- [ ] **Step 1: Add discovery input tests**

Add to `tests/test_discovery_flow.py`:

```python
def test_run_discovery_crew_loads_curated_and_approved_sourced_companies(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\n"
        "Acme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    (knowledge / "approved-company-candidates.csv").write_text(
        "Company,Career page\n"
        "Beta,https://beta.com/jobs\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-13")
    kickoff_inputs = []

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            kickoff_inputs.append(inputs)

    DiscoveryFlow(crew_factory=lambda: _Crew()).run_discovery_crew()

    assert kickoff_inputs == [
        {"today": "2026-05-13", "company": "Acme", "career_page": "https://acme.com/careers"},
        {"today": "2026-05-13", "company": "Beta", "career_page": "https://beta.com/jobs"},
    ]
    rows = _read_coverage_rows(Path("data/2026-05-13/discovery_coverage.csv"))
    assert [row["company"] for row in rows] == ["Acme", "Beta"]


def test_run_discovery_crew_accepts_missing_approved_sourced_file(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nAcme,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-13")
    kickoff_inputs = []

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            kickoff_inputs.append(inputs)

    DiscoveryFlow(crew_factory=lambda: _Crew()).run_discovery_crew()

    assert kickoff_inputs == [
        {"today": "2026-05-13", "company": "Acme", "career_page": "https://acme.com/careers"}
    ]


def test_run_discovery_crew_dedupes_curated_and_approved_sourced_companies(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "companies.csv").write_text(
        "Company,Career page\nAcme,https://acme.com/careers/\n",
        encoding="utf-8",
    )
    (knowledge / "approved-company-candidates.csv").write_text(
        "Company,Career page\nAcme Inc.,https://acme.com/careers\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(discovery_flow_module, "today", lambda: "2026-05-13")
    kickoff_inputs = []

    class _Crew:
        def kickoff(self, inputs: dict[str, str]) -> None:
            kickoff_inputs.append(inputs)

    DiscoveryFlow(crew_factory=lambda: _Crew()).run_discovery_crew()

    assert kickoff_inputs == [
        {"today": "2026-05-13", "company": "Acme", "career_page": "https://acme.com/careers/"}
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_discovery_flow.py -v
```

Expected: FAIL because discovery reads only `knowledge/companies.csv`.

- [ ] **Step 3: Implement discovery loading and coverage initialization**

In `src/job_hunting/tools/discovery_coverage.py`, change `initialize_from_companies` signature:

```python
    def initialize_from_companies(
        self,
        companies_path: Path = Path("knowledge/companies.csv"),
        companies: list[tuple[str, str]] | None = None,
    ) -> Path:
```

At the start of the method:

```python
        source_rows = companies if companies is not None else self._load_companies(companies_path)
        rows = [
            {
                "company": company,
                "career_page": career_page,
                "status": "not_attempted",
                "jobs_found": "0",
                "matched_jobs": "0",
                "notes": "",
                "scraped_at": "",
            }
            for company, career_page in source_rows
            if company.strip() or career_page.strip()
        ]
```

Move the old CSV loading logic into:

```python
    @staticmethod
    def _load_companies(companies_path: Path) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        if companies_path.exists():
            with companies_path.open(newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    company = (row.get("Company") or row.get("company") or "").strip()
                    career_page = (
                        row.get("Career page") or row.get("career_page") or ""
                    ).strip()
                    if company or career_page:
                        rows.append((company, career_page))
        return rows
```

In `src/job_hunting/flows/discovery_flow.py`, import helpers:

```python
from job_hunting.tools.company_candidate_store import normalize_company_key, normalize_url_key
from job_hunting.utils import approved_company_candidates_file
```

Update `run_discovery_crew` ordering:

```python
        companies = self._load_companies()
        coverage_store.initialize_from_companies(companies=companies)
```

Replace `_load_companies` with:

```python
    @staticmethod
    def _load_companies(
        companies_paths: list[str | Path] | None = None,
    ) -> list[tuple[str, str]]:
        paths = companies_paths or [
            Path("knowledge/companies.csv"),
            approved_company_candidates_file(),
        ]
        rows: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for path in paths:
            path = Path(path)
            try:
                with path.open(newline="", encoding="utf-8-sig") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        company = (row.get("Company") or row.get("company") or "").strip()
                        career_page = (
                            row.get("Career page") or row.get("career_page") or ""
                        ).strip()
                        if not company and not career_page:
                            continue
                        key = (normalize_company_key(company), normalize_url_key(career_page))
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append((company, career_page))
            except FileNotFoundError:
                continue
        return rows
```

- [ ] **Step 4: Run discovery tests**

Run:

```bash
uv run pytest tests/test_discovery_flow.py tests/test_company_candidate_store.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/flows/discovery_flow.py src/job_hunting/tools/discovery_coverage.py tests/test_discovery_flow.py
git commit -m "Load approved sourced companies during discovery" -m "Discovery must process Telegram-approved sourced companies alongside manually curated companies while keeping coverage deterministic and deduped.\n\nConstraint: Missing knowledge/approved-company-candidates.csv is a normal first-run state.\nConfidence: high\nScope-risk: moderate\nDirective: Initialize coverage from the exact deduped company list that discovery will attempt.\nTested: uv run pytest tests/test_discovery_flow.py tests/test_company_candidate_store.py -v\nNot-tested: Live CrewAI scraping." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 7: Full Regression and Documentation Alignment

**Files:**
- Modify: `README.md`
- Modify: `docs/setup-guide.md`
- Test: full test suite

- [ ] **Step 1: Update README command behavior**

In `README.md`, replace the company sourcing review sentence in "How To Use":

```markdown
Run company sourcing when you want to expand the company list. It searches using `knowledge/company-source-queries.yaml`, deduplicates against `knowledge/companies.csv`, `knowledge/approved-company-candidates.csv`, and prior generated candidates, writes rich review candidates to `data/<date>/company_candidates.csv`, and sends each new pending candidate to Telegram with Approve/Decline buttons. Approved candidates are appended to `knowledge/approved-company-candidates.csv` for future discovery runs.
```

Add to "Data Layout":

```markdown
- `knowledge/approved-company-candidates.csv`
```

- [ ] **Step 2: Update setup guide if it mentions manual company candidate review**

Run:

```bash
rg -n "company_candidates|approved-company|pending_review|status=approved|company sourcing" docs/setup-guide.md README.md
```

If `docs/setup-guide.md` says to manually edit `company_candidates.csv`, replace that paragraph with:

```markdown
Company sourcing sends each new candidate to Telegram for review. Click `Approve` to append the company to `knowledge/approved-company-candidates.csv`, or `Decline` to keep it out of discovery. The rich generated file under `data/<date>/company_candidates.csv` remains the audit log for sourced candidates and review decisions.
```

- [ ] **Step 3: Run focused test suite**

Run:

```bash
uv run pytest \
  tests/test_company_candidate_store.py \
  tests/test_company_sourcing_tools.py \
  tests/test_company_sourcing_flow.py \
  tests/test_telegram_notifier.py \
  tests/test_telegram_bot_company_candidates.py \
  tests/test_discovery_flow.py \
  -v
```

Expected: all selected tests pass.

- [ ] **Step 4: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

If `uv run pytest` fails because the local macOS environment cannot install or load `onnxruntime`, run the documented fallback:

```bash
uv sync --no-install-package onnxruntime
uv run --no-sync pytest
```

Expected: all tests pass under the prepared environment.

- [ ] **Step 5: Commit docs and final fixes**

```bash
git add README.md docs/setup-guide.md
git commit -m "Document Telegram company approval workflow" -m "User-facing setup docs should match the new review path where Telegram approvals produce the separate approved sourced company input for discovery.\n\nConstraint: knowledge/companies.csv remains manually curated.\nConfidence: high\nScope-risk: narrow\nDirective: Keep docs clear that data/<date>/company_candidates.csv is an audit log, not the discovery input.\nTested: uv run pytest\nNot-tested: Live Telegram bot interaction." -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

If `docs/setup-guide.md` did not need changes, omit it from `git add`. If no documentation files changed after inspection, skip this commit and include that fact in the final implementation report.

---

## Final Verification

- [ ] Run:

```bash
git status --short
```

Expected: clean worktree.

- [ ] Run:

```bash
git log --oneline -7
```

Expected: one commit per completed task, with the latest commit documenting docs or final verification if documentation changed.

- [ ] Confirm acceptance criteria:

```text
job_hunting_source_companies sends Telegram review cards for new pending candidates.
Telegram company messages use HTML parse mode and clickable links.
Company approval updates rich candidate status and appends lean approved rows.
Company decline updates rich candidate status only.
Discovery reads knowledge/companies.csv and knowledge/approved-company-candidates.csv.
Discovery dedupes overlapping company/career-page rows.
Full test suite passes or the environment-specific test blocker is documented.
```
