# Job Hunting Multi-Agent System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CrewAI-based multi-agent system that automates job discovery, scores vacancies, generates tailored applications (CV + cover letter + Q&A answers), and provides conversational job search assistance via Chainlit.

**Architecture:** Two CrewAI Flows (DiscoveryFlow triggered by cron, ApplicationFlow triggered by Telegram approval) orchestrate two Crews. A standalone Career Advisor agent powers a Chainlit chat UI. All runtime data is shared via JSON files in `data/{YYYY-MM-DD}/` date folders.

**Tech Stack:** Python 3.10+, CrewAI 1.9.3 with tools, python-telegram-bot 21+, Chainlit 1.0+, SeleniumScrapingTool, Node.js (fill-template.js), pdflatex (TeX Live / MacTeX)

---

## File Map

Files to create or modify:

```
src/job_hunting/
├── main.py                              MODIFY — replace with new entry points
├── config.py                            CREATE — shared LLM instance
├── models.py                            CREATE — VacancyData, ScoreData, VacancyStatus
├── utils.py                             CREATE — date-based path helpers
├── crews/
│   ├── __init__.py                      CREATE
│   ├── discovery/
│   │   ├── __init__.py                  CREATE
│   │   ├── crew.py                      CREATE
│   │   └── config/
│   │       ├── agents.yaml              CREATE
│   │       └── tasks.yaml               CREATE
│   └── application/
│       ├── __init__.py                  CREATE
│       ├── crew.py                      CREATE
│       └── config/
│           ├── agents.yaml              CREATE
│           └── tasks.yaml               CREATE
├── flows/
│   ├── __init__.py                      CREATE
│   ├── discovery_flow.py                CREATE
│   └── application_flow.py             CREATE
├── tools/
│   ├── __init__.py                      MODIFY — export new tools
│   ├── dedup_tool.py                    CREATE
│   ├── telegram_notifier.py             CREATE
│   ├── cv_generator.py                  CREATE
│   └── cover_letter_tool.py             CREATE
├── agents/
│   ├── __init__.py                      CREATE
│   └── career_advisor.py               CREATE
└── advisor/
    ├── __init__.py                      CREATE
    └── app.py                           CREATE

knowledge/
└── search-criteria.md                   CREATE — filled by user before first run

.env.example                             CREATE
pyproject.toml                           MODIFY — add deps, update entry points

tests/
├── test_models.py                       CREATE
├── test_utils.py                        CREATE
├── test_dedup_tool.py                   CREATE
├── test_telegram_notifier.py            CREATE
├── test_cv_generator.py                 CREATE
└── test_cover_letter_tool.py            CREATE
```

---

## Task 1: Initialize git and update project dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `src/job_hunting/crews/__init__.py`, `src/job_hunting/flows/__init__.py`, `src/job_hunting/agents/__init__.py`, `src/job_hunting/advisor/__init__.py`

- [ ] **Step 1: Initialize git repository**

```bash
cd /Users/admin/Documents/projects/agents-departments/job-hunting
git init
git add .gitignore 2>/dev/null || true
```

- [ ] **Step 2: Create .gitignore**

```
.env
data/
.tmp/
__pycache__/
*.pyc
.DS_Store
*.pdf
*.tex
*.aux
*.log
*.out
*.fls
*.fdb_latexmk
```

- [ ] **Step 3: Update pyproject.toml with new dependencies and entry points**

Replace the `[project.scripts]` and `dependencies` sections:

```toml
[project]
name = "job_hunting"
version = "0.1.0"
description = "job-hunting using crewAI"
authors = [{ name = "Your Name", email = "you@example.com" }]
requires-python = ">=3.10,<3.14"
dependencies = [
    "crewai[tools]==1.9.3",
    "python-telegram-bot>=21.0",
    "chainlit>=1.0",
    "python-dotenv",
]

[project.scripts]
job_hunting_discover = "job_hunting.main:run_discovery"
job_hunting_bot      = "job_hunting.main:run_bot"
job_hunting_advisor  = "job_hunting.main:run_advisor"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.crewai]
type = "flow"
```

- [ ] **Step 4: Install updated dependencies**

```bash
pip install -e ".[dev]" 2>/dev/null || pip install -e .
```

Expected: installs python-telegram-bot, chainlit, crewai[tools].

- [ ] **Step 5: Create .env.example**

```bash
cat > .env.example << 'EOF'
OPENAI_API_BASE=https://your-cliproxyapi-endpoint
OPENAI_API_KEY=your-api-key
MODEL=claude-sonnet-4-6
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
MIN_SCORE=70
EOF
```

- [ ] **Step 6: Copy .env.example to .env and fill in real values**

```bash
cp .env.example .env
# Edit .env with your real credentials
```

- [ ] **Step 7: Create package __init__ files**

```bash
mkdir -p src/job_hunting/crews/discovery/config
mkdir -p src/job_hunting/crews/application/config
mkdir -p src/job_hunting/flows
mkdir -p src/job_hunting/agents
mkdir -p src/job_hunting/advisor
mkdir -p tests

touch src/job_hunting/crews/__init__.py
touch src/job_hunting/crews/discovery/__init__.py
touch src/job_hunting/crews/application/__init__.py
touch src/job_hunting/flows/__init__.py
touch src/job_hunting/agents/__init__.py
touch src/job_hunting/advisor/__init__.py
touch tests/__init__.py
```

- [ ] **Step 8: Create initial data and knowledge directories**

```bash
mkdir -p data
mkdir -p knowledge/profile
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: project setup — deps, entry points, folder structure"
```

---

## Task 2: Shared models, utils, and LLM config

**Files:**
- Create: `src/job_hunting/models.py`
- Create: `src/job_hunting/utils.py`
- Create: `src/job_hunting/config.py`
- Create: `tests/test_models.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/test_models.py`:

```python
import json
from job_hunting.models import VacancyStatus, vacancy_id_from


def test_vacancy_status_values():
    assert VacancyStatus.PENDING_APPROVAL == "pending_approval"
    assert VacancyStatus.APPROVED == "approved"
    assert VacancyStatus.DECLINED == "declined"
    assert VacancyStatus.DOCUMENTS_READY == "documents_ready"
    assert VacancyStatus.APPLIED == "applied"
    assert VacancyStatus.NOT_APPLIED == "not_applied"
    assert VacancyStatus.SKIPPED == "skipped"


def test_vacancy_id_from():
    assert vacancy_id_from("Acme Corp", "Senior Product Manager") == "acme-corp--senior-product-manager"
    assert vacancy_id_from("Web3 Inc.", "Head of Product") == "web3-inc--head-of-product"
    assert vacancy_id_from("A & B", "PM") == "a--b--pm"
```

