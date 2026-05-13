# Discovery Coverage Loop Reliability Design Spec

**Date:** 2026-05-12
**Status:** Pending user review

## Objective

Make discovery coverage deterministic by moving company iteration out of the
LLM-controlled `vacancy_scout` task and into `DiscoveryFlow`.

The discovery crew should process exactly one company per kickoff. Python code
should own the full company list, initialize coverage, invoke the crew per
company, and record a deterministic terminal coverage status for each company
that finishes or fails inside the flow.

## Problem

The current discovery task asks `vacancy_scout` to read
`knowledge/companies.csv` and loop through every company. In longer runs, the
agent can stop before full coverage, invent batching concepts such as run
windows, or hit CrewAI iteration limits. Rows such as `not_attempted` or
`skipped` with "Skipped in this run window before scraping" mean the target
company was never scraped.

Increasing `max_iter` only treats the symptom. The long procedural loop must
not be owned by an LLM task.

## Scope

In scope:

- Make `DiscoveryFlow` read `knowledge/companies.csv`.
- Initialize `data/<today>/discovery_coverage.csv` from the company list.
- Invoke the discovery crew once per company with `today`, `company`, and
  `career_page`.
- Record `failed` from Python when a per-company crew kickoff raises.
- Rewrite the scout task prompt so it handles exactly one company per run.
- Replace tests that encode the old max-iteration architecture.

Out of scope:

- Replacing CrewAI for vacancy scraping or scoring.
- Changing Telegram approval behavior.
- Changing vacancy and score JSON schemas.
- Adding concurrency for per-company crew runs.
- Automatically recovering from process-level external interruption.

## Architecture

`DiscoveryFlow.run_discovery_crew` becomes the deterministic orchestrator:

```text
today
  -> ensure data/<today>/vacancies and data/<today>/scores exist
  -> read knowledge/companies.csv
  -> initialize data/<today>/discovery_coverage.csv as not_attempted rows
  -> for each company row:
       DiscoveryCrew().crew().kickoff({
         "today": today,
         "company": company,
         "career_page": career_page
       })
       if kickoff raises:
         DiscoveryCoverageStore(today).record(..., status="failed")
  -> scan historical pending scores for Telegram approval
```

The crew remains sequential internally. The scout task scrapes one company and
returns saved vacancy IDs for that company. The fit analyst scores the vacancy
IDs returned by that one scout task.

## Coverage Contract

`DiscoveryCoverageStore.initialize_from_companies()` keeps `not_attempted` as
the initial template state.

`DiscoveryCoverageTool` remains restricted to recordable terminal statuses:

- `completed`: the provided career page was evaluated successfully, even if no
  jobs matched the search criteria.
- `skipped`: the provided career page cannot be evaluated as a usable career
  page for that company.
- `failed`: scraping, tool execution, or the per-company crew run failed.

Every `failed` row must include a human-readable failure reason in `notes`.
The reason should be short enough for CSV review but specific enough to act on,
for example `Crew kickoff failed: TimeoutError while scraping career page`.

`not_attempted` must not be accepted by `DiscoveryCoverageTool`. At the end of a
normal `DiscoveryFlow` run, no `not_attempted` rows should remain. If the whole
Python process is interrupted externally, the last unprocessed rows may remain
`not_attempted`; that is the only expected exception.

## Prompt Changes

The `scrape_vacancies_task` prompt should use the provided `{company}` and
`{career_page}` inputs. It must not instruct the scout to read
`knowledge/companies.csv` or loop over all companies.

The prompt must not mention run windows, batching, or marking companies as
skipped because there was not enough time. It should clearly state that this
crew kickoff is responsible for one company only.

## Error Handling

If the per-company crew kickoff raises, `DiscoveryFlow` catches the exception
and records:

```text
status=failed
jobs_found=0
matched_jobs=0
notes=<short exception type and message>
```

The flow then continues with the next company. A single failing company should
not prevent the remaining companies from being attempted.

If the scout records `failed` through `DiscoveryCoverageTool`, it must provide a
specific reason in `notes`, such as an HTTP error, Selenium timeout, unsupported
page structure, or missing career page content. Generic notes such as `failed`,
`error`, or an empty string are not acceptable for failed statuses.

If the company CSV is missing, the initialized coverage file is header-only and
the flow performs no per-company crew calls. Existing historical pending-score
scanning still runs.

## Testing

Use TDD for implementation.

Add or update tests proving:

- `DiscoveryFlow` reads every company row and invokes the discovery crew once
  per company.
- A successful per-company crew run can leave a `completed` coverage row.
- A per-company exception records `failed` and the loop continues.
- `failed` rows include a non-empty, actionable reason in `notes`.
- `DiscoveryCoverageTool` rejects `not_attempted`.
- The scout task prompt describes one company per run and does not instruct the
  scout to read or loop through `knowledge/companies.csv`.
- The old max-iteration budget test is removed or replaced because max iteration
  count no longer defines coverage reliability.

Verification target:

```bash
uv run pytest
```

On macOS x86_64, the project may require the documented setup workaround before
tests can run:

```bash
uv sync --no-install-package onnxruntime
uv run --no-sync pytest
```

## Acceptance Criteria

- Running discovery no longer depends on one LLM agent completing the whole
  company list.
- Each crew kickoff receives one company and one career page.
- The scout no longer reads `knowledge/companies.csv`.
- Coverage distinguishes `completed`, `failed`, and genuine `skipped`.
- Failed coverage rows explain why the company failed in the `notes` column.
- No prompt text can produce "Skipped in this run window before scraping".
- Normal flow completion leaves no `not_attempted` rows.
- The full test suite passes in the prepared environment.
