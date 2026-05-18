# Job Hunting Multi-Agent System — Design Spec

**Date:** 2026-05-10
**Status:** Approved

> Archival note: this original system design predates the structured YAML
> profile section migration. References below to Markdown profile files are
> historical context; current setup uses `knowledge/profile.yaml` plus
> allowlisted `knowledge/profile/*.yaml` section files.

---

## Overview

A multi-agent AI system built with CrewAI (Python SDK) that automates the job hunting pipeline. The system uses two CrewAI Flows as orchestrators, two Crews, and one standalone conversational agent exposed via Chainlit.

---

## Architecture

### Three independently runnable entry points

```
job_hunting_discover   # cron-triggered → runs Discovery
job_hunting_bot        # long-running → Telegram approval + notification loop
job_hunting_advisor    # long-running → Chainlit Career Advisor UI
```

### Two CrewAI Flows

**DiscoveryFlow** — cron-triggered daily. Runs the Discovery Crew, then sends Telegram approval messages for qualifying vacancies.

**ApplicationFlow** — triggered per approved job by the Telegram bot. Runs the Application Crew, then sends a Telegram completion notification with Applied/Not applied buttons.

### One standalone agent

**Career Advisor** — a single CrewAI agent (no crew, no flow) wired into a Chainlit chat UI. Always-on, answers questions about the job search.

---

## Source Layout

```
src/job_hunting/
├── flows/
│   ├── discovery_flow.py
│   └── application_flow.py
├── crews/
│   ├── discovery/
│   │   ├── crew.py
│   │   └── config/
│   │       ├── agents.yaml
│   │       └── tasks.yaml
│   └── application/
│       ├── crew.py
│       └── config/
│           ├── agents.yaml
│           └── tasks.yaml
├── agents/
│   └── career_advisor.py
├── tools/
│   ├── cv_generator.py       # wraps fill-template.js + pdflatex
│   ├── cover_letter_tool.py  # fills LaTeX template + pdflatex
│   └── telegram_notifier.py  # sends messages via bot token
├── bot/
│   └── telegram_bot.py       # long-polling bot
├── advisor/
│   └── app.py                # Chainlit app
└── main.py                   # CLI entry points
```

---

## Knowledge & Data Layout

### `knowledge/` — static agent knowledge (read via `FileReadTool`, not RAG)

Agents access `knowledge/` files with `FileReadTool` (full file reads), not CrewAI's embedding-based Knowledge feature. Files are small and structured enough to read in full — RAG adds unnecessary complexity and indirection at this scale.

```
knowledge/
├── profile/
│   ├── profile-summary.md
│   ├── work-experience.md
│   ├── personal-projects.md
│   ├── general-info.md
│   ├── public-performance.md
│   └── values-and-interests.md
├── companies.csv              # company name + career page URL
└── profile.yaml.search         # qualitative filters for agent reasoning: role titles,
                               #   seniority, salary range, location, work format,
                               #   industry, company stage, excluded companies/criteria
```

### `data/` — runtime artifacts, organized by Discovery run date

```
data/
└── {YYYY-MM-DD}/              # date of the Discovery run
    ├── vacancies/
    │   └── {company_slug}--{role_slug}.json
    ├── scores/
    │   └── {company_slug}--{role_slug}.json
    └── applications/
        └── {company_slug}--{role_slug}/
            ├── cv.tex
            ├── cv.pdf
            ├── cover-letter.tex
            ├── cover-letter.pdf
            └── qa-answers.md
```

All data about a vacancy (score, documents) lives in the folder of the date it was discovered.

### Vacancy JSON schema

```json
{
  "id": "acme--senior-pm",
  "company": "Acme",
  "title": "Senior Product Manager",
  "url": "https://acme.com/careers/senior-pm",
  "description": "...",
  "questions": ["Why do you want to work here?"],
  "scraped_at": "2026-05-10T09:00:00Z"
}
```

### Score JSON schema

```json
{
  "vacancy_id": "acme--senior-pm",
  "date": "2026-05-10",
  "score": 87,
  "reasoning": "Strong match on...",
  "status": "pending_approval"
}
```

### Status lifecycle

```
pending_approval  →  approved | declined
approved          →  documents_ready
documents_ready   →  applied | not_applied
skipped                          (below score threshold, never sent to Telegram)
```

---

## Discovery Flow & Crew

### Trigger

System cron calls `job_hunting_discover` (e.g. daily at 9am, Mon–Fri).

### DiscoveryFlow

```
@start: run_discovery_crew()
  → Discovery Crew kickoff
  → returns list of scored vacancies above threshold

@listen(run_discovery_crew): send_approval_requests()
  → for each qualifying vacancy:
      sends Telegram message with company, role, URL, fit score,
      and [Approve] / [Decline] inline keyboard buttons
```

### Discovery Crew agents

| Agent | Task | Tools |
|---|---|---|
| **Vacancy Scout** | Read `knowledge/companies.csv`, scrape each career page, extract open positions | `SeleniumScrapingTool`, `FileReadTool`, `FileWriterTool` |
| **Fit Analyst** | Score each vacancy against profile + search-criteria, filter below threshold | `FileReadTool`, `FileWriterTool` |

**Note on scraping:** Most company career pages redirect to ATS platforms (Greenhouse, Lever, Workday, BambooHR) which are JavaScript-rendered. `SeleniumScrapingTool` uses a real browser and handles JS-rendered pages correctly. It is used for both career page scraping and individual vacancy URL availability checks.

### Vacancy Scout validation steps (per vacancy found)

