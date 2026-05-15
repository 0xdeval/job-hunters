# Unified Profile YAML Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private `knowledge/profile.yaml` contract, use it to drive Discovery and Application crew context, and remove person-specific hardcoding from generated CV and cover letter artifacts.

**Architecture:** Add a focused profile context module that validates `profile.yaml`, builds Discovery/Application context slices, and keeps crew-specific section policies in code. Update crew prompts to consume prepared context instead of hardcoded file reads, then update current CV/cover-letter renderers to consume structured identity and section availability while keeping the Node CV renderer in phase 1.

**Tech Stack:** Python 3.10+, PyYAML, CrewAI YAML task configs, pytest, current Node `personalized-outreach/scripts/fill-template.js`, LaTeX templates.

---

## File Structure

- Create `src/job_hunting/profile_context.py`
  - Owns `profile.yaml` loading, validation, allowed section keys, and deterministic context building.
  - Exposes `load_profile_config`, `build_discovery_context`, and `build_application_context`.
- Create `tests/test_profile_context.py`
  - Tests YAML parsing, validation failures, Discovery context, Application context, and example profile validity.
- Create `examples/knowledge/profile.yaml`
  - Public template users copy to private `knowledge/profile.yaml`.
- Create `examples/knowledge/profile/education.md`
  - Moves example education/certification facts out of `general-info.md`.
- Create `examples/knowledge/profile/skills.md`
  - Example first-class skills section.
- Modify `README.md` and `docs/setup-guide.md`
  - Document `profile.yaml`, deprecate `search-criteria.md`, and clarify real `knowledge/` stays private.
- Modify `src/job_hunting/flows/discovery_flow.py`
  - Build Discovery context once and pass `discovery_filter_context` to crew kickoff.
- Modify `src/job_hunting/crews/discovery/config/tasks.yaml`
  - Replace `knowledge/search-criteria.md` instructions with prepared context inputs.
- Modify `tests/test_discovery_crew_config.py`
  - Assert prompts use new context and no longer mention `search-criteria.md`.
- Modify `src/job_hunting/flows/application_flow.py`
  - Build Application context and pass it into Application crew kickoff.
- Modify `src/job_hunting/crews/application/config/tasks.yaml`
  - Replace hardcoded profile file reads with `application_profile_context`.
- Create `tests/test_application_flow.py`
  - Assert ApplicationFlow passes prepared profile context into ApplicationCrew kickoff.
- Modify `src/job_hunting/tools/cv_generator.py`
  - Pass profile YAML path to Node renderer.
- Modify `personalized-outreach/scripts/fill-template.js`
  - Read `profile.yaml`, render identity/links/education/public-speaking from structured config and allowlisted files, remove special-case injections.
- Modify `personalized-outreach/templates/cv-template.md`
  - Replace hardcoded public speaking and education blocks with placeholders.
- Modify `tests/test_cv_generator.py`
  - Add synthetic profile tests proving no Mike-specific strings leak into CV `.tex`.
- Modify `src/job_hunting/tools/cover_letter_tool.py`
  - Render signature from profile identity.
- Modify `personalized-outreach/templates/cover-letter.md`
  - Replace hardcoded signature with `==SIGNATURE==`.
- Modify `tests/test_cover_letter_tool.py`
  - Add synthetic profile signature test.

## Task 1: Profile YAML Template and Context Loader

**Files:**
- Create: `examples/knowledge/profile.yaml`
- Create: `examples/knowledge/profile/education.md`
- Create: `examples/knowledge/profile/skills.md`
- Create: `src/job_hunting/profile_context.py`
- Create: `tests/test_profile_context.py`

- [ ] **Step 1: Add failing tests for example YAML and validation**

Create `tests/test_profile_context.py`:

```python
from pathlib import Path

import pytest

from job_hunting.profile_context import (
    ProfileConfigError,
    build_application_context,
    build_discovery_context,
    load_profile_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_loads_example_profile_yaml():
    config = load_profile_config(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert config.identity.full_name == "Alex Candidate"
    assert config.identity.preferred_name == "Alex"
    assert config.identity.links[0].key == "linkedin"
    assert config.search.roles.primary == "Product Manager"
    assert config.profile_sections["skills"] == Path("profile/skills.md")


def test_rejects_unknown_profile_section_key(tmp_path):
    profile_yaml = tmp_path / "profile.yaml"
    profile_yaml.write_text(
        """
identity:
  full_name: Alex Candidate
  preferred_name: Alex
  email: alex@example.com
  location:
    base: Lisbon, Portugal
    work_modes: [Remote]
  links: []
search:
  roles:
    primary: Product Manager
    accepted: [Product Manager]
    excluded: []
  seniority:
    target: Senior
    accepted: [Senior]
    excluded: []
  locations:
    accepted: [Remote]
    excluded: []
  industries:
    preferred: [SaaS]
  salary: "$120000+"
  dealbreakers: []
profile_sections:
  unsupported: profile/unsupported.md
""",
        encoding="utf-8",
    )

    with pytest.raises(ProfileConfigError, match="unsupported profile_sections key: unsupported"):
        load_profile_config(profile_yaml)


def test_discovery_context_uses_search_and_system_owned_scoring_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile-summary.md").write_text("Senior PM with fintech and AI experience.", encoding="utf-8")
    (profile_dir / "skills.md").write_text("- Product strategy\n- SQL\n", encoding="utf-8")
    (profile_dir / "work-experience.md").write_text("## Acme -- Senior Product Manager\n\n- Grew activation by 30%.", encoding="utf-8")
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        """
identity:
  full_name: Alex Candidate
  preferred_name: Alex
  email: alex@example.com
  location:
    base: Lisbon, Portugal
    work_modes: [Remote, Remote Europe]
  links: []
search:
  roles:
    primary: Product Manager
    accepted: [Product Manager, AI Product Manager]
    excluded: [Project Manager]
  seniority:
    target: Senior
    accepted: [Senior, Lead]
    excluded: [Junior]
  locations:
    accepted: [Remote, Remote Europe, Lisbon]
    excluded: [US-only remote]
  industries:
    preferred: [FinTech, AI, SaaS]
  salary: "$120000+"
  dealbreakers: [Requires relocation outside Portugal]
profile_sections:
  summary: profile/profile-summary.md
  skills: profile/skills.md
  work_experience: profile/work-experience.md
""",
        encoding="utf-8",
    )

    context = build_discovery_context(profile_yaml)

    assert "Product Manager" in context.filter_context
    assert "US-only remote" in context.filter_context
    assert "Senior PM with fintech" in context.scoring_context
    assert "Product strategy" in context.scoring_context
    assert "Grew activation by 30%" in context.scoring_context


def test_application_context_reads_only_allowlisted_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile-summary.md").write_text("Approved summary.", encoding="utf-8")
    (profile_dir / "hidden.md").write_text("Hidden fact.", encoding="utf-8")
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        """
identity:
  full_name: Alex Candidate
  preferred_name: Alex
  email: alex@example.com
  location:
    base: Lisbon, Portugal
    work_modes: [Remote]
  links: []
search:
  roles:
    primary: Product Manager
    accepted: [Product Manager]
    excluded: []
  seniority:
    target: Senior
    accepted: [Senior]
    excluded: []
  locations:
    accepted: [Remote]
    excluded: []
  industries:
    preferred: [SaaS]
  salary: "$120000+"
  dealbreakers: []
profile_sections:
  summary: profile/profile-summary.md
""",
        encoding="utf-8",
    )

    context = build_application_context(profile_yaml)

    assert "Alex Candidate" in context.identity_context
    assert "Approved summary." in context.profile_sections_context
    assert "Hidden fact." not in context.profile_sections_context
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run --no-sync pytest tests/test_profile_context.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'job_hunting.profile_context'`.

- [ ] **Step 3: Add example profile files**

Create `examples/knowledge/profile.yaml`:

```yaml
identity:
  full_name: Alex Candidate
  preferred_name: Alex
  email: alex@example.com
  location:
    base: Lisbon, Portugal
    work_modes:
      - Remote
      - Remote Europe
      - Hybrid Lisbon
  links:
    - key: linkedin
      label: LinkedIn
      url: https://www.linkedin.com/in/alex-candidate/
      display: alex-candidate
      show_on_cv: true
    - key: github
      label: GitHub
      url: https://github.com/alexcandidate
      display: alexcandidate
      show_on_cv: true

search:
  roles:
    primary: Product Manager
    accepted:
      - Product Manager
      - AI Product Manager
      - Crypto Product Manager
    excluded:
      - Product Owner
      - Project Manager
  seniority:
    target: Senior
    accepted:
      - Middle
      - Senior
      - Lead
      - Staff
      - Associate
    excluded:
      - Intern
      - Junior
      - Director
  locations:
    accepted:
      - Remote
      - Remote Europe
      - Portugal
      - Lisbon
      - Spain Remote
    excluded:
      - US-only remote
      - Canada-only remote
      - Non-Portugal hybrid
  industries:
    preferred:
      - FinTech
      - AI
      - Crypto
      - SaaS
  salary: "$120000+"
  dealbreakers:
    - Requires relocation outside Portugal
    - Requires onsite outside Lisbon

profile_sections:
  summary: profile/profile-summary.md
  work_experience: profile/work-experience.md
  projects: profile/personal-projects.md
  education: profile/education.md
  skills: profile/skills.md
  public_speaking: profile/public-speaking.md
  values: profile/values-and-interests.md
```

Create `examples/knowledge/profile/education.md`:

```markdown
# Education

## University of Example

**Degree:** Bachelor's degree, Applied Mathematics
**Period:** 2016 - 2020

### Details

- GPA 8/10

## Certifications

- Product Analytics Certificate — Example Institute
```

Create `examples/knowledge/profile/skills.md`:

```markdown
# Skills

## Product

- Product strategy
- Roadmapping
- Discovery
- Experimentation

## Technical

- SQL
- Analytics
- API products

## Domain

- FinTech
- AI
- SaaS
```

- [ ] **Step 4: Implement `profile_context.py`**