- [ ] **Step 2: Write failing tests for utils**

Create `tests/test_utils.py`:

```python
from pathlib import Path
from job_hunting.utils import vacancies_dir, scores_dir, applications_dir


def test_vacancies_dir():
    assert vacancies_dir("2026-05-10") == Path("data/2026-05-10/vacancies")


def test_scores_dir():
    assert scores_dir("2026-05-10") == Path("data/2026-05-10/scores")


def test_applications_dir():
    result = applications_dir("2026-05-10", "acme--senior-pm")
    assert result == Path("data/2026-05-10/applications/acme--senior-pm")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_models.py tests/test_utils.py -v
```

Expected: ImportError — modules don't exist yet.

- [ ] **Step 4: Create models.py**

Create `src/job_hunting/models.py`:

```python
import re
from enum import Enum
from typing import TypedDict


class VacancyStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DECLINED = "declined"
    DOCUMENTS_READY = "documents_ready"
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    SKIPPED = "skipped"


class VacancyData(TypedDict):
    id: str
    company: str
    title: str
    url: str
    description: str
    questions: list[str]
    scraped_at: str


class ScoreData(TypedDict):
    vacancy_id: str
    date: str
    company: str
    title: str
    score: int
    reasoning: str
    status: str
    requires_cover_letter: bool


def vacancy_id_from(company: str, title: str) -> str:
    def slugify(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s-]", "-", text)
        text = re.sub(r"[\s-]+", "-", text)
        return text.strip("-")

    return f"{slugify(company)}--{slugify(title)}"
```

- [ ] **Step 5: Create utils.py**

Create `src/job_hunting/utils.py`:

```python
from datetime import date
from pathlib import Path


def today() -> str:
    return date.today().isoformat()


def vacancies_dir(run_date: str) -> Path:
    return Path(f"data/{run_date}/vacancies")


def scores_dir(run_date: str) -> Path:
    return Path(f"data/{run_date}/scores")


def applications_dir(run_date: str, vacancy_id: str) -> Path:
    return Path(f"data/{run_date}/applications/{vacancy_id}")


def all_vacancy_files() -> list[Path]:
    return list(Path("data").glob("*/vacancies/*.json"))


def all_score_files() -> list[Path]:
    return list(Path("data").glob("*/scores/*.json"))
```

- [ ] **Step 6: Create config.py**

Create `src/job_hunting/config.py`:

```python
import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()


def get_llm() -> LLM:
    return LLM(
        model=os.environ["MODEL"],
        base_url=os.environ["OPENAI_API_BASE"],
        api_key=os.environ["OPENAI_API_KEY"],
    )


MIN_SCORE: int = int(os.getenv("MIN_SCORE", "70"))
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: int = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/test_models.py tests/test_utils.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add src/job_hunting/models.py src/job_hunting/utils.py src/job_hunting/config.py tests/
git commit -m "feat: shared models, utils, and LLM config"
```

---

## Task 3: DedupTool

**Files:**
- Create: `src/job_hunting/tools/dedup_tool.py`
- Create: `tests/test_dedup_tool.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_dedup_tool.py`:

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from job_hunting.tools.dedup_tool import DedupTool


def test_url_not_seen_returns_false(tmp_path):
    tool = DedupTool()
    with patch("job_hunting.tools.dedup_tool.all_vacancy_files", return_value=[]):
        result = tool._run(url="https://acme.com/jobs/pm")
    assert result == "new"


def test_url_already_seen_returns_duplicate(tmp_path):
    vacancy = {"url": "https://acme.com/jobs/pm", "id": "acme--pm"}
    vacancy_file = tmp_path / "acme--pm.json"
    vacancy_file.write_text(json.dumps(vacancy))

    tool = DedupTool()
    with patch(
        "job_hunting.tools.dedup_tool.all_vacancy_files",
        return_value=[vacancy_file],
    ):
        result = tool._run(url="https://acme.com/jobs/pm")
    assert result == "duplicate"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_dedup_tool.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement DedupTool**

Create `src/job_hunting/tools/dedup_tool.py`:

```python
import json
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from job_hunting.utils import all_vacancy_files


class DedupInput(BaseModel):
    url: str = Field(description="The vacancy URL to check for duplicates")


class DedupTool(BaseTool):
    name: str = "Vacancy Dedup Checker"
    description: str = (
        "Check if a vacancy URL has already been scraped in a previous run. "
        "Returns 'duplicate' if seen before, 'new' if not."
    )
    args_schema: type[BaseModel] = DedupInput

    def _run(self, url: str) -> str:
        for vacancy_file in all_vacancy_files():
            try:
                data = json.loads(vacancy_file.read_text())
                if data.get("url") == url:
                    return "duplicate"
            except (json.JSONDecodeError, OSError):
                continue
        return "new"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_dedup_tool.py -v
```

Expected: all PASS.

- [ ] **Step 5: Update tools __init__.py**

Edit `src/job_hunting/tools/__init__.py`:

```python
from job_hunting.tools.dedup_tool import DedupTool

__all__ = ["DedupTool"]
```

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/dedup_tool.py src/job_hunting/tools/__init__.py tests/test_dedup_tool.py
git commit -m "feat: DedupTool for vacancy URL deduplication"
```

---

## Task 4: TelegramNotifierTool

**Files:**
- Create: `src/job_hunting/tools/telegram_notifier.py`
- Create: `tests/test_telegram_notifier.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_telegram_notifier.py`:

```python
from unittest.mock import AsyncMock, patch, MagicMock
from job_hunting.tools.telegram_notifier import TelegramNotifierTool


def test_send_approval_message_builds_correct_payload():
    tool = TelegramNotifierTool()
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=MagicMock(message_id=42))

    with patch("job_hunting.tools.telegram_notifier.Bot", return_value=mock_bot), \
         patch("job_hunting.tools.telegram_notifier.asyncio.run") as mock_run:
        tool._run(
            message_type="approval",
            company="Acme",
            title="Senior PM",
            url="https://acme.com/jobs/pm",
            score=85,
            vacancy_id="acme--senior-pm",
            date="2026-05-10",
        )
        mock_run.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_telegram_notifier.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement TelegramNotifierTool**

Create `src/job_hunting/tools/telegram_notifier.py`:

```python
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
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        cb = f"{vacancy_id}:{date}"

        if message_type == "approval":
            text = (
                f"🔍 *New vacancy — {company}*\n"
                f"📌 {title}\n"
                f"🔗 [Open]({url})\n"
                f"⭐ Fit score: {score}/100"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve:{cb}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"decline:{cb}"),
                ]
            ])
        else:
            text = (
                f"📋 *{company} — {title}*\n"
                f"CV, cover letter, and Q&A answers are ready.\n"
                f"📎 `data/{date}/applications/{vacancy_id}/`"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Applied", callback_data=f"applied:{cb}"),
                    InlineKeyboardButton("❌ Not applied", callback_data=f"not_applied:{cb}"),
                ]
            ])

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_telegram_notifier.py -v
```

Expected: all PASS.

- [ ] **Step 5: Update tools __init__.py**

```python
from job_hunting.tools.dedup_tool import DedupTool
from job_hunting.tools.telegram_notifier import TelegramNotifierTool

__all__ = ["DedupTool", "TelegramNotifierTool"]
```

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/telegram_notifier.py src/job_hunting/tools/__init__.py tests/test_telegram_notifier.py
git commit -m "feat: TelegramNotifierTool for approval and completion messages"
```

---

## Task 5: CVGeneratorTool

**Files:**
- Create: `src/job_hunting/tools/cv_generator.py`
- Create: `tests/test_cv_generator.py`

**Prerequisites:** Node.js installed (`node --version`), `personalized-outreach/scripts/fill-template.js` exists.

- [ ] **Step 1: Write failing test**

Create `tests/test_cv_generator.py`:

```python
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from job_hunting.tools.cv_generator import CVGeneratorTool


SAMPLE_TAILORED_JSON = {
    "summary": "Experienced product manager with strong Web3 background.",
    "workExperienceIds": ["blockscout"],
    "workExperienceDescriptions": {
        "blockscout": ["Grew MAU by **300%** via product-led growth initiatives"]
    },
    "projectIds": [],
    "projectDescriptions": {},
    "skills": "Product strategy, Web3, DeFi, SQL, Python",
}


def test_cv_generator_calls_node_script(tmp_path):
    tool = CVGeneratorTool()
    output_path = tmp_path / "cv.tex"

    mock_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        tool._run(
            tailored_json=json.dumps(SAMPLE_TAILORED_JSON),
            output_tex_path=str(output_path),
        )
        assert mock_run.call_count >= 1
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "fill-template.js" in " ".join(first_call_args)


def test_cv_generator_raises_on_node_error(tmp_path):
    tool = CVGeneratorTool()
    output_path = tmp_path / "cv.tex"

    mock_result = MagicMock(returncode=1, stdout="", stderr="Error: template not found")

    with patch("subprocess.run", return_value=mock_result):
        result = tool._run(
            tailored_json=json.dumps(SAMPLE_TAILORED_JSON),
            output_tex_path=str(output_path),
        )
        assert "Error" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cv_generator.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement CVGeneratorTool**

Create `src/job_hunting/tools/cv_generator.py`:

```python
import json
import subprocess
import tempfile
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

TEMPLATE_PATH = "personalized-outreach/templates/cv-template.md"
SCRIPT_PATH = "personalized-outreach/scripts/fill-template.js"
PROFILE_DIR = "knowledge/profile/"


class CVGeneratorInput(BaseModel):
    tailored_json: str = Field(
        description="JSON string with tailored CV data: summary, workExperienceIds, "
        "workExperienceDescriptions, projectIds, projectDescriptions, skills"
    )
    output_tex_path: str = Field(description="Absolute or relative path for the output .tex file")


class CVGeneratorTool(BaseTool):
    name: str = "CV Generator"
    description: str = (
        "Generate a tailored CV PDF from the candidate's profile. "
        "Provide tailored JSON data and the output file path. "
        "Returns the path to the generated PDF, or an error message."
    )
    args_schema: type[BaseModel] = CVGeneratorInput

    def _run(self, tailored_json: str, output_tex_path: str) -> str:
        output_path = Path(output_tex_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="tailored-cv-"
        ) as f:
            f.write(tailored_json)
            json_path = f.name

        result = subprocess.run(
            ["node", SCRIPT_PATH, TEMPLATE_PATH, json_path, str(output_path), PROFILE_DIR],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"Error generating .tex: {result.stderr}"

        pdf_path = output_path.with_suffix(".pdf")
        tex_dir = str(output_path.parent)

        draft_result = subprocess.run(
            [
                "pdflatex",
                "-draftmode",
                "-interaction=nonstopmode",
                f"-output-directory={tex_dir}",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        if draft_result.returncode != 0:
            return (
                f"LaTeX validation failed. Fix the .tex file before converting to PDF.\n"
                f"Errors:\n{draft_result.stdout[-2000:]}"
            )

        compile_result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={tex_dir}",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            return f"PDF compilation failed:\n{compile_result.stdout[-2000:]}"

        return str(pdf_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cv_generator.py -v
```

Expected: all PASS.

- [ ] **Step 5: Update tools __init__.py**

```python
from job_hunting.tools.dedup_tool import DedupTool
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.tools.cv_generator import CVGeneratorTool

__all__ = ["DedupTool", "TelegramNotifierTool", "CVGeneratorTool"]
```

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/cv_generator.py src/job_hunting/tools/__init__.py tests/test_cv_generator.py
git commit -m "feat: CVGeneratorTool with LaTeX draft validation before PDF compilation"
```

---

## Task 6: CoverLetterTool

**Files:**
- Create: `src/job_hunting/tools/cover_letter_tool.py`
- Create: `tests/test_cover_letter_tool.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_cover_letter_tool.py`:

```python
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from job_hunting.tools.cover_letter_tool import CoverLetterTool


SAMPLE_TEMPLATE = r"""
\begin{document}
==INTRO==

==MAIN BODY==

==CONCLUSION==
\end{document}
"""

SAMPLE_CONTENT = {
    "intro": "I was excited to see this role at Acme.",
    "main_body": "At Blockscout, I grew MAU by 300% through product-led growth.",
    "conclusion": "I would love to discuss this further.",
}


