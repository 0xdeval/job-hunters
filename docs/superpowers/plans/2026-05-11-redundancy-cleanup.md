# Redundancy Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove proven redundant code/files safely while preserving runtime behavior and local setup.

**Architecture:** Execute cleanup in three phases. Phase A is `.gitignore` hardening only. Phase B removes proven-unused template leftovers with evidence. Phase C generates a per-item clutter report and deletes only user-approved items.

**Tech Stack:** Python 3.10+, CrewAI, pytest, git, ripgrep (`rg`)

---

### Task 1: Baseline Safety And Branch Setup

**Files:**
- Modify: none
- Test: none

- [ ] **Step 1: Sync local `main` and create cleanup branch**

Run:
```bash
git switch main
git pull --ff-only
git switch -c chore/redundancy-cleanup
```
Expected: branch `chore/redundancy-cleanup` created from latest `main`.

- [ ] **Step 2: Record baseline workspace state**

Run:
```bash
git status --short
git rev-parse --short HEAD
```
Expected: clean or intentionally known local state, plus baseline SHA captured for rollback reference.

- [ ] **Step 3: Commit branch-start marker**

Run:
```bash
git commit --allow-empty -m "chore: start redundancy cleanup from main"
```
Expected: one empty commit marking the cleanup branch start.

### Task 2: Phase A - Ignore Generated/Local Junk (No Deletions)

**Files:**
- Modify: `.gitignore`
- Test: none

- [ ] **Step 1: Ensure required ignore rules exist exactly once**

Target `.gitignore` block:
```gitignore
**/__pycache__/
*.pyc
.DS_Store
```

Implementation notes:
- Keep existing ignore entries.
- If duplicates exist, keep one canonical copy.
- Do not delete local files in this phase.

- [ ] **Step 2: Verify ignore behavior without deleting files**

Run:
```bash
git check-ignore -v src/job_hunting/__pycache__/main.cpython-311.pyc
git check-ignore -v src/job_hunting/.DS_Store
```
Expected: each command returns matching `.gitignore` rule.

- [ ] **Step 3: Commit Phase A**

Run:
```bash
git add .gitignore
git commit -m "chore: harden ignore rules for local artifacts"
```
Expected: commit includes only `.gitignore` changes.

### Task 3: Phase B - Remove Proven Unused Template Leftovers

**Files:**
- Create: `docs/superpowers/reports/2026-05-11-redundancy-phase-b.md`
- Delete: `src/job_hunting/crew.py`
- Delete: `src/job_hunting/config/agents.yaml`
- Delete: `src/job_hunting/config/tasks.yaml`
- Delete: `src/job_hunting/tools/custom_tool.py`
- Test: `tests/test_cv_generator.py`, `tests/test_cover_letter_tool.py`, `tests/test_dedup_tool.py`, `tests/test_telegram_notifier.py`, `tests/test_models.py`, `tests/test_utils.py`

- [ ] **Step 1: Generate evidence report before deletion**

Create `docs/superpowers/reports/2026-05-11-redundancy-phase-b.md` with this exact structure:
```markdown
# Phase B Redundancy Evidence Report (2026-05-11)

## Candidate: src/job_hunting/crew.py
- Entrypoint reachability: none
- Test reachability: none
- Config binding relevance: none
- Template fingerprint: default CrewAI scaffold (`researcher` / `reporting_analyst`)
- Decision: delete

## Candidate: src/job_hunting/config/agents.yaml
- Entrypoint reachability: none
- Test reachability: none
- Config binding relevance: not referenced by active crews
- Template fingerprint: default scaffold roles
- Decision: delete

## Candidate: src/job_hunting/config/tasks.yaml
- Entrypoint reachability: none
- Test reachability: none
- Config binding relevance: not referenced by active crews
- Template fingerprint: default scaffold tasks
- Decision: delete

## Candidate: src/job_hunting/tools/custom_tool.py
- Entrypoint reachability: none
- Test reachability: none
- Config binding relevance: none
- Template fingerprint: default "MyCustomTool" example stub
- Decision: delete
```

- [ ] **Step 2: Verify evidence with repo queries**

Run:
```bash
rg -n "job_hunting\.crew|researcher|reporting_analyst" src tests
rg -n "src/job_hunting/config/agents.yaml|src/job_hunting/config/tasks.yaml|MyCustomTool|custom_tool" src tests
```
Expected: no runtime/test references to the four candidate files.