Create `src/job_hunting/profile_context.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ALLOWED_PROFILE_SECTION_KEYS = {
    "summary",
    "work_experience",
    "projects",
    "education",
    "skills",
    "public_speaking",
    "values",
}

DISCOVERY_SCORING_SECTIONS = ("summary", "skills", "work_experience")


class ProfileConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LinkConfig:
    key: str
    label: str
    url: str
    display: str
    show_on_cv: bool = False


@dataclass(frozen=True)
class IdentityConfig:
    full_name: str
    preferred_name: str
    email: str
    location_base: str
    work_modes: tuple[str, ...]
    links: tuple[LinkConfig, ...]


@dataclass(frozen=True)
class RoleSearchConfig:
    primary: str
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class SenioritySearchConfig:
    target: str
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class LocationsSearchConfig:
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class IndustriesSearchConfig:
    preferred: tuple[str, ...]


@dataclass(frozen=True)
class SearchConfig:
    roles: RoleSearchConfig
    seniority: SenioritySearchConfig
    locations: LocationsSearchConfig
    industries: IndustriesSearchConfig
    salary: str
    dealbreakers: tuple[str, ...]


@dataclass(frozen=True)
class ProfileConfig:
    path: Path
    root_dir: Path
    identity: IdentityConfig
    search: SearchConfig
    profile_sections: dict[str, Path]


@dataclass(frozen=True)
class DiscoveryProfileContext:
    filter_context: str
    scoring_context: str


@dataclass(frozen=True)
class ApplicationProfileContext:
    identity_context: str
    profile_sections_context: str
    section_keys: tuple[str, ...]


def load_profile_config(path: Path | str = "knowledge/profile.yaml") -> ProfileConfig:
    profile_path = Path(path)
    try:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ProfileConfigError(f"profile config not found: {profile_path}") from exc
    if not isinstance(raw, dict):
        raise ProfileConfigError("profile config must be a YAML mapping")

    identity = _parse_identity(_require_mapping(raw, "identity"))
    search = _parse_search(_require_mapping(raw, "search"))
    profile_sections = _parse_profile_sections(_require_mapping(raw, "profile_sections"))

    return ProfileConfig(
        path=profile_path,
        root_dir=profile_path.parent,
        identity=identity,
        search=search,
        profile_sections=profile_sections,
    )


def build_discovery_context(path: Path | str = "knowledge/profile.yaml") -> DiscoveryProfileContext:
    config = load_profile_config(path)
    filter_context = _format_discovery_filter_context(config)
    scoring_parts = []
    for key in DISCOVERY_SCORING_SECTIONS:
        if key not in config.profile_sections:
            continue
        scoring_parts.append(_read_section(config, key))
    if not scoring_parts:
        raise ProfileConfigError(
            "Discovery scoring requires at least one of profile_sections: "
            + ", ".join(DISCOVERY_SCORING_SECTIONS)
        )
    return DiscoveryProfileContext(
        filter_context=filter_context,
        scoring_context="\n\n".join(scoring_parts),
    )


def build_application_context(path: Path | str = "knowledge/profile.yaml") -> ApplicationProfileContext:
    config = load_profile_config(path)
    section_parts = []
    for key in config.profile_sections:
        section_parts.append(_read_section(config, key))
    return ApplicationProfileContext(
        identity_context=_format_identity_context(config.identity),
        profile_sections_context="\n\n".join(section_parts),
        section_keys=tuple(config.profile_sections.keys()),
    )


def _parse_identity(raw: dict[str, Any]) -> IdentityConfig:
    location = _require_mapping(raw, "location")
    links_raw = raw.get("links", [])
    if not isinstance(links_raw, list):
        raise ProfileConfigError("identity.links must be a list")
    links = tuple(_parse_link(item, index) for index, item in enumerate(links_raw))
    return IdentityConfig(
        full_name=_require_string(raw, "full_name"),
        preferred_name=_require_string(raw, "preferred_name"),
        email=_require_string(raw, "email"),
        location_base=_require_string(location, "base", prefix="identity.location"),
        work_modes=tuple(_require_string_list(location, "work_modes", prefix="identity.location")),
        links=links,
    )


def _parse_link(raw: Any, index: int) -> LinkConfig:
    if not isinstance(raw, dict):
        raise ProfileConfigError(f"identity.links[{index}] must be a mapping")
    return LinkConfig(
        key=_require_string(raw, "key", prefix=f"identity.links[{index}]"),
        label=_require_string(raw, "label", prefix=f"identity.links[{index}]"),
        url=_require_string(raw, "url", prefix=f"identity.links[{index}]"),
        display=str(raw.get("display") or raw.get("url") or ""),
        show_on_cv=bool(raw.get("show_on_cv", False)),
    )


def _parse_search(raw: dict[str, Any]) -> SearchConfig:
    roles = _require_mapping(raw, "roles", prefix="search")
    seniority = _require_mapping(raw, "seniority", prefix="search")
    locations = _require_mapping(raw, "locations", prefix="search")
    industries = _require_mapping(raw, "industries", prefix="search")
    return SearchConfig(
        roles=RoleSearchConfig(
            primary=_require_string(roles, "primary", prefix="search.roles"),
            accepted=tuple(_require_string_list(roles, "accepted", prefix="search.roles")),
            excluded=tuple(_string_list(roles.get("excluded", []), "search.roles.excluded")),
        ),
        seniority=SenioritySearchConfig(
            target=_require_string(seniority, "target", prefix="search.seniority"),
            accepted=tuple(_require_string_list(seniority, "accepted", prefix="search.seniority")),
            excluded=tuple(_string_list(seniority.get("excluded", []), "search.seniority.excluded")),
        ),
        locations=LocationsSearchConfig(
            accepted=tuple(_require_string_list(locations, "accepted", prefix="search.locations")),
            excluded=tuple(_string_list(locations.get("excluded", []), "search.locations.excluded")),
        ),
        industries=IndustriesSearchConfig(
            preferred=tuple(_require_string_list(industries, "preferred", prefix="search.industries")),
        ),
        salary=_require_string(raw, "salary", prefix="search"),
        dealbreakers=tuple(_string_list(raw.get("dealbreakers", []), "search.dealbreakers")),
    )


def _parse_profile_sections(raw: dict[str, Any]) -> dict[str, Path]:
    sections: dict[str, Path] = {}
    for key, value in raw.items():
        if key not in ALLOWED_PROFILE_SECTION_KEYS:
            raise ProfileConfigError(f"unsupported profile_sections key: {key}")
        if not isinstance(value, str) or not value.strip():
            raise ProfileConfigError(f"profile_sections.{key} must be a non-empty path")
        sections[key] = Path(value)
    return sections


def _read_section(config: ProfileConfig, key: str) -> str:
    relative_path = config.profile_sections[key]
    full_path = config.root_dir / relative_path
    try:
        content = full_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ProfileConfigError(
            f"profile_sections.{key} points to {relative_path}, but the file does not exist"
        ) from exc
    return f"## {key}\n\n{content}"


def _format_identity_context(identity: IdentityConfig) -> str:
    links = "\n".join(
        f"- {link.label}: {link.url} ({link.display})"
        for link in identity.links
    )
    return (
        f"Full name: {identity.full_name}\n"
        f"Preferred name: {identity.preferred_name}\n"
        f"Email: {identity.email}\n"
        f"Location: {identity.location_base}\n"
        f"Work modes: {', '.join(identity.work_modes)}\n"
        f"Links:\n{links}"
    )


def _format_discovery_filter_context(config: ProfileConfig) -> str:
    search = config.search
    return "\n".join(
        [
            f"Primary role: {search.roles.primary}",
            f"Accepted roles: {', '.join(search.roles.accepted)}",
            f"Excluded roles: {', '.join(search.roles.excluded)}",
            f"Target seniority: {search.seniority.target}",
            f"Accepted seniority: {', '.join(search.seniority.accepted)}",
            f"Excluded seniority: {', '.join(search.seniority.excluded)}",
            f"Accepted locations: {', '.join(search.locations.accepted)}",
            f"Excluded locations: {', '.join(search.locations.excluded)}",
            f"Preferred industries: {', '.join(search.industries.preferred)}",
            f"Salary threshold: {search.salary}",
            f"Dealbreakers: {', '.join(search.dealbreakers)}",
            f"Candidate base location: {config.identity.location_base}",
            f"Candidate work modes: {', '.join(config.identity.work_modes)}",
        ]
    )


def _require_mapping(raw: dict[str, Any], key: str, prefix: str = "") -> dict[str, Any]:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, dict):
        raise ProfileConfigError(f"{name} is required and must be a mapping")
    return value


def _require_string(raw: dict[str, Any], key: str, prefix: str = "") -> str:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise ProfileConfigError(f"{name} is required")
    return value.strip()


def _require_string_list(raw: dict[str, Any], key: str, prefix: str = "") -> list[str]:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if value is None:
        raise ProfileConfigError(f"{name} is required")
    return _string_list(value, name)


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ProfileConfigError(f"{name} must be a list of strings")
    return [item.strip() for item in value]
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run --no-sync pytest tests/test_profile_context.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add examples/knowledge/profile.yaml examples/knowledge/profile/education.md examples/knowledge/profile/skills.md src/job_hunting/profile_context.py tests/test_profile_context.py
git commit -m "Add validated profile YAML context" -m "Discovery and application generation need a structured private profile contract before prompts and renderers can stop reading free-form criteria and hardcoded profile files.

Constraint: Real knowledge/profile.yaml remains ignored; examples/knowledge/profile.yaml is the public template.
Rejected: Letting crews read arbitrary knowledge/profile files directly | validation and section allowlists must happen before crew kickoff.
Confidence: high
Scope-risk: moderate
Directive: Keep crew-specific section policies in code, not user YAML.
Tested: uv run --no-sync pytest tests/test_profile_context.py -q
Not-tested: Discovery/Application crew prompt integration is covered in later tasks.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 2: Discovery Crew Uses Prepared Profile Context

**Files:**
- Modify: `src/job_hunting/flows/discovery_flow.py`
- Modify: `src/job_hunting/crews/discovery/config/tasks.yaml`
- Modify: `tests/test_discovery_crew_config.py`
- Modify: `tests/test_discovery_flow.py`

- [ ] **Step 1: Add failing prompt-config tests**

In `tests/test_discovery_crew_config.py`, update `test_scrape_task_handles_one_provided_company` and add:

```python
def test_scrape_task_uses_prepared_filter_context():
    description = _scrape_task_description()

    assert "{discovery_filter_context}" in description
    assert "knowledge/search-criteria.md" not in description
    assert "profile.yaml.search" in description