def test_cover_letter_fills_placeholders(tmp_path):
    tool = CoverLetterTool()
    output_path = tmp_path / "cover-letter.tex"

    mock_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("builtins.open", mock_open(read_data=SAMPLE_TEMPLATE)), \
         patch("subprocess.run", return_value=mock_result), \
         patch.object(Path, "write_text"):
        tool._run(
            intro=SAMPLE_CONTENT["intro"],
            main_body=SAMPLE_CONTENT["main_body"],
            conclusion=SAMPLE_CONTENT["conclusion"],
            output_tex_path=str(output_path),
        )


def test_cover_letter_raises_on_compile_error(tmp_path):
    tool = CoverLetterTool()
    output_path = tmp_path / "cover-letter.tex"

    mock_result = MagicMock(returncode=1, stdout="LaTeX Error", stderr="")

    with patch("builtins.open", mock_open(read_data=SAMPLE_TEMPLATE)), \
         patch("subprocess.run", return_value=mock_result), \
         patch.object(Path, "write_text"):
        result = tool._run(
            intro="intro",
            main_body="body",
            conclusion="conclusion",
            output_tex_path=str(output_path),
        )
        assert "failed" in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cover_letter_tool.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement CoverLetterTool**

Create `src/job_hunting/tools/cover_letter_tool.py`:

```python
import subprocess
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

TEMPLATE_PATH = "personalized-outreach/templates/cover-letter.md"


class CoverLetterInput(BaseModel):
    intro: str = Field(description="Opening paragraph, 60-80 words")
    main_body: str = Field(description="Main body paragraphs, 150-200 words total")
    conclusion: str = Field(description="Closing paragraph, 40-60 words")
    output_tex_path: str = Field(description="Path for the output .tex file")


class CoverLetterTool(BaseTool):
    name: str = "Cover Letter Generator"
    description: str = (
        "Fill the cover letter LaTeX template with the provided content sections "
        "and compile to PDF. Returns the PDF path or an error message."
    )
    args_schema: type[BaseModel] = CoverLetterInput

    def _run(self, intro: str, main_body: str, conclusion: str, output_tex_path: str) -> str:
        output_path = Path(output_tex_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = Path(TEMPLATE_PATH).read_text()
        filled = (
            template
            .replace("==INTRO==", intro)
            .replace("==MAIN BODY==", main_body)
            .replace("==CONCLUSION==", conclusion)
        )
        output_path.write_text(filled)

        tex_dir = str(output_path.parent)

        draft = subprocess.run(
            [
                "pdflatex",
                "-draftmode",
                "-interaction=nonstopmode",
                f"-output-directory={tex_dir}",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        if draft.returncode != 0:
            return (
                f"LaTeX validation failed. Fix the cover letter before converting to PDF.\n"
                f"Errors:\n{draft.stdout[-2000:]}"
            )

        compile_result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={tex_dir}",
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            return f"PDF compilation failed:\n{compile_result.stdout[-2000:]}"

        return str(output_path.with_suffix(".pdf"))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cover_letter_tool.py -v
```

Expected: all PASS.

- [ ] **Step 5: Update tools __init__.py**

```python
from job_hunting.tools.dedup_tool import DedupTool
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.tools.cv_generator import CVGeneratorTool
from job_hunting.tools.cover_letter_tool import CoverLetterTool

__all__ = ["DedupTool", "TelegramNotifierTool", "CVGeneratorTool", "CoverLetterTool"]
```

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/tools/cover_letter_tool.py src/job_hunting/tools/__init__.py tests/test_cover_letter_tool.py
git commit -m "feat: CoverLetterTool with LaTeX validation before PDF compilation"
```

---

## Task 7: Discovery Crew

**Files:**
- Create: `src/job_hunting/crews/discovery/config/agents.yaml`
- Create: `src/job_hunting/crews/discovery/config/tasks.yaml`
- Create: `src/job_hunting/crews/discovery/crew.py`

- [ ] **Step 1: Create agents.yaml**

Create `src/job_hunting/crews/discovery/config/agents.yaml`:

```yaml
vacancy_scout:
  role: Vacancy Scout
  goal: >
    Discover new, live job openings from company career pages that have not
    been seen in previous runs.
  backstory: >
    You are an expert web researcher specializing in job market intelligence.
    You know how to navigate ATS platforms like Greenhouse, Lever, and Workday.
    You are thorough: you verify every vacancy is live before recording it,
    and you never save the same vacancy twice.
  verbose: true
  allow_delegation: false

fit_analyst:
  role: Fit Analyst
  goal: >
    Score each vacancy against the candidate's profile and search criteria,
    and determine whether a cover letter is required.
  backstory: >
    You are a senior recruiter and career advisor who can precisely assess
    how well a candidate matches any role. You give objective, metric-backed
    scores and clear reasoning. You also carefully read job descriptions to
    determine whether they explicitly request a cover letter.
  verbose: true
  allow_delegation: false
```

- [ ] **Step 2: Create tasks.yaml**

Create `src/job_hunting/crews/discovery/config/tasks.yaml`:

```yaml
scrape_vacancies_task:
  description: >
    Today's date is {today}. You are discovering new job vacancies.

    1. Read the file knowledge/companies.csv. It contains columns: company_name, career_page_url.
    2. For each company, use SeleniumScrapingTool to scrape the career_page_url and extract
       all open job positions (title, job-specific URL, brief description snippet).
    3. For each vacancy found:
       a. Use Vacancy Dedup Checker with the vacancy URL. If result is "duplicate", skip entirely.
       b. Use SeleniumScrapingTool to open the job-specific URL. Read the page content.
          If the page shows the job is closed, filled, or returns an error, skip entirely.
       c. Extract: full job description, required skills, any explicit application questions
          (e.g. "Why do you want to work here?"), and whether a cover letter is requested.
       d. Generate a vacancy ID as: lowercase company name and title, spaces and
          special chars replaced with hyphens, double-hyphen between company and title.
          Example: "Acme Corp" + "Senior PM" → "acme-corp--senior-pm"
       e. Write a JSON file to data/{today}/vacancies/{vacancy_id}.json with this exact schema:
          {
            "id": "{vacancy_id}",
            "company": "{company_name}",
            "title": "{job_title}",
            "url": "{job_url}",
            "description": "{full_job_description}",
            "questions": ["{question1}", "{question2}"],
            "scraped_at": "{ISO8601 timestamp}"
          }
          If there are no application questions, use an empty list [].
    4. Return a list of all vacancy IDs that were successfully saved.
  expected_output: >
    A JSON list of vacancy IDs saved, e.g. ["acme-corp--senior-pm", "gnosis--head-of-product"].
    Return an empty list [] if no new vacancies were found.
  agent: vacancy_scout

