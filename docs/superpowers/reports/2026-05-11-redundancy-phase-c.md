# Phase C Redundancy Candidate Report (2026-05-11)

## Risk Rubric

- `low`: no runtime path dependency and minimal operational impact expected.
- `medium`: likely safe but there is workflow/documentation uncertainty.
- `high`: convention/runtime-loaded asset or unclear behavior impact.

| Path | Category | Why potentially redundant | Reachability evidence | Risk | Recommendation |
|---|---|---|---|---|---|
| `chainlit.md` | docs | Possibly duplicative with root `README.md` usage notes, but may be conventionally consumed by Chainlit UX. | No direct code/test references via grep; no explicit config pointer found in searched scopes. | high | Keep by default. Delete only if a runtime check shows Chainlit startup and welcome/onboarding behavior unchanged without this file. |
| `personalized-outreach/scripts/fill-template.ts` | script | Looks like TS source parallel to active JS runtime entrypoint. | `fill-template.ts` found only in self usage string; active references point to `fill-template.js` in runtime/test paths. | medium | Candidate for deletion if team confirms no TS editing/build workflow depends on this file. |
| `personalized-outreach/README.md` | docs | Potential overlap with root README and `personalized-outreach/SKILL.md`. | No runtime/test references; references are self-contained inside this README. | medium | Keep unless maintainers explicitly confirm this standalone README has no separate audience. |
| `.chainlit/translations/*.json` | config | Large locale set could be clutter in single-language operation, but these are convention-loaded assets. | 23 locale files tracked; no direct code/test references found, which is not proof of non-usage for convention-loaded content. | high | Keep by default. Delete only with an explicit supported-locales policy and runtime validation of fallback behavior. |

## Evidence Snapshot

### Command A

```bash
rg -n "chainlit\.md" src tests README.md chainlit.md personalized-outreach || true
```

Output:
```text
(no matches)
```

### Command B

```bash
rg -n "fill-template\.ts" src tests README.md chainlit.md personalized-outreach || true
```

Output:
```text
personalized-outreach/scripts/fill-template.ts:187:    console.error("Usage: npx ts-node fill-template.ts <template> <data.json> <output.tex>");
```

### Command C

```bash
rg -n "fill-template\.js|SCRIPT_PATH" src tests README.md chainlit.md personalized-outreach || true
```

Output:
```text
personalized-outreach/scripts/fill-template.js:692:      "Usage: node fill-template.js <template.tex> <tailored-data.json> <output.tex> <profile-dir>"
personalized-outreach/scripts/fill-template.js:694:    console.error("Example: node fill-template.js cv-template.md data.json output.tex profile/")
tests/test_cv_generator.py:33:        assert "fill-template.js" in " ".join(first_call_args)
personalized-outreach/SKILL.md:104:2. **Fill LaTeX template** using `scripts/fill-template.js`
personalized-outreach/SKILL.md:177:### Step 2: Run fill-template.js Script
personalized-outreach/SKILL.md:182:mkdir -p .tmp && node personalized-outreach/scripts/fill-template.js \
personalized-outreach/SKILL.md:284:- **LaTeX characters:** Automatically escaped by fill-template.js (% → \%, $ → \$, etc.)
personalized-outreach/SKILL.md:376:   - **CV:** Read `best-practices/cv.md` → Generate JSON → Run `fill-template.js` → Output filled `.tex` file
src/job_hunting/tools/cv_generator.py:10:SCRIPT_PATH = PROJECT_ROOT / "personalized-outreach/scripts/fill-template.js"
src/job_hunting/tools/cv_generator.py:44:                str(SCRIPT_PATH),
```

### Command D

```bash
rg -n "personalized-outreach/README\.md|/personalized-outreach" src tests README.md chainlit.md personalized-outreach || true
```

Output:
```text
personalized-outreach/README.md:62:/personalized-outreach
personalized-outreach/README.md:156:2. Invoke `/personalized-outreach`
```

### Command E

```bash
rg -n "\.chainlit/translations|translations/.*\.json|ar-SA\.json|pt-PT\.json" src tests README.md chainlit.md personalized-outreach || true
```

Output:
```text
(no matches)
```

### Command F

```bash
git ls-files .chainlit/translations/*.json | wc -l
git ls-files .chainlit/translations/*.json
```

Output:
```text
23
.chainlit/translations/ar-SA.json
.chainlit/translations/bn.json
.chainlit/translations/da-DK.json
.chainlit/translations/de-DE.json
.chainlit/translations/el-GR.json
.chainlit/translations/en-US.json
.chainlit/translations/es.json
.chainlit/translations/fr-FR.json
.chainlit/translations/gu.json
.chainlit/translations/he-IL.json
.chainlit/translations/hi.json
.chainlit/translations/it.json
.chainlit/translations/ja.json
.chainlit/translations/kn.json
.chainlit/translations/ko.json
.chainlit/translations/ml.json
.chainlit/translations/mr.json
.chainlit/translations/nl.json
.chainlit/translations/pt-PT.json
.chainlit/translations/ta.json
.chainlit/translations/te.json
.chainlit/translations/zh-CN.json
.chainlit/translations/zh-TW.json
```

## Deletion Gates (Explicit)

- `chainlit.md`: delete only after running the advisor UI and confirming no onboarding/welcome regression.
- `personalized-outreach/scripts/fill-template.ts`: delete only after maintainer confirms there is no TS-based local workflow.
- `personalized-outreach/README.md`: delete only after maintainer confirms documentation can be consolidated without losing intended audience.
- `.chainlit/translations/*.json`: delete only after an explicit locale policy is set and runtime fallback is validated.

No deletions performed pending user approval.