def test_score_task_uses_prepared_scoring_context():
    description = _tasks_config()["score_vacancies_task"]["description"]

    assert "{discovery_filter_context}" in description
    assert "{candidate_scoring_context}" in description
    assert "knowledge/search-criteria.md" not in description
    assert "knowledge/profile/profile-summary.md" not in description
```

Update the existing assertion in `test_scrape_task_handles_one_provided_company` from:

```python
assert "knowledge/search-criteria.md" in description
```

to:

```python
assert "{discovery_filter_context}" in description
```

- [ ] **Step 2: Add failing flow kickoff tests**

In `tests/test_discovery_flow.py`, import:

```python
from unittest.mock import patch

from job_hunting.profile_context import DiscoveryProfileContext
```

For each test that captures `kickoff_inputs` (`test_discovery_flow_runs_one_kickoff_per_company`,
`test_discovery_flow_uses_approved_company_candidates`, and the other kickoff-input assertions
reported by `rg -n "kickoff_inputs" tests/test_discovery_flow.py`), wrap `flow.run_discovery_crew()`
with:

```python
with patch(
    "job_hunting.flows.discovery_flow.build_discovery_context",
    return_value=DiscoveryProfileContext(
        filter_context="filter context",
        scoring_context="scoring context",
    ),
):
    result = flow.run_discovery_crew()
