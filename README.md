# Job Hunting Crew

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![crewAI](https://img.shields.io/badge/crewAI-Agents-111111?style=flat)](https://crewai.com)
[![Selenium](https://img.shields.io/badge/Selenium-Web%20Automation-43B02A?style=flat&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Chainlit](https://img.shields.io/badge/Chainlit-Advisor%20UI-1E90FF?style=flat)](https://docs.chainlit.io/)
[![uv](https://img.shields.io/badge/uv-Dependency%20Manager-DE5FE9?style=flat)](https://docs.astral.sh/uv/)

AI-powered job hunting automation that discovers relevant vacancies, scores them against your profile, asks for approval in Telegram, and generates tailored application documents (CV, cover letter, answers) for approved roles. It can also source new company career-page candidates for later vacancy discovery.

## What This Service Is For

This project helps you run a structured, human-in-the-loop job search pipeline:

1. Discover new roles from company career pages.
2. Source new company career pages from public search queries.
3. Score each role for fit.
4. Ask you to approve/decline vacancies via Telegram.
5. Generate application assets for approved jobs.
6. Track all artifacts locally in `data/`.

## ATS Support (100% Working)

The following ATS domains are working 100% in this project:

- `jobs.ashbyhq.com`
- `job-boards.greenhouse.io`
- `jobs.lever.co`
- `jobs.personio.com`
- `bamboohr.com`

> ⚠️ IMPORTANT: Custom career pages are also supported, but can be handled differently by AI and potentially can't be properly processed

## Quick Start

For a non-code setup walkthrough, see [`docs/setup-guide.md`](docs/setup-guide.md).
Example `knowledge/` files are available in [`examples/knowledge/`](examples/knowledge/).

### 1. Install dependencies

Requires Python `>=3.10,<3.14`.

```bash
pip install uv
uv sync
source .venv/bin/activate
```

If `uv sync` fails on Intel macOS because of `onnxruntime`, run:

```bash
uv sync --no-install-package onnxruntime
source .venv/bin/activate
```

### 2. Configure environment

```bash
cp .env.example .env
```

Set values in `.env`:

- `OPENAI_API_BASE`
- `OPENAI_API_KEY`
- `MODEL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_ALLOWED_USERS` (optional, comma-separated)
- `MIN_SCORE` (default: `70`)

### 3. Add target companies

Create a `knowledge` folder in the project root and fill all necessary files. Examples are in [`examples/knowledge/`](examples/knowledge/); the guide for files are in [`docs/setup-guide.md`](docs/setup-guide.md)

Edit `knowledge/companies.csv` with company name + career page URL.

Optional: edit `knowledge/company-source-queries.yaml` to tune public search queries used for finding new company career pages. This does not modify `knowledge/companies.csv`; sourced candidates are written separately for review.

### 4. Run the system

Start the Telegram bot (terminal 1):

```bash
job_hunting_bot
```

Run discovery (terminal 2, cron-friendly entrypoint):

```bash
job_hunting_discover
```

Source new company career-page candidates (cron-friendly, separate from vacancy discovery):

```bash
job_hunting_source_companies
```

Optional: start the local advisor chat UI (Chainlit):

```bash
job_hunting_advisor
```

## How To Use

1. Run discovery periodically (manual or cron).
2. Receive Telegram approval cards for high-score roles.
3. Click `Approve` to trigger document generation.
4. Review generated artifacts in `data/<date>/applications/<vacancy_id>/`.
5. Mark status back in Telegram (`applied`, `not_applied`, etc.).

Run company sourcing when you want to expand the company list. It searches using `knowledge/company-source-queries.yaml`, deduplicates against `knowledge/companies.csv`, `knowledge/approved-company-candidates.csv`, and prior generated candidates, writes rich review candidates to `data/<date>/company_candidates.csv`, and sends each new pending candidate to Telegram with `Approve`/`Decline` buttons. Approved candidates are appended to `knowledge/approved-company-candidates.csv` for future discovery runs.

## Data Layout

Generated files are stored under:

- `data/<YYYY-MM-DD>/vacancies/*.json`
- `data/<YYYY-MM-DD>/scores/*.json`
- `data/<YYYY-MM-DD>/applications/<vacancy_id>/...`
- `data/<YYYY-MM-DD>/company_candidates.csv`
- `data/<YYYY-MM-DD>/discovery_coverage.csv`
- `knowledge/approved-company-candidates.csv`

## Main Commands

Activate the environment first:

```bash
source .venv/bin/activate
```

- `job_hunting_bot` — Starts the Telegram bot. Output: waits for Telegram actions and handles approvals/status updates.
- `job_hunting_discover` — Reads `knowledge/companies.csv`, discovers vacancies, scores them, and sends suitable roles to Telegram. Output: `data/<YYYY-MM-DD>/discovery_coverage.csv`, `data/<YYYY-MM-DD>/vacancies/`, `data/<YYYY-MM-DD>/scores/`, and application files after approval.
- `job_hunting_source_companies` — Searches for new company career-page candidates. Output: `data/<YYYY-MM-DD>/company_candidates.csv` and a Telegram review notification when new candidates are found.
- `job_hunting_advisor` — Starts the Chainlit advisor UI. Output: local web chat for career/application questions.

Without activating `.venv`, prefix commands with `uv run`, for example:

```bash
uv run job_hunting_discover
```

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