score_vacancies_task:
  description: >
    Today's date is {today}. Score all newly discovered vacancies.

    The previous task returned a list of vacancy IDs (e.g. ["acme-corp--senior-pm"]).
    For each vacancy ID, read the file at data/{today}/vacancies/{vacancy_id}.json
    using FileReadTool with the exact path.
    2. Read knowledge/search-criteria.md — these are the candidate's filters.
    3. Read knowledge/profile/profile-summary.md for candidate context.
    4. For each vacancy:
       a. Score it 0-100 based on fit with the candidate's profile and search criteria.
          Consider: role title match, seniority, location/remote preference, industry,
          company stage, salary range, excluded criteria from search-criteria.md.
       b. Determine requires_cover_letter: true if the job description explicitly asks
          for one, false otherwise.
       c. Set status to "skipped" if score is clearly below criteria (do not send to Telegram).
          Otherwise set status to "pending_approval".
       d. Write a JSON file to data/{today}/scores/{vacancy_id}.json with this schema:
          {
            "vacancy_id": "{vacancy_id}",
            "date": "{today}",
            "company": "{company_name}",
            "title": "{job_title}",
            "score": {integer 0-100},
            "reasoning": "{brief explanation of score}",
            "status": "pending_approval",
            "requires_cover_letter": {true or false}
          }
    5. Return a list of score file paths for vacancies with status "pending_approval".
  expected_output: >
    A JSON list of score file paths for qualifying vacancies, e.g.
    ["data/2026-05-10/scores/acme-corp--senior-pm.json"].
    Return [] if no vacancies qualify.
  agent: fit_analyst
  context:
    - scrape_vacancies_task
```

- [ ] **Step 3: Create crew.py**

Create `src/job_hunting/crews/discovery/crew.py`:

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import SeleniumScrapingTool, FileReadTool, FileWriterTool
from typing import List
from job_hunting.config import get_llm
from job_hunting.tools import DedupTool


@CrewBase
class DiscoveryCrew:
    """Discovers and scores new job vacancies."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def vacancy_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["vacancy_scout"],
            llm=get_llm(),
            tools=[SeleniumScrapingTool(), FileWriterTool(), DedupTool()],
            verbose=True,
        )

    @agent
    def fit_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["fit_analyst"],
            llm=get_llm(),
            tools=[FileReadTool(), FileWriterTool()],
            verbose=True,
        )

    @task
    def scrape_vacancies_task(self) -> Task:
        return Task(config=self.tasks_config["scrape_vacancies_task"])

    @task
    def score_vacancies_task(self) -> Task:
        return Task(config=self.tasks_config["score_vacancies_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

- [ ] **Step 4: Smoke test — verify crew instantiates without error**

```bash
python -c "
from job_hunting.crews.discovery.crew import DiscoveryCrew
c = DiscoveryCrew()
print('Discovery crew OK:', c.crew())
"
```

Expected: prints `Discovery crew OK:` with no exceptions.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/crews/discovery/
git commit -m "feat: Discovery Crew — Vacancy Scout and Fit Analyst"
```

---

## Task 8: DiscoveryFlow

**Files:**
- Create: `src/job_hunting/flows/discovery_flow.py`

- [ ] **Step 1: Create discovery_flow.py**

Create `src/job_hunting/flows/discovery_flow.py`:

```python
import json
from pathlib import Path
from datetime import date
from crewai.flow.flow import Flow, listen, start
from job_hunting.crews.discovery.crew import DiscoveryCrew
from job_hunting.config import MIN_SCORE
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import scores_dir


class DiscoveryFlow(Flow):

    @start()
    def run_discovery_crew(self) -> list[dict]:
        today = date.today().isoformat()
        result = DiscoveryCrew().crew().kickoff(inputs={"today": today})
        qualifying = []
        score_dir = scores_dir(today)
        if score_dir.exists():
            for score_file in score_dir.glob("*.json"):
                try:
                    data = json.loads(score_file.read_text())
                    if data.get("score", 0) >= MIN_SCORE and data.get("status") == "pending_approval":
                        qualifying.append(data)
                except (json.JSONDecodeError, OSError):
                    continue
        return qualifying

    @listen(run_discovery_crew)
    def send_approval_requests(self, qualifying_vacancies: list[dict]) -> None:
        if not qualifying_vacancies:
            print("No qualifying vacancies found today.")
            return

        notifier = TelegramNotifierTool()
        for vacancy in qualifying_vacancies:
            notifier._run(
                message_type="approval",
                company=vacancy["company"],
                title=vacancy["title"],
                url=vacancy.get("url", ""),
                score=vacancy["score"],
                vacancy_id=vacancy["vacancy_id"],
                date=vacancy["date"],
            )
            print(f"Sent approval request for {vacancy['vacancy_id']}")
```

- [ ] **Step 2: Smoke test — verify flow instantiates**

```bash
python -c "
from job_hunting.flows.discovery_flow import DiscoveryFlow
f = DiscoveryFlow()
print('DiscoveryFlow OK:', f)
"
```

Expected: prints without exceptions.

- [ ] **Step 3: Manual test run (requires valid .env and companies.csv)**

Before running, ensure `knowledge/companies.csv` has at least one row:
```
company_name,career_page_url
TestCompany,https://example.com/careers
```

Then run:
```bash
python -c "
from job_hunting.flows.discovery_flow import DiscoveryFlow
DiscoveryFlow().kickoff()
"
```

Expected: agents run, vacancy files appear in `data/{today}/vacancies/`, score files in `data/{today}/scores/`, Telegram messages sent.

- [ ] **Step 4: Commit**

```bash
git add src/job_hunting/flows/discovery_flow.py
git commit -m "feat: DiscoveryFlow — orchestrates Discovery Crew and sends Telegram approval requests"
```

---

## Task 9: Application Crew

**Files:**
- Create: `src/job_hunting/crews/application/config/agents.yaml`
- Create: `src/job_hunting/crews/application/config/tasks.yaml`
- Create: `src/job_hunting/crews/application/crew.py`

- [ ] **Step 1: Create agents.yaml**

Create `src/job_hunting/crews/application/config/agents.yaml`:

```yaml
profile_steward:
  role: Profile Steward
  goal: >
    Produce a concise, tailored profile brief for a specific job vacancy,
    and confirm whether a cover letter is required.
  backstory: >
    You are an expert career consultant with deep knowledge of the candidate's
    background. You identify the most relevant experiences and achievements
    for each specific role, and produce a clear brief that other agents rely on.
  verbose: true
  allow_delegation: false

qa_analyst:
  role: Application Q&A Analyst
  goal: >
    Extract application questions from a job description and write honest,
    specific answers based solely on the candidate's real experience.
  backstory: >
    You are an expert at crafting genuine, compelling answers to job application
    questions. You never fabricate facts. You write in a professional but human
    tone, with specific examples and real metrics from the candidate's profile.
  verbose: true
  allow_delegation: false

cv_architect:
  role: CV Architect
  goal: >
    Generate a tailored LaTeX CV and compile it to PDF for a specific job vacancy.
  backstory: >
    You are an expert CV writer who creates metrics-driven, tailored CVs.
    You follow strict quality rules: no AI slop, no PascalCase in sentences,
    metrics before keywords, bold key numbers. You produce clean LaTeX that
    compiles without errors.
  verbose: true
  allow_delegation: false

cover_letter_writer:
  role: Cover Letter Writer
  goal: >
    Write a tailored cover letter and compile it to PDF — only if required by the vacancy.
  backstory: >
    You are an expert cover letter writer. You write professional yet human letters:
    specific, direct, with real metrics. You never write generic phrases or corporate
    fluff. You skip this task entirely if no cover letter is required.
  verbose: true
  allow_delegation: false
```

- [ ] **Step 2: Create tasks.yaml**

Create `src/job_hunting/crews/application/config/tasks.yaml`:

```yaml
profile_brief_task:
  description: >
    You are preparing an application for this vacancy:
    - Company: {company}
    - Title: {title}
    - Vacancy ID: {vacancy_id}
    - Description: {description}
    - Requires cover letter: {requires_cover_letter}

    Read all profile files from knowledge/profile/ using FileReadTool:
    - profile-summary.md
    - work-experience.md
    - personal-projects.md
    - general-info.md
    - public-performance.md
    - values-and-interests.md

    Produce a structured profile brief (max 600 words) with:
    1. Candidate overview — 2-3 sentence summary tailored to this role
    2. Top 4+ relevant work experiences with their key metrics and achievements
    3. Most relevant 1-2 personal projects
    4. Skills alignment with the vacancy requirements
    5. requires_cover_letter: {requires_cover_letter} (pass through from input)
  expected_output: >
    A structured profile brief in markdown, including a requires_cover_letter field
    at the end (true or false). This brief will be used by all subsequent agents.
  agent: profile_steward

qa_task:
  description: >
    Based on the profile brief from the previous task and this vacancy description:
    {description}

    1. Extract all explicit application questions from the vacancy description.
       These are questions the employer wants answered (e.g. "Why do you want to work here?",
       "Describe your experience with X").
    2. For each question, write a genuine, specific answer using only facts from the
       profile brief. Use real metrics when available. No generic phrases.
    3. If no questions are found, write "No application questions in this vacancy."
    4. Write the output to data/{date}/applications/{vacancy_id}/qa-answers.md
       using FileWriterTool.
  expected_output: >
    Markdown file with each question as a heading followed by the answer,
    saved to data/{date}/applications/{vacancy_id}/qa-answers.md.
  agent: qa_analyst
  context:
    - profile_brief_task

cv_task:
  description: >
    Generate a tailored CV for this vacancy:
    - Company: {company}
    - Title: {title}
    - Description: {description}

    Steps:
    1. Read personalized-outreach/best-practices/cv.md with FileReadTool to understand
       the required quality bar for format, density, and tone.
    2. Using the profile brief from profile_brief_task, generate a tailored JSON object
       with this exact structure:
       {
         "summary": "Tailored summary max 430 chars for this role and company",
         "workExperienceIds": ["id1", "id2", "id3", "id4"],
         "workExperienceDescriptions": {
           "id1": ["Achievement with **metric**", "Achievement 2"],
           "id2": ["Achievement with **metric**"]
         },
         "projectIds": ["project-id-1"],
         "projectDescriptions": {
           "project-id-1": ["Tailored project description"]
         },
         "skills": "Tailored skills list for this vacancy"
       }
       IDs come from work-experience.md: lowercase company name, spaces to hyphens,
       remove special chars. E.g. "Blockscout" → "blockscout".
       Include at least 4 work experiences. Bold key metrics with **double asterisks**.
       Apply the anti-slop filter: no "spearheaded", "leveraged", "streamlined", etc.
       No PascalCase in sentences.
    3. Use CV Generator tool with the JSON string and output path:
       data/{date}/applications/{vacancy_id}/cv.tex
    4. The tool returns the PDF path on success or an error. If error, fix the JSON and retry.
  expected_output: >
    The path to the generated cv.pdf file, e.g.
    "data/2026-05-10/applications/acme-corp--senior-pm/cv.pdf"
  agent: cv_architect
  context:
    - profile_brief_task

cover_letter_task:
  description: >
    Generate a tailored cover letter for this vacancy:
    - Company: {company}
    - Title: {title}
    - Description: {description}

    IMPORTANT: First check the requires_cover_letter field in the profile brief
    from profile_brief_task. If it is false, output exactly:
    "Cover letter not required for this vacancy." and stop — do not generate anything.

    If requires_cover_letter is true:
    1. Read personalized-outreach/best-practices/cover-letter.md with FileReadTool.
    2. Using the profile brief, draft three sections:
       - intro: 60-80 words. Open with a specific hook tied to the company or role —
         not "I am writing to apply". Mirror the company's language, then bridge to
         your background. No PascalCase, no AI slop.
       - main_body: 150-200 words total. 2-3 experiences with real metrics. Lead with
         the outcome, not the task. Keep it direct and human.
       - conclusion: 40-60 words. Soft call to action. Genuine interest.
    3. Use Cover Letter Generator tool with intro, main_body, conclusion, and output path:
       data/{date}/applications/{vacancy_id}/cover-letter.tex
    4. If the tool returns an error, fix the content and retry once.
  expected_output: >
    The path to the generated cover-letter.pdf, e.g.
    "data/2026-05-10/applications/acme-corp--senior-pm/cover-letter.pdf"
    — or "Cover letter not required for this vacancy." if not needed.
  agent: cover_letter_writer
  context:
    - profile_brief_task
```

- [ ] **Step 3: Create crew.py**

Create `src/job_hunting/crews/application/crew.py`:

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import FileReadTool, FileWriterTool
from typing import List
from job_hunting.config import get_llm
from job_hunting.tools import CVGeneratorTool, CoverLetterTool


