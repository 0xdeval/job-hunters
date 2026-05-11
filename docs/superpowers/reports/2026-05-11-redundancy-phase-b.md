# Phase B Redundancy Evidence Report (2026-05-11)

## Candidate: src/job_hunting/crew.py
- Entrypoint reachability: No runtime imports from `src/job_hunting/main.py` or active flows; active runtime uses `job_hunting.crews.discovery.crew` and `job_hunting.crews.application.crew`.
- Test reachability: No references in `tests/` to `job_hunting.crew` or `JobHunting`.
- Config binding relevance: Binds to scaffold-only keys `researcher`, `reporting_analyst`, `research_task`, and `reporting_task` not used by active crews.
- Template fingerprint: Canonical CrewAI starter with `JobHunting` class and placeholder comments around research/reporting setup.
- Decision: delete

## Candidate: src/job_hunting/config/agents.yaml
- Entrypoint reachability: Not imported by runtime entrypoints or active flows; active crews use per-crew config files under `src/job_hunting/crews/*/config`.
- Test reachability: No test references to this top-level YAML path.
- Config binding relevance: Defines `researcher` and `reporting_analyst` for the unused scaffold crew only.
- Template fingerprint: Generic placeholder roles/goals with `{topic}` interpolation and stock CrewAI prose.
- Decision: delete

## Candidate: src/job_hunting/config/tasks.yaml
- Entrypoint reachability: Not imported by runtime entrypoints or active flows.
- Test reachability: No test references to this top-level YAML path.
- Config binding relevance: Defines `research_task` and `reporting_task` for scaffold-only agents.
- Template fingerprint: Generic starter tasks (“Conduct a thorough research about {topic}”, “fully fledged report” wording).
- Decision: delete

## Candidate: src/job_hunting/tools/custom_tool.py
- Entrypoint reachability: No runtime imports from flows, crews, or entrypoints.
- Test reachability: No references in tests to `custom_tool` or `MyCustomTool`.
- Config binding relevance: No bindings into active crew/task configuration.
- Template fingerprint: Stock CrewAI custom tool example with placeholder description and `_run` returning example text.
- Decision: delete

## Targeted Test Verification
- Command 1: `uv run pytest tests/test_cv_generator.py tests/test_cover_letter_tool.py tests/test_dedup_tool.py tests/test_telegram_notifier.py tests/test_models.py tests/test_utils.py -q`
- Outcome 1: Failed during dependency resolution with `onnxruntime==1.26.0` wheel incompatibility for `macosx_26_0_x86_64`.
- Command 2 (fallback): `./.venv/bin/pytest tests/test_cv_generator.py tests/test_cover_letter_tool.py tests/test_dedup_tool.py tests/test_telegram_notifier.py tests/test_models.py tests/test_utils.py -q`
- Outcome 2: Failed immediately because `./.venv/bin/pytest` does not exist in this workspace.
