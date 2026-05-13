# Company Sourcing Telegram Approval Design Spec

**Date:** 2026-05-13
**Status:** Pending user review

## Objective

Upgrade `job_hunting_source_companies` so newly sourced company candidates are
reviewed directly in Telegram instead of requiring manual CSV status edits.

The sourcing flow should keep a rich candidate CSV for review messages and
auditability. Telegram approvals should append approved companies to a separate
lean discovery input file under `knowledge/`. Discovery should read both the
manually curated company list and the Telegram-approved sourced company list.

## Scope

In scope:

- Add rich fields needed for Telegram company review messages.
- Send one Telegram review message per new pending company candidate.
- Add Approve and Decline buttons for company candidates.
- Update the rich candidate row when a Telegram review action is clicked.
- Append approved candidates to `knowledge/approved-company-candidates.csv`.
- Keep approved sourced companies separate from `knowledge/companies.csv`.
- Make discovery load both company input CSV files.
- Dedupe discovery inputs before coverage initialization and crew kickoff.

Out of scope:

- Appending sourced approvals directly to `knowledge/companies.csv`.
- Telegram editing or deletion of already approved company records.
- Automatic application or vacancy approval for company candidates.
- Replacing the existing company sourcing crew architecture.
- Adding a web UI for reviewing company candidates.

## Data Files

The daily sourced candidate file remains:

```text
data/<YYYY-MM-DD>/company_candidates.csv
```

Its schema becomes rich enough to support Telegram review:

```csv
candidate_id,company,career_page,website,description,industry,source,match_score,match_reason,status,discovered_at,reviewed_at
```

Field responsibilities:

- `candidate_id`: stable short identifier used in Telegram callback data.
- `company`: company name shown in Telegram and used for approval output.
- `career_page`: career page URL appended to the approved discovery input.
- `website`: company website shown as a clickable Telegram link.
- `description`: short neutral company description shown in Telegram.
- `industry`: company industry or segment shown in Telegram.
- `source`: discovery source or query context.
- `match_score`: profile-fit score from the sourcing crew.
- `match_reason`: internal fit rationale for later review.
- `status`: `pending_review`, `approved`, or `declined`.
- `discovered_at`: timestamp from sourcing.
- `reviewed_at`: timestamp set by Telegram approval or decline.

Approved sourced companies are written to:

```text
knowledge/approved-company-candidates.csv
```

This file uses the same lean schema as `knowledge/companies.csv`:

```csv
Company,Career page
```

The lean approved file is the only new file discovery needs to consume.
Rich candidate details stay in `data/<YYYY-MM-DD>/company_candidates.csv`.

## Sourcing Flow

`CompanySourcingFlow.run_company_sourcing_crew` continues to run the
company-sourcing crew for the current date and verify that the daily candidate
CSV exists.

After the crew finishes, the flow identifies only newly added rows with
`status=pending_review`. It returns those candidates, not just a count, so the
notification step can send one Telegram message per new candidate.

Existing pending rows from earlier in the same file must not be resent on every
run. The flow can preserve the current before/after comparison strategy, but it
should track candidate identity rather than only a pending-row count.

If no new candidates were written, the flow prints the current no-op message and
sends no Telegram messages.

## Telegram Review Messages

Each new pending candidate receives one Telegram message with HTML parse mode.
The message includes:

- Company name
- Website link
- Career page link
- Short description
- Industry

All company-controlled or LLM-generated text is HTML-escaped. URLs are escaped
for HTML attributes. If a URL is missing, the line says it is unavailable
instead of creating a broken link.

Example message shape:

```text
New company candidate
Company: <b>Acme</b>
Website: Open website
Careers: Open career page
Industry: FinTech
Description: Builds spend management tools for startups.
```

Buttons:

- `Approve`
- `Decline`

Callback data uses a company-review namespace, separate from vacancy approval
callbacks:

```text
company_approve:<candidate_id>:<date>
company_decline:<candidate_id>:<date>
```

The callback must not include raw company names or URLs because Telegram limits
callback data length and because names/URLs can contain delimiter characters.

## Telegram Callback Handling

The existing bot authorization check continues to apply to company candidate
review callbacks.

On `company_approve`, the bot:

1. Finds the row in `data/<date>/company_candidates.csv` by `candidate_id`.
2. Updates `status` to `approved`.
3. Sets `reviewed_at`.
4. Appends `Company,Career page` to
   `knowledge/approved-company-candidates.csv` unless the company/career page is
   already present in `knowledge/companies.csv` or the approved sourced file.
5. Edits the Telegram message to show that the company was approved.

On `company_decline`, the bot:

1. Finds the row in `data/<date>/company_candidates.csv` by `candidate_id`.
2. Updates `status` to `declined`.
3. Sets `reviewed_at`.
4. Does not modify any `knowledge/` company input file.
5. Edits the Telegram message to show that the company was declined.

If the callback target cannot be found, the bot answers with a Telegram error
message and does not create or update approved company rows.

Duplicate approvals are idempotent. Re-clicking an approved candidate should not
append duplicate rows to `knowledge/approved-company-candidates.csv`.

## Discovery Integration

`DiscoveryFlow` changes from loading one company source to loading both:

```text
knowledge/companies.csv
knowledge/approved-company-candidates.csv
```

Both files use `Company` and `Career page` columns. Missing
`knowledge/approved-company-candidates.csv` is normal and should not be treated
as an error.

Discovery dedupes loaded rows before coverage initialization and crew kickoff.
The dedupe key should use normalized company name plus normalized career page so
the same source is not scraped twice when a company appears in both files.

After dedupe, the flow preserves the existing deterministic contract:

- initialize coverage for the companies that will be attempted
- invoke the discovery crew once per company
- record Python-level `failed` rows when a per-company crew kickoff raises
- continue scanning historical pending score files for Telegram vacancy approval

## Testing

Use TDD for implementation.

Add or update tests proving:

- candidate rows include `candidate_id` and `description`
- candidate IDs are stable and compact enough for Telegram callback data
- only newly added pending candidates are sent to Telegram
- company review messages use HTML parse mode
- company review messages render website and career-page URLs as links
- company review message text is HTML-escaped
- `company_approve` updates the rich candidate row and sets `reviewed_at`
- `company_approve` appends `Company,Career page` to
  `knowledge/approved-company-candidates.csv`
- duplicate approvals do not append duplicate discovery rows
- approvals do not append companies already present in `knowledge/companies.csv`
- `company_decline` updates only the rich candidate row
- invalid company callback targets do not create approved company rows
- discovery loads curated companies plus approved sourced companies
- discovery accepts a missing approved sourced company file
- discovery dedupes overlapping curated and approved sourced companies

Verification target:

```bash
uv run pytest
```

## Acceptance Criteria

- `job_hunting_source_companies` sends each new pending company candidate to
  Telegram for review.
- Telegram company messages include company name, website, career-page link,
  short description, and industry.
- Telegram company messages use HTML parse mode and safe escaping.
- Approving a company updates the rich candidate row and appends a lean row to
  `knowledge/approved-company-candidates.csv`.
- Declining a company updates the rich candidate row without changing
  discovery input files.
- The rich candidate CSV remains the review/audit record.
- `knowledge/companies.csv` remains manually curated and is not modified by
  Telegram company approvals.
- Discovery reads both curated and approved sourced company files.
- Discovery does not process duplicate company/career-page inputs twice.
- The full test suite passes in the prepared environment.