@CrewBase
class ApplicationCrew:
    """Generates tailored CV, cover letter, and Q&A answers for an approved vacancy."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def profile_steward(self) -> Agent:
        return Agent(
            config=self.agents_config["profile_steward"],
            llm=get_llm(),
            tools=[FileReadTool()],
            verbose=True,
        )

    @agent
    def qa_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_analyst"],
            llm=get_llm(),
            tools=[FileWriterTool()],
            verbose=True,
        )

    @agent
    def cv_architect(self) -> Agent:
        return Agent(
            config=self.agents_config["cv_architect"],
            llm=get_llm(),
            tools=[FileReadTool(), CVGeneratorTool()],
            verbose=True,
        )

    @agent
    def cover_letter_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["cover_letter_writer"],
            llm=get_llm(),
            tools=[FileReadTool(), CoverLetterTool()],
            verbose=True,
        )

    @task
    def profile_brief_task(self) -> Task:
        return Task(config=self.tasks_config["profile_brief_task"])

    @task
    def qa_task(self) -> Task:
        return Task(config=self.tasks_config["qa_task"])

    @task
    def cv_task(self) -> Task:
        return Task(config=self.tasks_config["cv_task"])

    @task
    def cover_letter_task(self) -> Task:
        return Task(config=self.tasks_config["cover_letter_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

- [ ] **Step 4: Smoke test**

```bash
python -c "
from job_hunting.crews.application.crew import ApplicationCrew
c = ApplicationCrew()
print('Application crew OK:', c.crew())
"
```

Expected: no exceptions.

- [ ] **Step 5: Commit**

```bash
git add src/job_hunting/crews/application/
git commit -m "feat: Application Crew — Profile Steward, Q&A Analyst, CV Architect, Cover Letter Writer"
```

---

## Task 10: ApplicationFlow

**Files:**
- Create: `src/job_hunting/flows/application_flow.py`

- [ ] **Step 1: Create application_flow.py**

Create `src/job_hunting/flows/application_flow.py`:

```python
import json
from pathlib import Path
from crewai.flow.flow import Flow, listen, start
from job_hunting.crews.application.crew import ApplicationCrew
from job_hunting.tools.telegram_notifier import TelegramNotifierTool
from job_hunting.utils import vacancies_dir, scores_dir


class ApplicationFlow(Flow):

    def __init__(self, vacancy_id: str, date: str):
        super().__init__()
        self._vacancy_id = vacancy_id
        self._date = date

    @start()
    def run_application_crew(self) -> dict:
        vacancy_path = vacancies_dir(self._date) / f"{self._vacancy_id}.json"
        score_path = scores_dir(self._date) / f"{self._vacancy_id}.json"

        vacancy = json.loads(vacancy_path.read_text())
        score = json.loads(score_path.read_text())

        score["status"] = "approved"
        score_path.write_text(json.dumps(score, indent=2))

        ApplicationCrew().crew().kickoff(
            inputs={
                "company": vacancy["company"],
                "title": vacancy["title"],
                "url": vacancy["url"],
                "description": vacancy["description"],
                "vacancy_id": self._vacancy_id,
                "date": self._date,
                "requires_cover_letter": str(score.get("requires_cover_letter", False)).lower(),
            }
        )
        return {"vacancy": vacancy, "score": score}

    @listen(run_application_crew)
    def notify_completion(self, result: dict) -> None:
        vacancy = result["vacancy"]
        score = result["score"]

        score_path = scores_dir(self._date) / f"{self._vacancy_id}.json"
        score["status"] = "documents_ready"
        score_path.write_text(json.dumps(score, indent=2))

        TelegramNotifierTool()._run(
            message_type="completion",
            company=vacancy["company"],
            title=vacancy["title"],
            url=vacancy["url"],
            score=score["score"],
            vacancy_id=self._vacancy_id,
            date=self._date,
        )
```

- [ ] **Step 2: Smoke test**

```bash
python -c "
from job_hunting.flows.application_flow import ApplicationFlow
f = ApplicationFlow(vacancy_id='test--test', date='2026-05-10')
print('ApplicationFlow OK:', f)
"
```

Expected: no exceptions.

- [ ] **Step 3: Commit**

```bash
git add src/job_hunting/flows/application_flow.py
git commit -m "feat: ApplicationFlow — runs Application Crew and sends Telegram completion notification"
```

---

## Task 11: Telegram Bot

**Files:**
- Create: `src/job_hunting/bot/telegram_bot.py`
- Create: `src/job_hunting/bot/__init__.py`

- [ ] **Step 1: Create bot/__init__.py**

```bash
touch src/job_hunting/bot/__init__.py
```

- [ ] **Step 2: Create telegram_bot.py**

Create `src/job_hunting/bot/telegram_bot.py`:

```python
import json
import logging
import threading
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from job_hunting.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from job_hunting.utils import scores_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _update_status(vacancy_id: str, date: str, status: str) -> None:
    score_path = scores_dir(date) / f"{vacancy_id}.json"
    if not score_path.exists():
        logger.warning(f"Score file not found: {score_path}")
        return
    data = json.loads(score_path.read_text())
    data["status"] = status
    score_path.write_text(json.dumps(data, indent=2))


def _parse_callback(data: str) -> tuple[str, str, str]:
    """Parse 'action:vacancy_id:date' → (action, vacancy_id, date)."""
    parts = data.split(":", 2)
    return parts[0], parts[1], parts[2]


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.from_user.id != TELEGRAM_CHAT_ID:
        return

    await query.answer()
    action, vacancy_id, date = _parse_callback(query.data)

    if action == "approve":
        _update_status(vacancy_id, date, "approved")
        await query.edit_message_text(f"✅ Approved — starting application for {vacancy_id}…")
        threading.Thread(
            target=_run_application_flow,
            args=(vacancy_id, date),
            daemon=True,
        ).start()

    elif action == "decline":
        _update_status(vacancy_id, date, "declined")
        await query.edit_message_text(f"❌ Declined: {vacancy_id}")

    elif action == "applied":
        _update_status(vacancy_id, date, "applied")
        await query.edit_message_text(f"✅ Marked as applied: {vacancy_id}")

    elif action == "not_applied":
        _update_status(vacancy_id, date, "not_applied")
        await query.edit_message_text(f"📝 Noted — not applied: {vacancy_id}")


def _run_application_flow(vacancy_id: str, date: str) -> None:
    from job_hunting.flows.application_flow import ApplicationFlow
    try:
        ApplicationFlow(vacancy_id=vacancy_id, date=date).kickoff()
    except Exception as e:
        logger.error(f"ApplicationFlow failed for {vacancy_id}: {e}")


def run() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot started. Listening for callbacks…")
    app.run_polling(drop_pending_updates=True)
```

- [ ] **Step 3: Manual test — start the bot and verify it connects**

```bash
python -c "from job_hunting.bot.telegram_bot import run; run()"
```

Expected: `Bot started. Listening for callbacks…` — no exceptions. Press Ctrl+C to stop.

- [ ] **Step 4: Commit**

```bash
git add src/job_hunting/bot/
git commit -m "feat: Telegram bot with approval and status callback handlers"
```

---

## Task 12: Career Advisor and Chainlit App

**Files:**
- Create: `src/job_hunting/agents/career_advisor.py`
- Create: `src/job_hunting/advisor/app.py`

- [ ] **Step 1: Create career_advisor.py**

Create `src/job_hunting/agents/career_advisor.py`:

```python
from crewai import Agent
from crewai_tools import FileReadTool
from job_hunting.config import get_llm


def build_career_advisor() -> Agent:
    return Agent(
        role="Career Advisor",
        goal=(
            "Help the candidate understand their job search status, assess fit for specific roles, "
            "and answer any questions about their applications and pipeline."
        ),
        backstory=(
            "You are a knowledgeable career advisor with full access to the candidate's job search data. "
            "You can read vacancy details, fit scores, application statuses, and profile information. "
            "You give direct, honest, and specific answers. You always base your answers on actual data "
            "from the files — never make up information."
        ),
        llm=get_llm(),
        tools=[FileReadTool()],
        verbose=True,
        memory=True,
    )
```

- [ ] **Step 2: Create advisor/app.py**

Create `src/job_hunting/advisor/app.py`:

```python
import chainlit as cl
from crewai import Task, Crew, Process
from job_hunting.agents.career_advisor import build_career_advisor


@cl.on_message
async def on_message(message: cl.Message) -> None:
    advisor = build_career_advisor()

    task = Task(
        description=(
            f"The candidate asks: {message.content}\n\n"
            "Use FileReadTool to read relevant files from data/ and knowledge/profile/ "
            "to answer accurately. Scan data/*/scores/*.json for application statuses, "
            "data/*/vacancies/*.json for vacancy details, and data/*/applications/ for "
            "generated documents. Always base your answer on actual file contents."
        ),
        expected_output="A clear, specific answer to the candidate's question.",
        agent=advisor,
    )

    crew = Crew(
        agents=[advisor],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    await cl.Message(content=str(result)).send()
```

- [ ] **Step 3: Test — start Chainlit and verify it loads**

```bash
chainlit run src/job_hunting/advisor/app.py --port 8001
```

Expected: Chainlit opens in browser at `http://localhost:8001`. Send a message like "What vacancies were found today?" and verify the advisor responds.

- [ ] **Step 4: Commit**

```bash
git add src/job_hunting/agents/career_advisor.py src/job_hunting/advisor/app.py
git commit -m "feat: Career Advisor agent and Chainlit chat interface"
```

---

## Task 13: Main entry points and search-criteria template

**Files:**
- Modify: `src/job_hunting/main.py`
- Create: `knowledge/search-criteria.md`

- [ ] **Step 1: Replace main.py with new entry points**

Overwrite `src/job_hunting/main.py`:

```python
from dotenv import load_dotenv

load_dotenv()


def run_discovery() -> None:
    """Cron entry point — discover and score new vacancies, send Telegram approval requests."""
    from job_hunting.flows.discovery_flow import DiscoveryFlow
    DiscoveryFlow().kickoff()


def run_bot() -> None:
    """Long-running entry point — start the Telegram bot."""
    from job_hunting.bot.telegram_bot import run
    run()


def run_advisor() -> None:
    """Long-running entry point — start the Chainlit Career Advisor."""
    import subprocess
    import sys
    import os
    advisor_path = os.path.join(os.path.dirname(__file__), "advisor", "app.py")
    subprocess.run([sys.executable, "-m", "chainlit", "run", advisor_path], check=True)
```

- [ ] **Step 2: Verify entry points work**

```bash
python -c "from job_hunting.main import run_discovery; print('run_discovery OK')"
python -c "from job_hunting.main import run_bot; print('run_bot OK')"
python -c "from job_hunting.main import run_advisor; print('run_advisor OK')"
```

Expected: each prints its OK message without exceptions.

- [ ] **Step 3: Create knowledge/search-criteria.md template**

Create `knowledge/search-criteria.md`:

```markdown
# Job Search Criteria

## Target role titles
- Product Manager
- Senior Product Manager
- Head of Product
- CPO

## Seniority
- Mid-level (3-5 years)
- Senior (5+ years)

## Location and work format
- Remote or hybrid
- Europe time zones preferred

## Salary range
- Minimum: $80,000 USD / year
- Preferred: $120,000+ USD / year

## Preferred industries / domains
- Web3 / DeFi / blockchain
- B2B SaaS
- Fintech

## Preferred company stage
- Series A to Series C startups
- Scale-ups

## Excluded criteria
- Companies in gambling, adult content, or tobacco industries
- On-site only roles outside of Europe
- Junior or internship roles
```

> **Note:** Edit this file with your real criteria before the first Discovery run.

- [ ] **Step 4: Set up cron job (adjust path to your venv)**

Print cron line to add:

```bash
echo "0 9 * * 1-5 $(which job_hunting_discover 2>/dev/null || echo '/path/to/venv/bin/job_hunting_discover')"
```

Add this line to crontab with `crontab -e`.

- [ ] **Step 5: Final smoke test — all three entry points**

```bash
# Verify discovery imports cleanly
job_hunting_discover --help 2>/dev/null || python -c "from job_hunting.main import run_discovery; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/main.py knowledge/search-criteria.md
git commit -m "feat: main entry points and search-criteria template — system ready for first run"
```

---

## System Dependencies Checklist

Before the first real run, verify:

```bash
node --version          # Node.js required for fill-template.js
pdflatex --version      # TeX Live / MacTeX required for PDF compilation
python --version        # Python 3.10+
```

Install if missing:
- Node.js: https://nodejs.org
- MacTeX: `brew install --cask mactex` or https://tug.org/mactex/
- ChromeDriver (for SeleniumScrapingTool): `brew install chromedriver` or `pip install webdriver-manager`
