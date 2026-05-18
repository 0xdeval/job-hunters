# Setup Guide

This guide is for people who are comfortable editing text files and using LLMs, but do not want to work with the code.

Before starting the service, fill the files in `knowledge/`. These files are the main control surface for your job search.

Example versions are available in `examples/knowledge/`.

## 1. Install The Project

Install dependencies:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
# or just
source ~/.bashrc
uv sync
source .venv/bin/activate
```

On some Intel macOS machines, `uv sync` can fail while installing the transitive `onnxruntime` dependency. This service does not use `onnxruntime` directly, so use:

```bash
uv sync --no-install-package onnxruntime
source .venv/bin/activate
```

After activation, commands are available as:

```bash
job_hunting_bot
job_hunting_discover
job_hunting_advisor
```

Without activation, use `uv run <command>`.

### Linux Server Browser Dependencies

Vacancy extraction uses Selenium with a real Chrome-compatible browser. The
Python dependency installs Selenium and downloads ChromeDriver, but the server
must also have Chrome or Chromium installed.

`job_hunting_bot` and `job_hunting_discover` check this at launch. If no browser
is found, they stop immediately with an install message instead of failing later
inside a scraping task.

On Ubuntu/Debian, install Chromium and the libraries usually needed by headless
Chrome:

```bash
sudo apt-get update
sudo apt-get install -y \
  chromium \
  fonts-liberation \
  libasound2t64 \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libcups2 \
  libdrm2 \
  libgbm1 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libxcomposite1 \
  libxdamage1 \
  libxrandr2 \
  xdg-utils
```

If your distribution uses a different binary path, set it explicitly:

```bash
export CHROME_BINARY=/usr/bin/chromium
```

For a long-running service, put the same variable in the systemd unit or shell
profile used to start the bot.

You can check the server before starting the bot:

```bash
which chromium || which chromium-browser || which google-chrome || which google-chrome-stable
```

## 2. Configure Environment Variables

Create your local environment file:

```bash
cp .env.example .env
```

Fill `.env`:

```env
OPENAI_API_BASE=https://your-llm-api-endpoint
OPENAI_API_KEY=your-api-key
MODEL=your-model-name
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
TELEGRAM_ALLOWED_USERS=
MIN_SCORE=70
CHROME_BINARY=
```

What each value means:

| Variable | Meaning |
| --- | --- |
| `OPENAI_API_BASE` | API endpoint for your LLM provider or proxy. |
| `OPENAI_API_KEY` | API key for your LLM provider or proxy. |
| `MODEL` | Model name used by the agents. |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather for the Telegram bot. |
| `TELEGRAM_CHAT_ID` | Chat where notifications should be sent. |
| `TELEGRAM_ALLOWED_USERS` | Optional comma-separated Telegram user IDs allowed to interact with the bot. |
| `MIN_SCORE` | Minimum vacancy score needed before Telegram approval is requested. |
| `CHROME_BINARY` | Optional explicit path to Chrome/Chromium, for example `/usr/bin/chromium`. |

## 3. Fill Files Before Starting

The common setup files are:

```text
knowledge/
├── companies.csv
├── profile.yaml
└── profile/
    ├── work-experience.yaml
    ├── personal-projects.yaml
    ├── education.yaml
    ├── skills.yaml
    ├── values-and-interests.yaml
    └── public-performance.yaml
```

### `knowledge/profile.yaml`

This private file is the structured control surface for identity, Discovery search filters, and allowlisted profile evidence files. Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and edit it for the candidate.

Real `knowledge/profile.yaml` stays ignored by git. Commit only example files.

The file has three top-level sections:

- `identity` — name, preferred name, email, optional candidate summary, optional languages, location, work modes, and links used in generated artifacts.
- `search` — structured Discovery filters for roles, seniority, locations, industries, optional salary, and dealbreakers.
- `profile_sections` — explicit links to the structured YAML profile section files the system may use as evidence.

Good structure looks like:

```yaml
identity:
  full_name: Ada Lovelace
  preferred_name: Ada
  email: ada@example.com
  summary: Product leader with analytics experience.
  languages: [English, Portuguese]
  location:
    base: London, UK
    work_modes: [Remote Europe]
  links:
    - key: linkedin
      label: LinkedIn
      url: https://www.linkedin.com/in/ada-lovelace/
      display: ada-lovelace
      show_on_cv: true