```

Update every expected kickoff input dictionary in those tests to include:

```python
"discovery_filter_context": "filter context",
"candidate_scoring_context": "scoring context",
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_crew_config.py tests/test_discovery_flow.py -q
```

Expected: FAIL because DiscoveryFlow does not build/pass context and prompts still mention `search-criteria.md`.

- [ ] **Step 4: Update DiscoveryFlow**

In `src/job_hunting/flows/discovery_flow.py`, add:

```python
from job_hunting.profile_context import build_discovery_context
```

Inside `run_discovery_crew`, before the company loop, add:

```python
profile_context = build_discovery_context()
```

Update kickoff inputs to:

```python
inputs={
    "today": today_str,
    "company": company,
    "career_page": career_page,
    "discovery_filter_context": profile_context.filter_context,
    "candidate_scoring_context": profile_context.scoring_context,
}
```

- [ ] **Step 5: Update discovery task prompts**

In `src/job_hunting/crews/discovery/config/tasks.yaml`, replace the scrape task file-read instruction with:

```yaml
    1. Use this prepared discovery filter context. It was built from
       profile.yaml.search and identity.location before crew kickoff:
       {discovery_filter_context}
```

Replace the score task criteria reads with:

```yaml
    For each vacancy ID in the list, read the file at data/{today}/vacancies/<vacancy_id>.json
    using the "Read a file's content" tool with the exact path.

    Use this prepared discovery filter context:
    {discovery_filter_context}

    Use this prepared candidate scoring context:
    {candidate_scoring_context}
```

Keep the scoring considerations but change:

```yaml
excluded criteria from search-criteria.md
```

to:

```yaml
dealbreakers from the prepared discovery filter context
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run --no-sync pytest tests/test_discovery_crew_config.py tests/test_discovery_flow.py tests/test_profile_context.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/job_hunting/flows/discovery_flow.py src/job_hunting/crews/discovery/config/tasks.yaml tests/test_discovery_crew_config.py tests/test_discovery_flow.py
git commit -m "Feed discovery from profile YAML context" -m "Discovery needs structured search filters and controlled candidate scoring context instead of free-form search-criteria reads.

Constraint: Company sourcing is out of scope and should not influence this integration.
Rejected: Keeping search-criteria.md in Discovery prompts | it duplicates profile.yaml.search and keeps filters free-form.
Confidence: high
Scope-risk: moderate
Directive: Build profile context in code before crew kickoff and keep agent file reads narrow.
Tested: uv run --no-sync pytest tests/test_discovery_crew_config.py tests/test_discovery_flow.py tests/test_profile_context.py -q
Not-tested: Live career-page scraping.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 3: Application Crew Uses Prepared Profile Context

**Files:**
- Modify: `src/job_hunting/flows/application_flow.py`
- Modify: `src/job_hunting/crews/application/config/tasks.yaml`
- Create: `tests/test_application_flow.py`
- Create: `tests/test_application_crew_config.py`

- [ ] **Step 1: Add failing ApplicationFlow context test**

Create `tests/test_application_flow.py`:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from job_hunting.flows.application_flow import ApplicationFlow
from job_hunting.profile_context import ApplicationProfileContext


def test_application_flow_passes_prepared_profile_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vacancy_dir = Path("data/2026-05-14/vacancies")
    score_dir = Path("data/2026-05-14/scores")
    vacancy_dir.mkdir(parents=True)
    score_dir.mkdir(parents=True)
    (vacancy_dir / "acme--pm.json").write_text(
        json.dumps(
            {
                "id": "acme--pm",
                "company": "Acme",
                "title": "Senior PM",
                "url": "https://acme.example/jobs/pm",
                "description": "Build product workflows.",
                "questions": ["Why Acme?"],
            }
        ),
        encoding="utf-8",
    )
    (score_dir / "acme--pm.json").write_text(
        json.dumps(
            {
                "vacancy_id": "acme--pm",
                "date": "2026-05-14",
                "company": "Acme",
                "title": "Senior PM",
                "score": 90,
                "status": "pending_approval",
                "requires_cover_letter": True,
            }
        ),
        encoding="utf-8",
    )

    crew = MagicMock()
    crew.kickoff.return_value = None
    app_crew = MagicMock()
    app_crew.crew.return_value = crew

    with patch("job_hunting.flows.application_flow.ApplicationCrew", return_value=app_crew), patch(
        "job_hunting.flows.application_flow.build_application_context",
        return_value=ApplicationProfileContext(
            identity_context="identity context",
            profile_sections_context="profile sections context",
            section_keys=("summary", "skills"),
        ),
    ):
        ApplicationFlow(vacancy_id="acme--pm", date="2026-05-14", notifier=None).run_application_crew()

    inputs = crew.kickoff.call_args.kwargs["inputs"]
    assert inputs["identity_context"] == "identity context"
    assert inputs["profile_sections_context"] == "profile sections context"
    assert inputs["profile_section_keys"] == "summary, skills"
