# Phase C Redundancy Candidate Report (2026-05-11)

| Path | Category | Why potentially redundant | Reachability evidence | Risk | Recommendation |
|---|---|---|---|---|---|
| chainlit.md | docs | Potentially duplicative with root README advisor usage notes, but this file may still be consumed by Chainlit convention/runtime behavior. | `rg -n "chainlit\.md" src tests README.md chainlit.md personalized-outreach` returned no references from runtime code/tests; this is not sufficient to prove convention-based non-usage. | medium | Conservative: keep unless a runtime validation confirms Chainlit behavior is unchanged without this file. |
| personalized-outreach/scripts/fill-template.ts | script | TS source looks like a parallel/legacy implementation while runtime path and tests target JS script. | `rg -n "fill-template\.ts" src tests README.md chainlit.md personalized-outreach` matched only self-reference in `fill-template.ts`; `rg -n "fill-template\.js|SCRIPT_PATH" src tests README.md chainlit.md personalized-outreach` shows active JS wiring in `src/job_hunting/tools/cv_generator.py` and tests. | medium | Candidate for deletion after confirming no local TS editing/build workflow depends on it. |
| personalized-outreach/README.md | docs | Possible documentation overlap with root README and `personalized-outreach/SKILL.md`. | `rg -n "personalized-outreach/README\.md|/personalized-outreach" src tests README.md chainlit.md personalized-outreach` only matches lines inside `personalized-outreach/README.md`; no runtime/test reference discovered. | low | Candidate to consolidate into `SKILL.md`/root README; delete only if maintainers confirm no separate audience. |
| .chainlit/translations/*.json | config | Could be clutter for a single-language setup, but these are convention-loaded localization assets and may be used dynamically. | `rg -n "\.chainlit/translations|translations/.*\.json|ar-SA\.json|pt-PT\.json" src tests README.md chainlit.md personalized-outreach` returned no code/test references; `git ls-files .chainlit/translations/*.json \| wc -l` shows 23 tracked locale files. | high | Conservative: keep by default; only prune after runtime validation of language fallback and explicit supported-locale policy. |

## Evidence Snapshot

### 1) `chainlit.md`

Command:
```bash
rg -n "chainlit\.md" src tests README.md chainlit.md personalized-outreach || true
```
Summary:
- No matches were returned.
- This indicates no explicit code/test reference in searched scopes, but does not rule out convention-based runtime usage.

### 2) `personalized-outreach/scripts/fill-template.ts`

Commands:
```bash
rg -n "fill-template\.ts" src tests README.md chainlit.md personalized-outreach || true
rg -n "fill-template\.js|SCRIPT_PATH" src tests README.md chainlit.md personalized-outreach || true
```
Summary:
- `fill-template.ts` search returned only one self-reference line in `personalized-outreach/scripts/fill-template.ts` (usage text).
- `fill-template.js|SCRIPT_PATH` search returned active references in:
  - `src/job_hunting/tools/cv_generator.py`
  - `tests/test_cv_generator.py`
  - `personalized-outreach/SKILL.md`
- Evidence supports JS as the active path and TS as potentially redundant.

### 3) `personalized-outreach/README.md`

Command:
```bash
rg -n "personalized-outreach/README\.md|/personalized-outreach" src tests README.md chainlit.md personalized-outreach || true
```
Summary:
- Matches were found only inside `personalized-outreach/README.md` itself.
- No runtime code or tests reference this file in searched scopes.

### 4) `.chainlit/translations/*.json`

Commands:
```bash
rg -n "\.chainlit/translations|translations/.*\.json|ar-SA\.json|pt-PT\.json" src tests README.md chainlit.md personalized-outreach || true
git ls-files .chainlit/translations/*.json | wc -l
git ls-files .chainlit/translations/*.json
```
Summary:
- No matches in runtime/test/docs scopes searched for explicit references.
- 23 translation JSON files are tracked under `.chainlit/translations/`.
- Because these are convention-loaded assets, zero grep references is not proof of non-usage.

No deletions performed pending user approval.
