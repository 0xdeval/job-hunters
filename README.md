# Job Hunting Crew

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![crewAI](https://img.shields.io/badge/crewAI-Agents-111111?style=flat)](https://crewai.com)
[![Selenium](https://img.shields.io/badge/Selenium-Web%20Automation-43B02A?style=flat&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Chainlit](https://img.shields.io/badge/Chainlit-Advisor%20UI-1E90FF?style=flat)](https://docs.chainlit.io/)
[![uv](https://img.shields.io/badge/uv-Dependency%20Manager-DE5FE9?style=flat)](https://docs.astral.sh/uv/)

AI-powered job hunting automation that discovers relevant vacancies, scores them against your profile, asks for approval in Telegram, and generates tailored application documents (CV, cover letter, answers) for approved roles.

## What This Service Is For

This project helps you run a structured, human-in-the-loop job search pipeline:

1. Discover new roles from company career pages.
2. Score each role for fit.
3. Ask you to approve/decline via Telegram.
4. Generate application assets for approved jobs.
5. Track all artifacts locally in `data/`.

## ATS Support (100% Working)

The following ATS domains are working 100% in this project:

- `jobs.ashbyhq.com`
- `job-boards.greenhouse.io`
- `jobs.lever.co`
- `jobs.personio.com`
- `bamboohr.com`

## Quick Start

### 1. Install dependencies

Requires Python `>=3.10,<3.14`.

```bash
pip install uv
uv sync
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

Edit `knowledge/companies.csv` with company name + career page URL.

### 4. Run the system

Start the Telegram bot (terminal 1):

```bash
uv run job_hunting_bot
```

Run discovery (terminal 2, cron-friendly entrypoint):

```bash
uv run job_hunting_discover
```

Optional: start the local advisor chat UI (Chainlit):

```bash
uv run job_hunting_advisor
```

## How To Use

1. Run discovery periodically (manual or cron).
2. Receive Telegram approval cards for high-score roles.
3. Click `Approve` to trigger document generation.
4. Review generated artifacts in `data/<date>/applications/<vacancy_id>/`.
5. Mark status back in Telegram (`applied`, `not_applied`, etc.).

## Data Layout

Generated files are stored under:

- `data/<YYYY-MM-DD>/vacancies/*.json`
- `data/<YYYY-MM-DD>/scores/*.json`
- `data/<YYYY-MM-DD>/applications/<vacancy_id>/...`

## Main Commands

- `uv run job_hunting_discover` — Discover and score vacancies.
- `uv run job_hunting_bot` — Run Telegram approval/status bot.
- `uv run job_hunting_advisor` — Run Chainlit career advisor UI.