search:
  roles:
    primary: Product Manager
    accepted: [Product Manager, Senior Product Manager]
    excluded: []
  seniority:
    target: Senior
    accepted: [Senior, Lead]
    excluded: [Intern]
  locations:
    accepted: [Remote Europe, Portugal]
    excluded: [US-only]
  industries:
    preferred: [FinTech, AI, B2B SaaS]
  salary: "$120000+"
  dealbreakers:
    - Requires relocation

profile_sections:
  work_experience: profile/work-experience.yaml
  projects: profile/personal-projects.yaml
  education: profile/education.yaml
  skills: profile/skills.yaml
  public_speaking: profile/public-performance.yaml
  values: profile/values-and-interests.yaml
```

Supported `profile_sections` keys are `work_experience`, `projects`, `education`, `skills`, `public_speaking`, and `values`. There is no `summary` section; Discovery scoring generates its profile summary from the structured scoring sections.

Put search controls in `knowledge/profile.yaml` under `search`.

`search.salary` is optional. If present, Discovery includes it as a salary threshold. If omitted, Discovery and application generation continue without a salary constraint.

### `knowledge/companies.csv`

This file is the active list of companies used by vacancy discovery.

Format:

```csv
Company,Career page
Example Company,https://example.com/careers
Another Company,https://jobs.ashbyhq.com/another-company
```

Use one row per company.

Good career page URLs often look like:

- `https://jobs.ashbyhq.com/company`
- `https://job-boards.greenhouse.io/company`
- `https://jobs.lever.co/company`
- `https://jobs.personio.com/company`
- `https://company.com/careers`

## 4. Fill Profile Section Files

Profile files live in:

```text
knowledge/profile/
```

Use real information. The agents use this structured YAML to score roles, evaluate company fit, and prepare application materials. Copy examples from `examples/knowledge/profile/*.yaml`, keep section filenames as `.yaml`, and use HTTPS-only URLs in every `links` entry. Clickable links are underlined in rendered CV PDFs.

| File | What to fill |
| --- | --- |
| `work-experience.yaml` | Roles, company context, dates, industry, and achievements. |
| `personal-projects.yaml` | Side projects, open-source work, links, tech stack, outcomes. |
| `education.yaml` | Education, certifications, grades, and formal training. |
| `skills.yaml` | Skill groups and skills. The LLM chooses the most relevant skills for artifacts unless tailored output specifies skills. |
| `public-performance.yaml` | Talks and publications. This file is referenced by the `public_speaking` section key. |
| `values-and-interests.yaml` | Structured values and interests. |

`show_on_cv` is optional and defaults to `true`. Set it to `false` to keep source context available while excluding that item or group from the CV. For work experience, it applies at the role level.

### `work-experience.yaml`

```yaml
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period:
      start: 2022-08
      end: 2026-04
    industry: B2B SaaS
    "company_summary": Product analytics platform
    show_on_cv: true
    achievements:
      - area: Activation
        text: Grew activation by 30% through onboarding experiments.
        links:
          - label: Case study
            url: https://example.com/case-study
```

Achievement links are optional. When an achievement has multiple links, the CV renders them at the end of the sentence separated with a dot.

### `personal-projects.yaml`

```yaml
projects:
  - id: hush
    name: Hush
    title: Crypto privacy payment solution
    period:
      start: 2026-02
      end: 2026-03
    description: Privacy-focused DeFi integration for private collateral and repayments.
    show_on_cv: true
    links:
      - label: GitHub
        url: https://github.com/0xdeval/hush
    tech_stack:
      - Aave
      - Privacy Infrastructure
```