1. **Dedup check** — scan `data/*/vacancies/` for matching URL. If found, skip entirely — nothing written.
2. **Availability check** — open the vacancy URL directly. If HTTP error or page indicates position is closed/filled, skip entirely — nothing written.
3. **Both checks pass** — extract full details, write to `data/{date}/vacancies/`.

Dedup scanning uses a custom tool that globs all existing vacancy JSON files and returns a set of known URLs.

---

## Application Flow & Crew

### Trigger

Telegram bot receives `approve:{vacancy_id}:{date}` callback → calls `ApplicationFlow.kickoff()` in a background thread.

### ApplicationFlow

```
@start: run_application_crew()
  → reads vacancy + score JSON from data/{date}/
  → Application Crew kickoff with vacancy context

@listen(run_application_crew): notify_completion()
  → sends Telegram message:
      📋 {Company} — {Role}
      CV, cover letter, and Q&A answers are ready.
      📎 data/{date}/applications/{vacancy_id}/
      [✅ Applied]  [❌ Not applied]
  → updates score status to "documents_ready"
```

### Application Crew agents

| Agent | Task | Tools |
|---|---|---|
| **Profile Steward** | Reads all `knowledge/profile/` files, produces a concise profile brief tailored to this vacancy; also extracts `requires_cover_letter: true/false` from the vacancy description | `FileReadTool` |
| **Q&A Analyst** | Extracts application questions from vacancy description, answers each based on profile brief | `FileWriterTool` → `qa-answers.md` |
| **CV Architect** | Generates tailored JSON selections → runs `fill-template.js` → validates LaTeX → converts `.tex` to PDF | Custom `CVGeneratorTool` |
| **Cover Letter Writer** | Fills LaTeX cover letter template → validates LaTeX → converts to PDF. **Skipped entirely if `requires_cover_letter` is false.** | Custom `CoverLetterTool` |

**Agent order:** Profile Steward → Q&A Analyst → CV Architect → Cover Letter Writer (conditional).
Profile Steward output is passed as context to all downstream agents.

### CV generation pipeline

Reuses `personalized-outreach/` folder (templates, best-practices, `fill-template.js`) as-is. The `CVGeneratorTool` Python wrapper:
1. Runs `node personalized-outreach/scripts/fill-template.js` with tailored JSON → produces `.tex`
2. Validates: runs `pdflatex -draftmode -interaction=nonstopmode` on the `.tex` file
   - If exit code is non-zero or log contains errors → returns error to agent for retry
   - If clean → proceeds to full compilation
3. Runs `pdflatex -interaction=nonstopmode` → produces final `.pdf`

`CoverLetterTool` follows the same validate-then-compile pattern using `personalized-outreach/templates/cover-letter.md`.

Output: `data/{date}/applications/{vacancy_id}/cv.tex`, `cv.pdf`, and optionally `cover-letter.tex`, `cover-letter.pdf`.

---

## Telegram Bot

### Trigger

`job_hunting_bot` — long-running `python-telegram-bot` process (long-polling).

### Callback handlers

| Callback data | Action |
|---|---|
| `approve:{vacancy_id}:{date}` | Update status → `approved`, kick off ApplicationFlow in background thread, reply "Starting application for {company}…" |
| `decline:{vacancy_id}:{date}` | Update status → `declined`, reply "Declined ✓" |
| `applied:{vacancy_id}:{date}` | Update status → `applied`, reply "Marked as applied ✓" |
| `not_applied:{vacancy_id}:{date}` | Update status → `not_applied`, reply "Noted ✓" |

**Security:** every incoming message and callback is validated against `TELEGRAM_CHAT_ID`. Any other sender is silently ignored.

**Concurrency:** ApplicationFlow runs in a background thread so the bot stays responsive during CV generation.

---

## Career Advisor

### Trigger

`job_hunting_advisor` — starts Chainlit server.

### Agent

Single CrewAI agent, no crew or flow.

```
Tools:
  - FileReadTool → data/ (vacancies, scores, applications)
  - FileReadTool → knowledge/profile/
Memory: session-level (Chainlit manages conversation history)
```

Answers questions such as:
- "What jobs am I waiting to hear back from?"
- "Show me everything I applied to this week"
- "How well do I fit the Acme PM role?"
- "What did I answer for the Gnosis application Q&A?"

Scans `data/` dynamically per question — no pre-indexing needed at personal-use data volumes.

### Chainlit integration

`advisor/app.py` hooks into `@cl.on_message`, passes the user message to the Career Advisor agent, streams the response back.

---

## Configuration

### Environment variables (`.env`)

```
OPENAI_API_BASE=<CLIProxyAPI endpoint>
OPENAI_API_KEY=<CLIProxyAPI key>
MODEL=<model name>
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<your chat id>
MIN_SCORE=70                   # vacancies scoring below this are skipped (default: 70)
```

### Python dependencies (`pyproject.toml`)

```toml
dependencies = [
    "crewai[tools]>=1.9.3",
    "python-telegram-bot>=21.0",
    "chainlit>=1.0",
    "python-dotenv",
]
```

### System dependencies (install separately, document in README)

- **Node.js** — required for `fill-template.js`
- **MacTeX / TeX Live** — required for `pdflatex` (LaTeX → PDF)

### CLI entry points (`pyproject.toml`)

```toml
[project.scripts]
job_hunting_discover = "job_hunting.main:run_discovery"
job_hunting_bot      = "job_hunting.main:run_bot"
job_hunting_advisor  = "job_hunting.main:run_advisor"
```

### Cron example

```cron
0 9 * * 1-5  /path/to/venv/bin/job_hunting_discover
```

---

## Out of scope (v1)

- LinkedIn / Indeed / other job board scraping (companies.csv only for now)
- Multi-user support
- Web dashboard
- Automatic job application submission
