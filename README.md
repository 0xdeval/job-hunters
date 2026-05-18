# Job Hunting Crew

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![crewAI](https://img.shields.io/badge/crewAI-Agents-111111?style=flat)](https://crewai.com)
[![Selenium](https://img.shields.io/badge/Selenium-Web%20Automation-43B02A?style=flat&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Chainlit](https://img.shields.io/badge/Chainlit-Advisor%20UI-1E90FF?style=flat)](https://docs.chainlit.io/)
[![uv](https://img.shields.io/badge/uv-Dependency%20Manager-DE5FE9?style=flat)](https://docs.astral.sh/uv/)

AI-powered job hunting automation that discovers relevant vacancies from your curated company list, scores them against your profile, asks for approval in Telegram, and generates tailored application documents (CV, cover letter, answers) for approved roles.

## What This Service Is For

This project helps you run a structured, human-in-the-loop job search pipeline:

1. Discover new roles from curated company career pages.
2. Score each role for fit.
3. Ask you to approve/decline vacancies via Telegram.
4. Generate application assets for approved jobs.
5. Track all artifacts locally in `data/`.

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
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
# or just
source ~/.bashrc
uv sync
source .venv/bin/activate
```

If `uv sync` fails on Intel macOS because of `onnxruntime`, run:

```bash
uv sync --no-install-package onnxruntime
source .venv/bin/activate
```

Selenium vacancy extraction also requires a Chrome-compatible browser on the
host. On Linux servers, install Chromium or Google Chrome before starting
`job_hunting_bot` or `job_hunting_discover`. Install a matching ChromeDriver as
well; the browser and driver major versions must match.

```bash
sudo apt-get update
sudo apt-get install -y chromium chromium-driver
```

PDF generation for tailored CVs and cover letters also requires `pdflatex`:

```bash
sudo apt-get install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended
pdflatex --version
```

If Ubuntu installed Chromium as a Snap, use the Snap-provided browser and
driver together:

```bash
export CHROME_BINARY=/snap/bin/chromium
export CHROMEDRIVER_PATH=/snap/bin/chromium.chromedriver
```

The launch commands check these prerequisites and return a clear error if the
browser or driver is not found. The scraper uses modern headless mode and a
temporary Chrome profile directory for VPS/server environments. If modern
headless Chromium exits before creating a WebDriver session, the scraper
automatically retries with legacy `--headless` and returns the ChromeDriver log
tail with the browser and driver paths it used.

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
- `CHROME_BINARY` (optional, for example `/usr/bin/chromium`)
- `CHROMEDRIVER_PATH` (optional, for example `/snap/bin/chromium.chromedriver`)

### 3. Add profile and target companies

Create a `knowledge` folder in the project root and fill all necessary files. Examples are in [`examples/knowledge/`](examples/knowledge/); the guide for files is in [`docs/setup-guide.md`](docs/setup-guide.md).

Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and edit it for the candidate. This private YAML file controls identity, optional candidate summary and languages, Discovery search filters, and the allowlisted structured YAML profile sections used for scoring and generated artifacts. Section examples live as `examples/knowledge/profile/*.yaml` and are referenced from `knowledge/profile.yaml.profile_sections`.

Supported profile section keys are `work_experience`, `projects`, `education`, `skills`, `public_speaking`, and `values`. Point each key at a `.yaml` file under `knowledge/profile/`; Markdown section files and a `summary` / profile-summary section are no longer supported. Discovery scoring builds its profile summary from the structured scoring sections.

Links inside profile section YAML must use HTTPS URLs. Clickable links in rendered CV PDFs are underlined. `show_on_cv` is optional and defaults to `true`; set it to `false` to exclude an item or group from the CV while keeping it available as source context. For work experience, `show_on_cv` applies at the role level.

Edit `knowledge/companies.csv` with company name + career page URL.

### 4. Run the system

Start the Telegram bot (terminal 1):

```bash
job_hunting_bot
```

Prepare one vacancy URL directly from Telegram:

```text
/prep_vacancy
```

Then send the vacancy URL to the bot. It extracts the vacancy, generates the application artifacts, and sends them back to the same chat.

Run discovery (terminal 2, cron-friendly entrypoint):

```bash
job_hunting_discover
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

Generated application files use company and position names, for example `Kraken-SeniorProductManager-CV.pdf`, `Kraken-SeniorProductManager-QA.md`, and `Kraken-SeniorProductManager-CoverLetter.pdf`.

## Data Layout

Generated files are stored under:

- `data/<YYYY-MM-DD>/vacancies/*.json`
- `data/<YYYY-MM-DD>/scores/*.json`
- `data/<YYYY-MM-DD>/applications/<vacancy_id>/...`
- `data/<YYYY-MM-DD>/discovery_coverage.csv`
- `knowledge/profile.yaml`
- `knowledge/profile/*.yaml`

## Main Commands

Activate the environment first:

```bash
source .venv/bin/activate
```

- `job_hunting_bot` — Starts the Telegram bot. Output: waits for Telegram actions and handles approvals/status updates.
- `job_hunting_discover` — Reads `knowledge/profile.yaml` and `knowledge/companies.csv`, discovers vacancies, scores them, and sends suitable roles to Telegram. Output: `data/<YYYY-MM-DD>/discovery_coverage.csv`, `data/<YYYY-MM-DD>/vacancies/`, `data/<YYYY-MM-DD>/scores/`, and application files after approval.
- `job_hunting_advisor` — Starts the Chainlit advisor UI. Output: local web chat for career/application questions.

Without activating `.venv`, prefix commands with `uv run`, for example:

```bash
uv run job_hunting_discover
```

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