```

- [ ] **Step 2: Add failing prompt-config checks**

Create `tests/test_application_crew_config.py`:

```python
from pathlib import Path

import yaml


def _tasks_config() -> dict:
    return yaml.safe_load(
        Path("src/job_hunting/crews/application/config/tasks.yaml").read_text(encoding="utf-8")
    )


def test_profile_brief_task_uses_prepared_application_context():
    description = _tasks_config()["profile_brief_task"]["description"]

    assert "{identity_context}" in description
    assert "{profile_sections_context}" in description
    assert "Read all profile files from knowledge/profile/" not in description
    assert "general-info.md" not in description


def test_cv_and_cover_letter_tasks_receive_identity_context():
    tasks = _tasks_config()

    assert "{identity_context}" in tasks["cv_task"]["description"]
    assert "{identity_context}" in tasks["cover_letter_task"]["description"]
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run --no-sync pytest tests/test_application_flow.py tests/test_application_crew_config.py -q
```

Expected: FAIL because ApplicationFlow and prompts do not pass/use prepared context yet.

- [ ] **Step 4: Update ApplicationFlow**

In `src/job_hunting/flows/application_flow.py`, import:

```python
from job_hunting.profile_context import build_application_context
```

Before `ApplicationCrew().crew().kickoff(...)`, add:

```python
profile_context = build_application_context()
```

Add kickoff inputs:

```python
"identity_context": profile_context.identity_context,
"profile_sections_context": profile_context.profile_sections_context,
"profile_section_keys": ", ".join(profile_context.section_keys),
```

- [ ] **Step 5: Update application task prompts**

In `src/job_hunting/crews/application/config/tasks.yaml`, replace the hardcoded profile file list in `profile_brief_task` with:

```yaml
    Use this structured identity context:
    {identity_context}

    Use only this allowlisted profile section context:
    {profile_sections_context}

    Available profile section keys: {profile_section_keys}

    Do not read additional files from knowledge/profile/. Do not use facts that
    are absent from the structured identity context or the allowlisted profile
    section context.
```

In `cv_task`, add:

```yaml
    Structured identity context for renderer-visible identity fields:
    {identity_context}
```

In `cover_letter_task`, add:

```yaml
    Structured identity context for signature and candidate identity:
    {identity_context}
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run --no-sync pytest tests/test_application_flow.py tests/test_application_crew_config.py tests/test_profile_context.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/job_hunting/flows/application_flow.py src/job_hunting/crews/application/config/tasks.yaml tests/test_application_flow.py tests/test_application_crew_config.py
git commit -m "Feed application artifacts from profile context" -m "Application generation needs one validated profile context so the Profile Steward remains the distillation point while renderers receive structured identity metadata.

Constraint: Detailed facts stay in allowlisted profile_sections files.
Rejected: Letting every application agent read profile files directly | it duplicates selection logic and weakens profile section controls.
Confidence: high
Scope-risk: moderate
Directive: Keep Profile Steward central; pass structured identity to artifact tasks and tools.
Tested: uv run --no-sync pytest tests/test_application_flow.py tests/test_application_crew_config.py tests/test_profile_context.py -q
Not-tested: Live LLM artifact generation.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 4: Remove CV Template and Renderer Hardcoding

**Files:**
- Modify: `personalized-outreach/templates/cv-template.md`
- Modify: `personalized-outreach/scripts/fill-template.js`
- Modify: `src/job_hunting/tools/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 1: Add failing synthetic CV generation test**

In `tests/test_cv_generator.py`, add a helper that runs the Node script directly:

```python
def _write_profile_yaml(profile_root: Path) -> None:
    (profile_root / "profile.yaml").write_text(
        """
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
    accepted: [Product Manager]
    excluded: []
  seniority:
    target: Senior
    accepted: [Senior]
    excluded: []
  locations:
    accepted: [Remote Europe]
    excluded: []
  industries:
    preferred: [SaaS]
  salary: "$120000+"
  dealbreakers: []
profile_sections:
  work_experience: profile/work-experience.md
  education: profile/education.md
  skills: profile/skills.md
  public_speaking: profile/public-speaking.md
""",
        encoding="utf-8",
    )
