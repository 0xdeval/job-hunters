# Setup Guide

This guide is for people who are comfortable editing text files and using LLMs, but do not want to work with the code.

Before starting the service, fill the files in `knowledge/`. These files are the main control surface for your job search.

Example versions are available in `examples/knowledge/`.

## 1. Install The Project

Install dependencies:

```bash
pip install uv
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
job_hunting_source_companies
job_hunting_advisor
```

Without activation, use `uv run <command>`.

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

## 3. Fill Files Before Starting

The required setup files are:

```text
knowledge/
├── companies.csv
├── company-source-queries.yaml
├── profile.yaml
└── profile/
    ├── profile-summary.md
    ├── work-experience.md
    ├── personal-projects.md
    ├── education.md
    ├── skills.md
    ├── values-and-interests.md
    └── public-speaking.md
```

### `knowledge/profile.yaml`

This private file is the structured control surface for identity, Discovery search filters, and allowlisted profile evidence files. Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and edit it for the candidate.

Real `knowledge/profile.yaml` stays ignored by git. Commit only example files.

The file has three top-level sections:

- `identity` — name, preferred name, email, location, work modes, and links used in generated artifacts.
- `search` — structured Discovery filters for roles, seniority, locations, industries, salary, and dealbreakers.
- `profile_sections` — explicit links to the profile markdown files the system may use as evidence.

Good structure looks like:

```yaml
identity:
  full_name: Ada Lovelace
  preferred_name: Ada
  email: ada@example.com
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
  summary: profile/profile-summary.md
  work_experience: profile/work-experience.md
  projects: profile/personal-projects.md
  education: profile/education.md
  skills: profile/skills.md
  public_speaking: profile/public-speaking.md
  values: profile/values-and-interests.md
```

`knowledge/search-criteria.md` is deprecated. Put search controls in `knowledge/profile.yaml` under `search`.

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

Company sourcing sends each new candidate to Telegram for review. Click `Approve` to append the company to `knowledge/approved-company-candidates.csv`, or `Decline` to keep it out of discovery. The rich generated file under `data/<date>/company_candidates.csv` remains the audit log for sourced candidates and review decisions.

### `knowledge/company-source-queries.yaml`

This file controls how the company sourcing crew searches for new companies.

It does not replace your profile. It only defines search templates and ATS domains.

Useful structure:

```yaml
source_groups:
  ats_search:
    enabled: true
    domains:
      - "jobs.ashbyhq.com"
      - "job-boards.greenhouse.io"
      - "jobs.lever.co"

  web_search:
    enabled: true
    templates:
      - "{role} {seniority} {industry} remote Europe"
      - "{role} {seniority} {industry} remote EMEA"
      - "site:{domain} {role} {industry} remote"
```

Supported template variables:

- `{role}`
- `{seniority}`
- `{industry}`
- `{domain}`

The crew uses profile/search context and this query config to decide which roles, seniorities, and industries to put into these templates.

## 4. Fill Profile Files

Profile files live in:

```text
knowledge/profile/
```

Use real information. The agents use this content to score roles, evaluate company fit, and prepare application materials.

| File | What to fill |
| --- | --- |
| `profile-summary.md` | Short career summary: who you are, what you specialize in, strongest achievements. |
| `work-experience.md` | Jobs, dates, company context, responsibilities, measurable results. |
| `personal-projects.md` | Side projects, open-source work, links, tech stack, outcomes. |
| `education.md` | Education, certifications, and formal training. |
| `skills.md` | Skills, tools, domains, and working strengths. |
| `values-and-interests.md` | Topics, industries, values, work style, company traits you care about. |
| `public-speaking.md` | Talks, publications, community activity, public proof. |

Practical tips:

- Use bullet points.
- Include numbers where possible.
- Mention industries and product areas clearly.
- Do not invent achievements; the system will use this text in application materials.

## 5. Run Commands

Start Telegram bot:

```bash
job_hunting_bot
```

Use it when you want Telegram approval cards, status updates, and review notifications. Keep it running in one terminal.

Run vacancy discovery:

```bash
job_hunting_discover
```

Use it after `knowledge/companies.csv` has companies. It finds vacancies, scores them, and sends suitable vacancies to Telegram.

Output:

- `data/<YYYY-MM-DD>/vacancies/*.json`
- `data/<YYYY-MM-DD>/scores/*.json`
- `data/<YYYY-MM-DD>/applications/<vacancy_id>/` after approval

Run company sourcing:

```bash
job_hunting_source_companies
```

Use it when you want new company career-page candidates.

Output:

- `data/<YYYY-MM-DD>/company_candidates.csv`
- Telegram notification when new candidates need review

Company sourcing sends each new candidate to Telegram for review. Click `Approve` to append the company to `knowledge/approved-company-candidates.csv`, or `Decline` to keep it out of discovery. The rich generated file under `data/<date>/company_candidates.csv` remains the audit log for sourced candidates and review decisions.

Run advisor UI:

```bash
job_hunting_advisor
```

Use it when you want a local Chainlit chat interface for career/application questions.

## 6. Suggested Routine

First-time setup:

1. Fill `.env`.
2. Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and fill it.
3. Fill the markdown files referenced by `knowledge/profile.yaml.profile_sections`.
4. Add initial companies to `knowledge/companies.csv`.
5. Run `job_hunting_bot`.
6. Run `job_hunting_discover`.

Ongoing usage:

- Run `job_hunting_discover` daily or every few hours.
- Run `job_hunting_source_companies` when you want more company sources.
- Review `data/<YYYY-MM-DD>/company_candidates.csv` as the audit log.
- Approve or decline candidates directly in Telegram (`Approve` appends to `knowledge/approved-company-candidates.csv`).
- Run `job_hunting_discover` again to search vacancies from the expanded company list.

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

If company sourcing finds irrelevant companies:

- Make `knowledge/profile.yaml.search` more specific.
- Remove broad templates from `knowledge/company-source-queries.yaml`.
- Add clearer industries and exclusions.

If Telegram does not work:

- Check `TELEGRAM_BOT_TOKEN`.
- Check `TELEGRAM_CHAT_ID`.
- Start the bot with `job_hunting_bot`.