- [ ] **Step 3: Delete files and clean empty directory if empty**

Run:
```bash
rm src/job_hunting/crew.py
rm src/job_hunting/config/agents.yaml
rm src/job_hunting/config/tasks.yaml
rm src/job_hunting/tools/custom_tool.py
rmdir src/job_hunting/config || true
```
Expected: all four files removed; `src/job_hunting/config` removed only if empty.

- [ ] **Step 4: Run targeted regression checks**

Run:
```bash
uv run pytest tests/test_cv_generator.py tests/test_cover_letter_tool.py tests/test_dedup_tool.py tests/test_telegram_notifier.py tests/test_models.py tests/test_utils.py -q
```
Expected: all selected tests pass.

- [ ] **Step 5: Commit Phase B**

Run:
```bash
git add docs/superpowers/reports/2026-05-11-redundancy-phase-b.md src/job_hunting
git commit -m "chore: remove unused scaffold files"
```
Expected: commit contains evidence report + deletions only.

### Task 4: Phase C - Report Docs/Tooling Clutter And Gate Deletions

**Files:**
- Create: `docs/superpowers/reports/2026-05-11-redundancy-phase-c.md`
- Modify/Delete: varies by user-approved items only
- Test: varies by approved items

- [ ] **Step 1: Produce Phase C candidate report (no deletion yet)**

Create `docs/superpowers/reports/2026-05-11-redundancy-phase-c.md` as a table with one row per candidate and exact paths:
```markdown
# Phase C Redundancy Candidate Report (2026-05-11)

| Path | Category | Why potentially redundant | Reachability evidence | Risk | Recommendation |
|---|---|---|---|---|---|
| chainlit.md | docs | Possible duplicate of README operational guidance | Checked references with rg across src/tests/docs | medium | keep or delete |
| personalized-outreach/scripts/fill-template.ts | script | TS source may be unused at runtime if only JS entrypoint is executed | Checked runtime calls and tests for .ts path usage | medium | keep or delete |
```

- [ ] **Step 2: Present per-item approval request to user**

Run:
```bash
git status --short
```
Expected: only report file staged/unstaged; no candidate deleted yet.

Approval gate:
- Delete only items explicitly approved by the user.
- Keep all unapproved or uncertain items.

- [ ] **Step 3: Apply only approved deletions and verify**

Create an approval file with exact, user-approved paths:
```bash
cat > docs/superpowers/reports/2026-05-11-redundancy-phase-c-approved.txt
```
Paste one approved path per line, save, then run:
```bash
xargs -I{} rm "{}" < docs/superpowers/reports/2026-05-11-redundancy-phase-c-approved.txt
uv run pytest -q
```
Expected: tests remain green after approved deletions.

- [ ] **Step 4: Commit Phase C**

Run:
```bash
git add -A
git commit -m "chore: remove approved redundant docs/tooling items"
```
Expected: commit includes only user-approved deletions + report updates.

### Task 5: Final Verification And Delivery Summary

**Files:**
- Modify: none (unless fixes required)
- Test: full suite

- [ ] **Step 1: Run full verification**

Run:
```bash
uv run pytest -q
python -c "from job_hunting.main import run_discovery, run_bot, run_advisor; print('entrypoints import OK')"
```
Expected: tests pass and `entrypoints import OK` is printed.

- [ ] **Step 2: Generate deleted-path summary for review**

Run:
```bash
git log --oneline --decorate -n 5
git show --name-status --pretty=format: HEAD
```
Expected: recent commits clearly show cleanup-only changes.

- [ ] **Step 3: Prepare handoff note**

Include in handoff:
- Branch name
- Commits by phase
- Deleted file list
- Tests executed and result
- Explicit note that no behavior changes were introduced intentionally

## Self-Review Against Spec

- Spec coverage check:
  - Phase A `.gitignore` only: covered in Task 2.
  - Phase B evidence-first deletion for scaffold leftovers: covered in Task 3.
  - Phase C per-item explicit approval gate: covered in Task 4.
  - Verification after batches and final tests: covered in Tasks 3, 4, and 5.
  - Work on branch from `main`: covered in Task 1.
- Placeholder scan: plan contains no unresolved placeholders in commands or templates.
- Consistency check: phase naming, file paths, and commands are consistent across all tasks.
