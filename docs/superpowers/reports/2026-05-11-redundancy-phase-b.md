# Redundancy Cleanup Phase B — Evidence Report (2026-05-11)

- Status: DONE_WITH_CONCERNS

## What you changed

- Documented reachability and template evidence for the four Phase B candidates.
- Removed proven unused template leftovers:
  - `src/job_hunting/crew.py`
  - `src/job_hunting/config/agents.yaml`
  - `src/job_hunting/config/tasks.yaml`
  - `src/job_hunting/tools/custom_tool.py`
- Removed now-empty directory with `rmdir src/job_hunting/config || true`.

## Candidate Evidence

| Candidate | Entrypoint reachability | Test reachability | Config binding relevance | Template fingerprint | Decision |
| --- | --- | --- | --- | --- | --- |
| `src/job_hunting/crew.py` | No runtime imports from `src/job_hunting/main.py` or flows. Active runtime uses `job_hunting.crews.discovery.crew` and `job_hunting.crews.application.crew`. | No matches in `tests/` for `job_hunting.crew` or `JobHunting`. | Binds to `self.agents_config['researcher']`, `self.agents_config['reporting_analyst']`, `self.tasks_config['research_task']`, `self.tasks_config['reporting_task']` that are not part of active crew configs. | Canonical CrewAI scaffold comments and placeholder research/reporting duo. | Remove |
| `src/job_hunting/config/agents.yaml` | Not referenced by entrypoints or active flows; active crews resolve `config/agents.yaml` within per-crew folders under `src/job_hunting/crews/*/config`. | No tests reference this top-level file path. | Defines `researcher` / `reporting_analyst` only, which align to unused scaffold crew file. | Generic `{topic} Senior Data Researcher` and `Reporting Analyst` template copy. | Remove |
| `src/job_hunting/config/tasks.yaml` | Not referenced by entrypoints or active flows. | No tests reference this top-level file path. | Defines `research_task` / `reporting_task` for unused scaffold agents only. | Generic "Conduct a thorough research about {topic}" and "fully fledged report" template task text. | Remove |
| `src/job_hunting/tools/custom_tool.py` | No imports from runtime modules, flows, or crew definitions. | No tests reference `custom_tool` or `MyCustomTool`. | No bindings to active config/task pipelines. | Stock CrewAI example class (`MyCustomTool`, `_run` returns example placeholder text). | Remove |

## Evidence query summary

Executed required queries:

- `rg -n "job_hunting\.crew|researcher|reporting_analyst" src tests`
- `rg -n "src/job_hunting/config/agents.yaml|src/job_hunting/config/tasks.yaml|MyCustomTool|custom_tool" src tests`

Observed:

- Hits for `researcher`/`reporting_analyst` and `job_hunting.crew` occur in scaffold files themselves plus the unused top-level YAML pair.
- Active flow imports target `src/job_hunting/crews/discovery/crew.py` and `src/job_hunting/crews/application/crew.py`, not `src/job_hunting/crew.py`.
- `MyCustomTool`/`custom_tool` appear only in `src/job_hunting/tools/custom_tool.py`.

## Test command + results

- Command:
  - `uv run pytest tests/test_cv_generator.py tests/test_cover_letter_tool.py tests/test_dedup_tool.py tests/test_telegram_notifier.py tests/test_models.py tests/test_utils.py -q`
- Result:
  - Command executed but environment-blocked before test collection:
    - `error: Distribution onnxruntime==1.26.0 ... doesn't have a source distribution or wheel for macosx_26_0_x86_64`

## Commit SHA

- Pending at report creation time.

## Files changed

- `docs/superpowers/reports/2026-05-11-redundancy-phase-b.md`
- `src/job_hunting/crew.py` (deleted)
- `src/job_hunting/config/agents.yaml` (deleted)
- `src/job_hunting/config/tasks.yaml` (deleted)
- `src/job_hunting/tools/custom_tool.py` (deleted)