### `education.yaml`

```yaml
education:
  - id: hse-applied-math
    institution: Higher School of Economics
    degree: Bachelor's degree
    field: Computational and Applied Mathematics
    period:
      start: 2016-09
      end: 2020-06
    grade: GPA 8/10
    show_on_cv: true
    links:
      - label: Program
        url: https://example.com/program
```

### `skills.yaml`

```yaml
skill_groups:
  - name: Product
    show_on_cv: true
    skills:
      - Product strategy
      - Product discovery
      - Roadmap prioritization
  - name: Web3 / FinTech
    skills:
      - Web3
      - DeFi
      - Stablecoin payments
```

### `public-performance.yaml`

```yaml
talks:
  - id: product-summit-discovery
    conference: Example Product Summit
    title: Product discovery in regulated markets
    show_on_cv: true
    links:
      - label: Event
        url: https://example.com/product-summit

publications:
  - id: onboarding-metrics
    title: Designing onboarding metrics that teams can trust
    description: Practical onboarding measurement for product teams.
    links:
      - label: Article
        url: https://example.com/onboarding-metrics
```

### `values-and-interests.yaml`

```yaml
values:
  - id: ownership
    title: High ownership
    description: Prefers owning ambiguous product problems from discovery through launch.

interests:
  - id: privacy-preserving-products
    title: Privacy-preserving products
    description: Interested in products that make privacy usable without sacrificing compliance.
```

Practical tips:

- Use bullet points.
- Include numbers where possible.
- Mention industries and product areas clearly.
- Do not invent achievements; the system will use this structured evidence in application materials.

## 5. Run Commands

Start Telegram bot:

```bash
job_hunting_bot
```

Use it when you want Telegram approval cards, status updates, and review notifications. Keep it running in one terminal.

Prepare one vacancy URL directly from Telegram:

```text
/prep_vacancy
```

After the bot asks for a URL, send the vacancy URL in the same chat. The bot extracts the vacancy, creates a local vacancy/score record, runs application generation, sends progress updates, and returns the generated artifacts to that chat.

Run vacancy discovery:

```bash
job_hunting_discover
```

Use it after `knowledge/companies.csv` has companies. It finds vacancies, scores them, and sends suitable vacancies to Telegram.

Output:

- `data/<YYYY-MM-DD>/vacancies/*.json`
- `data/<YYYY-MM-DD>/scores/*.json`
- `data/<YYYY-MM-DD>/applications/<vacancy_id>/` after approval

Application artifact filenames use the company and role in PascalCase:

- `Kraken-SeniorProductManager-CV.pdf`
- `Kraken-SeniorProductManager-QA.md`
- `Kraken-SeniorProductManager-CoverLetter.pdf`

Run advisor UI:

```bash
job_hunting_advisor
```

Use it when you want a local Chainlit chat interface for career/application questions.

## 6. Suggested Routine

First-time setup:

1. Fill `.env`.
2. Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and fill it.
3. Fill the YAML files referenced by `knowledge/profile.yaml.profile_sections`.
4. Add initial companies to `knowledge/companies.csv`.
5. Run `job_hunting_bot`.
6. Run `job_hunting_discover`.

Ongoing usage:

- Run `job_hunting_discover` daily or every few hours.
- Edit `knowledge/companies.csv` when you want to add or remove monitored companies.

## 7. Troubleshooting

If a command is not found:

```bash
source .venv/bin/activate
```

Or run through uv:

```bash
uv run job_hunting_discover
```

If `uv sync` fails on `onnxruntime`:

```bash
uv sync --no-install-package onnxruntime
```

If nothing is found:

- Check that `knowledge/companies.csv` has valid career page URLs.
- Check that `knowledge/profile.yaml.search` is not too restrictive.
- Check that `.env` contains valid LLM and Telegram settings.

If Telegram does not work:

- Check `TELEGRAM_BOT_TOKEN`.
- Check `TELEGRAM_CHAT_ID`.
- Start the bot with `job_hunting_bot`.