```

Add:

```python
def test_cv_node_renderer_uses_profile_yaml_identity_and_sections(tmp_path):
    profile_root = tmp_path / "knowledge"
    profile_dir = profile_root / "profile"
    profile_dir.mkdir(parents=True)
    _write_profile_yaml(profile_root)
    (profile_dir / "work-experience.md").write_text(
        """# Work Experience

## Example Labs — Product Lead

**Period:** January 2020 – Present
**Industry:** Developer Tools
**Location:** London

Example Labs builds developer collaboration software

### Key Achievements

- Increased activation by **42%** through onboarding experiments
""",
        encoding="utf-8",
    )
    (profile_dir / "education.md").write_text(
        """# Education

## University of London

**Degree:** Bachelor of Analytical Engines
**Period:** 1843

### Details

- Honors
""",
        encoding="utf-8",
    )
    (profile_dir / "skills.md").write_text("# Skills\n\n- Product strategy\n- SQL\n", encoding="utf-8")
    (profile_dir / "public-speaking.md").write_text(
        "# Public Speaking\n\n- ProductConf: Presented humane analytics.\n",
        encoding="utf-8",
    )
    tailored_json = tmp_path / "tailored.json"
    tailored_json.write_text(
        json.dumps(
            {
                "summary": "Product leader focused on developer tools.",
                "workExperienceIds": ["example-labs"],
                "workExperienceDescriptions": {
                    "example-labs": ["Increased activation by **42%** through onboarding experiments"]
                },
                "projectIds": [],
                "projectDescriptions": {},
                "skills": ["Product strategy", "SQL"],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "cv.tex"

    result = subprocess.run(
        [
            "node",
            "personalized-outreach/scripts/fill-template.js",
            "personalized-outreach/templates/cv-template.md",
            str(tailored_json),
            str(output_path),
            str(profile_root),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rendered = output_path.read_text(encoding="utf-8")
    assert "Ada Lovelace" in rendered
    assert "London, UK" in rendered
    assert "University of London" in rendered
    assert "ProductConf" in rendered
    assert "Mike" not in rendered
    assert "Higher School of Economics" not in rendered
    assert "ETHCC" not in rendered
    assert "DappCon" not in rendered
    assert "Data Science and analyst experience" not in rendered
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run --no-sync pytest tests/test_cv_generator.py::test_cv_node_renderer_uses_profile_yaml_identity_and_sections -q
```

Expected: FAIL because the Node renderer still reads Markdown general info and the CV template has hardcoded sections.

- [ ] **Step 3: Update CV template placeholders**

In `personalized-outreach/templates/cv-template.md`, replace the hardcoded public speaking block with:

```latex
==PUBLIC_SPEAKING_SECTION==
```

Replace the hardcoded education block with:

```latex
==EDUCATION_SECTION==
```

- [ ] **Step 4: Update Node renderer**

In `personalized-outreach/scripts/fill-template.js`:

- Add a YAML loader using a small parser if `yaml` package is unavailable, or parse simple YAML via Python is not allowed here. Prefer using Node's existing environment only if `yaml` dependency exists. If no YAML dependency exists, add profile YAML parsing to Python wrapper in Task 4 Step 5 and pass normalized JSON to Node.
- Remove `includeDataScienceRoleAtEnd` use.
- Remove `ensureDataScienceSignal` use.
- Replace hardcoded `{Remote}` with `role.location || ""`.
- Render identity from normalized profile config.
- Render `==PUBLIC_SPEAKING_SECTION==` only when section content exists.
- Render `==EDUCATION_SECTION==` only when section content exists.

Implementation note: if Node YAML parsing would require a new dependency, do not add one. Instead update `CVGeneratorTool` to create a temporary normalized profile JSON using `job_hunting.profile_context` and pass that JSON path as an optional fifth argument after `profileDir`.

- [ ] **Step 5: Update CVGeneratorTool to pass normalized profile JSON**

In `src/job_hunting/tools/cv_generator.py`, import:

```python
from job_hunting.profile_context import build_application_context, load_profile_config
```

Create a temporary JSON file containing identity and section content before calling Node:

```python
profile_config = load_profile_config(PROJECT_ROOT / "knowledge/profile.yaml")
profile_payload = {
    "identity": {
        "fullName": profile_config.identity.full_name,
        "preferredName": profile_config.identity.preferred_name,
        "email": profile_config.identity.email,
        "location": profile_config.identity.location_base,
        "workModes": list(profile_config.identity.work_modes),
        "links": [
            {
                "key": link.key,
                "label": link.label,
                "url": link.url,
                "display": link.display,
                "showOnCv": link.show_on_cv,
            }
            for link in profile_config.identity.links
        ],
    },
}
```

Then pass the JSON path to Node as an optional fifth argument. Keep backward compatibility when that argument is missing for tests/manual usage.

- [ ] **Step 6: Run CV tests**

Run:

```bash
uv run --no-sync pytest tests/test_cv_generator.py tests/test_profile_context.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add personalized-outreach/templates/cv-template.md personalized-outreach/scripts/fill-template.js src/job_hunting/tools/cv_generator.py tests/test_cv_generator.py
git commit -m "Remove hardcoded CV profile content" -m "CV generation needs to render candidate identity and optional sections from profile context instead of Mike-specific template blocks and renderer assumptions.

Constraint: Keep the current Node renderer for phase 1; Python renderer migration is deferred.
Rejected: Adding a Node YAML dependency | profile parsing should stay centralized in Python context code.
Confidence: medium
Scope-risk: moderate
Directive: Do not reintroduce candidate-specific fallback content in templates or renderer helpers.
Tested: uv run --no-sync pytest tests/test_cv_generator.py tests/test_profile_context.py -q
Not-tested: Full pdflatex visual output beyond existing generator behavior.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 5: Remove Cover Letter Signature Hardcoding

**Files:**
- Modify: `personalized-outreach/templates/cover-letter.md`
- Modify: `src/job_hunting/tools/cover_letter_tool.py`
- Modify: `tests/test_cover_letter_tool.py`

- [ ] **Step 1: Add failing signature test**

In `tests/test_cover_letter_tool.py`, add:

```python
def test_cover_letter_uses_profile_preferred_name_for_signature(tmp_path):
    tool = CoverLetterTool()
    output_path = tmp_path / "cover-letter.tex"
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    template = r"""
\begin{document}
==INTRO==
==MAIN BODY==
==CONCLUSION==
\textbf{==SIGNATURE==}
\end{document}
"""

    with patch("pathlib.Path.read_text", return_value=template), \
         patch("job_hunting.tools.cover_letter_tool.profile_preferred_name", return_value="Ada"), \
         patch("subprocess.run", return_value=mock_result), \
         patch.object(Path, "write_text") as write_mock:
        tool._run(
            intro="intro",
            main_body="body",
            conclusion="conclusion",
            output_tex_path=str(output_path),
        )

    written = write_mock.call_args.args[0]
    assert r"\textbf{Ada}" in written
    assert "Mike" not in written
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run --no-sync pytest tests/test_cover_letter_tool.py::test_cover_letter_uses_profile_preferred_name_for_signature -q
```

Expected: FAIL because `profile_preferred_name` does not exist and template has hardcoded `Mike`.

- [ ] **Step 3: Update cover letter template**

In `personalized-outreach/templates/cover-letter.md`, replace:

```latex
\textbf{Mike}
```

with:

```latex
\textbf{==SIGNATURE==}
```

- [ ] **Step 4: Update cover letter tool**

In `src/job_hunting/tools/cover_letter_tool.py`, import:

```python
from job_hunting.profile_context import load_profile_config
```

Add:

```python
def profile_preferred_name() -> str:
    return load_profile_config(PROJECT_ROOT / "knowledge/profile.yaml").identity.preferred_name
```

Update replacement chain:

```python
            .replace("==CONCLUSION==", escape_latex(conclusion))
            .replace("==SIGNATURE==", escape_latex(profile_preferred_name()))
```

- [ ] **Step 5: Run cover letter tests**

Run:

```bash
uv run --no-sync pytest tests/test_cover_letter_tool.py tests/test_profile_context.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add personalized-outreach/templates/cover-letter.md src/job_hunting/tools/cover_letter_tool.py tests/test_cover_letter_tool.py
git commit -m "Render cover letter signature from profile YAML" -m "Cover letter generation needs candidate identity from profile.yaml so templates are reusable for every user.

Constraint: Keep existing intro/body/conclusion generation unchanged.
Rejected: Passing signature as an LLM-generated field | identity should be deterministic renderer-owned data.
Confidence: high
Scope-risk: narrow
Directive: Do not hardcode candidate names in artifact templates.
Tested: uv run --no-sync pytest tests/test_cover_letter_tool.py tests/test_profile_context.py -q
Not-tested: Full pdflatex visual output beyond existing generator behavior.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Task 6: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/setup-guide.md`

- [ ] **Step 1: Update docs**

In `README.md`, replace references that tell users to fill `knowledge/search-criteria.md` with guidance to copy and fill:

```text
examples/knowledge/profile.yaml -> knowledge/profile.yaml
```

Mention `search-criteria.md` is deprecated by `profile.yaml.search`.

In `docs/setup-guide.md`, add a `knowledge/profile.yaml` section with:

```markdown
### `knowledge/profile.yaml`

This private file is the structured control surface for identity, Discovery search filters, and allowlisted profile evidence files. Copy `examples/knowledge/profile.yaml` to `knowledge/profile.yaml` and edit it for the candidate.

Real `knowledge/profile.yaml` stays ignored by git. Commit only example files.
```

- [ ] **Step 2: Run targeted verification**

Run:

```bash
uv run --no-sync pytest tests/test_profile_context.py tests/test_discovery_crew_config.py tests/test_discovery_flow.py tests/test_application_crew_config.py tests/test_prep_vacancy_flow.py tests/test_cv_generator.py tests/test_cover_letter_tool.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
uv run --no-sync pytest -q
```

Expected: PASS.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: only intentional changes staged/unstaged; `.superpowers/` may remain untracked and should not be committed.

- [ ] **Step 5: Commit docs**

```bash
git add README.md docs/setup-guide.md
git commit -m "Document profile YAML setup" -m "Users need one private structured profile file for identity, search filters, and profile section allowlists before discovery and artifact generation run.

Constraint: Real knowledge/profile.yaml stays ignored by git.
Rejected: Continuing to document search-criteria.md as the primary search control | profile.yaml.search replaces it.
Confidence: high
Scope-risk: narrow
Directive: Keep examples public and real candidate knowledge private.
Tested: uv run --no-sync pytest -q
Not-tested: Fresh user onboarding outside the documented copy flow.
Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

## Final Branch Handoff

- [ ] **Step 1: Confirm final log**

Run:

```bash
git log --oneline --decorate -5
```

- [ ] **Step 2: Push branch**

Run:

```bash
git push -u origin unified-profile-artifacts
```

Expected: remote branch `origin/unified-profile-artifacts` is created.

- [ ] **Step 3: Final report**

Report:

- changed files by area
- verification commands and results
- pushed branch name
- known follow-up: optional Python CV renderer migration
