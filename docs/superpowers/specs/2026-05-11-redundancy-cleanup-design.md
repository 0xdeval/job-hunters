# Redundancy Cleanup Design Spec

**Date:** 2026-05-11
**Status:** Approved

## Objective

Clean the repository conservatively by removing redundant files/folders while preserving runtime behavior and local setup, and executing all code changes on a separate branch created from `main` after this spec is approved.

## Cleanup Strategy (Option 2)

### Phase A — Ignore generated/local junk (no deletion)

Update `.gitignore` to prevent local/generated noise from being tracked:

- `**/__pycache__/`
- `*.pyc`
- `.DS_Store`

Rationale: preserve current local hosted setup and avoid removing files that may currently exist on the developer machine.

### Phase B — Clear template leftovers

Delete only files that are both:

- proven unused by active entrypoints and tests, and
- clearly scaffold/template leftovers.

### Phase C — Docs/tooling clutter

Create a per-item candidate report and delete only items explicitly approved by the user, one by one.

## Safety Constraints

- Work on a separate branch created from `main`.
- No destructive git operations (`reset --hard`, forced checkout revert, etc.).
- Each deletion candidate in Phases B/C must include evidence before deletion.
- If any uncertainty remains, defer deletion and ask for explicit user decision.

## Redundancy Detection Method

Each candidate is evaluated with this checklist:

1. Runtime reachability from entrypoints:
   - `job_hunting.main:run_discovery`
   - `job_hunting.main:run_bot`
   - `job_hunting.main:run_advisor`
2. Test reachability from `tests/` imports/usages.
3. Indirect config binding checks (for string-based references such as CrewAI config paths).
4. Template/scaffold fingerprint checks (starter boilerplate signatures).

Deletion rule:

- Delete in Phase B only when all checks indicate `unused + scaffold/legacy`.
- Otherwise move to Phase C report and require explicit approval.

## Execution Flow

1. Create a new cleanup branch from `main` (example: `chore/redundancy-cleanup`).
2. Apply Phase A by updating `.gitignore` only.
3. Build and share the Phase B report with evidence per candidate, then delete clear cases.
4. Build and share the Phase C report, then delete only explicitly approved items.
5. Run verification gates after each deletion batch and run tests at the end.
6. Deliver with cleanup-only commits and a final deleted-paths summary.

## Verification Plan

- After each deletion batch: run targeted checks for affected modules.
- Final gate: run test suite and verify entrypoint import integrity.
- Report any non-clean result immediately; no silent cleanup retries.

## Out Of Scope

- Feature changes to Discovery/Application/Advisor behavior.
- Refactoring code that is in-use but stylistically imperfect.
- Broad reorganizations not required for redundancy cleanup.
