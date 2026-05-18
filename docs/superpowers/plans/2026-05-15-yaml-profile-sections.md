# YAML Profile Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Markdown profile evidence sections with validated YAML section files and render structured HTTPS proof links as underlined clickable PDF labels.

**Architecture:** Keep `knowledge/profile.yaml` as the identity/search/index file, and add typed section loading in `job_hunting.profile_context`. Build application/discovery context from structured section data, pass normalized structured JSON to the CV renderer, and update the Node renderer to format YAML-backed roles, projects, education, public performance, and skills.

**Tech Stack:** Python 3.10+, PyYAML, dataclasses, pytest, Node.js renderer script, LaTeX `\href`/`\underline` output.

---

## File Structure

- Modify: `src/job_hunting/profile_context.py`
  - Owns profile index parsing, section YAML parsing, validation, context formatting, and renderer-ready normalized profile data.
- Modify: `src/job_hunting/tools/cv_generator.py`
  - Uses the new normalized structured profile data instead of reading section files as raw strings.
- Modify: `personalized-outreach/scripts/fill-template.js`
  - Renders structured work experience, projects, education, public performance, skills, and underlined HTTPS links.
- Modify: `tests/test_profile_context.py`
  - Updates existing profile index/context tests from Markdown sections to YAML sections.
- Modify: `tests/test_cv_generator.py`
  - Updates normalized profile and Node renderer tests for structured section data and underlined links.
- Modify: `examples/knowledge/profile.yaml`
  - Points active section paths to `.yaml` files and removes `summary`.
- Create: `examples/knowledge/profile/work-experience.yaml`
- Create: `examples/knowledge/profile/personal-projects.yaml`
- Create: `examples/knowledge/profile/education.yaml`
- Create: `examples/knowledge/profile/skills.yaml`
- Create: `examples/knowledge/profile/public-performance.yaml`
- Create: `examples/knowledge/profile/values-and-interests.yaml`
- Modify: `README.md`
  - Documents YAML section files and HTTPS links.
- Modify: `docs/setup-guide.md`
  - Documents the new setup flow and section schemas.

## Validation Note

The local baseline `uv run pytest` currently cannot complete on macOS x86_64 because `onnxruntime==1.26.0` does not publish a compatible wheel for this platform. Use targeted tests that do not require installing the full dependency graph if the environment is already available; otherwise record the same blocker.

---

### Task 1: Parse And Validate YAML Section Files

**Files:**
- Modify: `src/job_hunting/profile_context.py`
- Modify: `tests/test_profile_context.py`

- [ ] **Step 1: Write failing tests for `.yaml` section paths and Markdown rejection**

Add tests near the current `profile_sections` tests in `tests/test_profile_context.py`:

```python
def test_profile_sections_must_point_to_yaml_files(tmp_path):
    profile_yaml = tmp_path / "profile.yaml"
    _write_valid_profile_yaml(
        profile_yaml,
        _valid_profile_yaml(profile_sections="work_experience: profile/work-experience.md"),
    )

    with pytest.raises(
        ProfileConfigError,
        match="profile_sections.work_experience must point to a .yaml file",
    ):
        load_profile_config(profile_yaml)


def test_loads_example_profile_yaml_with_yaml_sections():
    config = load_profile_config(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert config.identity.full_name == "Alex Candidate"
    assert config.search.roles.primary == "Product Manager"
    assert config.profile_sections["work_experience"] == Path("profile/work-experience.yaml")
    assert "summary" not in config.profile_sections
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_profile_context.py::test_profile_sections_must_point_to_yaml_files tests/test_profile_context.py::test_loads_example_profile_yaml_with_yaml_sections -q
```

Expected: failure because Markdown paths are still accepted and examples still point to `.md`.

- [ ] **Step 3: Update allowed section keys and path validation**

In `src/job_hunting/profile_context.py`, remove `summary` from `ALLOWED_PROFILE_SECTION_KEYS` and change `DISCOVERY_SCORING_SECTIONS`:

```python
ALLOWED_PROFILE_SECTION_KEYS = {
    "work_experience",
    "projects",
    "education",
    "skills",
    "public_speaking",
    "values",
}

DISCOVERY_SCORING_SECTIONS = ("work_experience", "projects", "skills")
```

Update `_parse_profile_sections`:

```python
def _parse_profile_sections(raw: dict[str, Any]) -> dict[str, Path]:
    sections: dict[str, Path] = {}
    for key, value in raw.items():
        if key not in ALLOWED_PROFILE_SECTION_KEYS:
            raise ProfileConfigError(f"unsupported profile_sections key: {key}")
        if not isinstance(value, str) or not value.strip():
            raise ProfileConfigError(f"profile_sections.{key} must be a non-empty path")
        section_path = Path(value.strip())
        if section_path.suffix != ".yaml":
            raise ProfileConfigError(f"profile_sections.{key} must point to a .yaml file")
        sections[key] = section_path
    return sections
```

- [ ] **Step 4: Add shared section dataclasses and helpers**

Add these dataclasses after `SearchConfig`:

```python
@dataclass(frozen=True)
class SectionLink:
    label: str
    url: str


@dataclass(frozen=True)
class PeriodConfig:
    start: str
    end: str


@dataclass(frozen=True)
class WorkAchievement:
    area: str
    text: str
    links: tuple[SectionLink, ...]


@dataclass(frozen=True)
class WorkRole:
    id: str
    company: str
    title: str
    period: PeriodConfig
    industry: str | None
    company_summary: str | None
    show_on_cv: bool
    achievements: tuple[WorkAchievement, ...]


@dataclass(frozen=True)
class ProjectItem:
    id: str
    name: str
    title: str | None
    period: PeriodConfig | None
    description: str
    show_on_cv: bool
    links: tuple[SectionLink, ...]
    tech_stack: tuple[str, ...]


@dataclass(frozen=True)
class EducationItem:
    id: str
    institution: str
    degree: str
    field: str
    period: PeriodConfig | None
    grade: str | None
    show_on_cv: bool
    links: tuple[SectionLink, ...]


@dataclass(frozen=True)
class SkillGroup:
    name: str
    show_on_cv: bool
    skills: tuple[str, ...]


@dataclass(frozen=True)
class TalkItem:
    id: str
    conference: str
    title: str
    show_on_cv: bool
    links: tuple[SectionLink, ...]


@dataclass(frozen=True)
class PublicationItem:
    id: str
    title: str
    description: str | None
    show_on_cv: bool
    links: tuple[SectionLink, ...]


@dataclass(frozen=True)
class ValueItem:
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class ProfileSections:
    work_experience: tuple[WorkRole, ...] = ()
    projects: tuple[ProjectItem, ...] = ()
    education: tuple[EducationItem, ...] = ()
    skills: tuple[SkillGroup, ...] = ()
    talks: tuple[TalkItem, ...] = ()
    publications: tuple[PublicationItem, ...] = ()
    values: tuple[ValueItem, ...] = ()
    interests: tuple[ValueItem, ...] = ()
```

Add helper validators near the existing `_require_string` helpers:

```python
def _optional_bool(raw: dict[str, Any], key: str, prefix: str = "", default: bool = True) -> bool:
    value = raw.get(key, default)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, bool):
        raise ProfileConfigError(f"{name} must be a boolean")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ProfileConfigError(f"{name} must be a non-empty list")
    return value


def _parse_period(raw: Any, prefix: str, *, required: bool) -> PeriodConfig | None:
    if raw is None and not required:
        return None
    if not isinstance(raw, dict):
        raise ProfileConfigError(f"{prefix}.period is required and must be a mapping")
    start = _require_string(raw, "start", prefix=f"{prefix}.period")
    end = _require_string(raw, "end", prefix=f"{prefix}.period")
    _validate_period_value(start, f"{prefix}.period.start", allow_present=False)
    _validate_period_value(end, f"{prefix}.period.end", allow_present=True)
    return PeriodConfig(start=start, end=end)


def _validate_period_value(value: str, name: str, *, allow_present: bool) -> None:
    if allow_present and value == "present":
        return
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ProfileConfigError(f"{name} must use YYYY-MM")
```

Also import `re` at the top.

- [ ] **Step 5: Add link validation**

Add:

```python
def _parse_section_links(raw: dict[str, Any], prefix: str) -> tuple[SectionLink, ...]:
    links_raw = raw.get("links", [])
    if links_raw is None:
        return ()
    if not isinstance(links_raw, list):
        raise ProfileConfigError(f"{prefix}.links must be a list")
    links: list[SectionLink] = []
    for index, item in enumerate(links_raw):
        link_prefix = f"{prefix}.links[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{link_prefix} must be a mapping")
        url = _require_string(item, "url", prefix=link_prefix)
        if not url.startswith("https://"):
            raise ProfileConfigError(f"{link_prefix}.url must be an https URL")
        links.append(
            SectionLink(
                label=_require_string(item, "label", prefix=link_prefix),
                url=url,
            )
        )
    return tuple(links)
```

- [ ] **Step 6: Add section parser functions**

Add parser functions:

```python
def load_profile_sections(config: ProfileConfig) -> ProfileSections:
    sections = ProfileSections()
    values = {
        "work_experience": (),
        "projects": (),
        "education": (),
        "skills": (),
        "talks": (),
        "publications": (),
        "values": (),
        "interests": (),
    }
    for key, relative_path in config.profile_sections.items():
        raw = _read_section_yaml(config, key, relative_path)
        if key == "work_experience":
            values["work_experience"] = _parse_work_experience(raw)
        elif key == "projects":
            values["projects"] = _parse_projects(raw)
        elif key == "education":
            values["education"] = _parse_education(raw)
        elif key == "skills":
            values["skills"] = _parse_skills(raw)
        elif key == "public_speaking":
            talks, publications = _parse_public_performance(raw)
            values["talks"] = talks
            values["publications"] = publications
        elif key == "values":
            profile_values, interests = _parse_values_and_interests(raw)
            values["values"] = profile_values
            values["interests"] = interests
    return ProfileSections(**values)


def _read_section_yaml(config: ProfileConfig, key: str, relative_path: Path) -> dict[str, Any]:
    full_path = config.root_dir / relative_path
    try:
        raw = yaml.safe_load(full_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ProfileConfigError(
            f"profile_sections.{key} points to {relative_path}, but the file does not exist"
        ) from exc
    if not isinstance(raw, dict):
        raise ProfileConfigError(f"profile_sections.{key} must be a YAML mapping")
    return raw
```

Add the concrete parser functions:

```python
def _parse_work_experience(raw: dict[str, Any]) -> tuple[WorkRole, ...]:
    roles = []
    for index, item in enumerate(_require_list(raw.get("roles"), "work_experience.roles")):
        prefix = f"work_experience.roles[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        achievement_items = []
        for achievement_index, achievement in enumerate(
            _require_list(item.get("achievements"), f"{prefix}.achievements")
        ):
            achievement_prefix = f"{prefix}.achievements[{achievement_index}]"
            if not isinstance(achievement, dict):
                raise ProfileConfigError(f"{achievement_prefix} must be a mapping")
            achievement_items.append(
                WorkAchievement(
                    area=_require_string(achievement, "area", prefix=achievement_prefix),
                    text=_require_string(achievement, "text", prefix=achievement_prefix),
                    links=_parse_section_links(achievement, achievement_prefix),
                )
            )
        roles.append(
            WorkRole(
                id=_require_string(item, "id", prefix=prefix),
                company=_require_string(item, "company", prefix=prefix),
                title=_require_string(item, "title", prefix=prefix),
                period=_parse_period(item.get("period"), prefix, required=True),
                industry=_optional_string(item, "industry", prefix=prefix),
                company_summary=_optional_string(item, "company_summary", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                achievements=tuple(achievement_items),
            )
        )
    return tuple(roles)


def _parse_projects(raw: dict[str, Any]) -> tuple[ProjectItem, ...]:
    projects = []
    for index, item in enumerate(_require_list(raw.get("projects"), "projects.projects")):
        prefix = f"projects.projects[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        projects.append(
            ProjectItem(
                id=_require_string(item, "id", prefix=prefix),
                name=_require_string(item, "name", prefix=prefix),
                title=_optional_string(item, "title", prefix=prefix),
                period=_parse_period(item.get("period"), prefix, required=False),
                description=_require_string(item, "description", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                links=_parse_section_links(item, prefix),
                tech_stack=tuple(_string_list(item.get("tech_stack", []), f"{prefix}.tech_stack")),
            )
        )
    return tuple(projects)


def _parse_education(raw: dict[str, Any]) -> tuple[EducationItem, ...]:
    education = []
    for index, item in enumerate(_require_list(raw.get("education"), "education.education")):
        prefix = f"education.education[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        education.append(
            EducationItem(
                id=_require_string(item, "id", prefix=prefix),
                institution=_require_string(item, "institution", prefix=prefix),
                degree=_require_string(item, "degree", prefix=prefix),
                field=_require_string(item, "field", prefix=prefix),
                period=_parse_period(item.get("period"), prefix, required=False),
                grade=_optional_string(item, "grade", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                links=_parse_section_links(item, prefix),
            )
        )
    return tuple(education)


def _parse_skills(raw: dict[str, Any]) -> tuple[SkillGroup, ...]:
    groups = []
    for index, item in enumerate(_require_list(raw.get("skill_groups"), "skills.skill_groups")):
        prefix = f"skills.skill_groups[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        groups.append(
            SkillGroup(
                name=_require_string(item, "name", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                skills=tuple(_require_string_list(item, "skills", prefix=prefix)),
            )
        )
    return tuple(groups)


def _parse_public_performance(
    raw: dict[str, Any],
) -> tuple[tuple[TalkItem, ...], tuple[PublicationItem, ...]]:
    talks_raw = raw.get("talks", [])
    publications_raw = raw.get("publications", [])
    if not talks_raw and not publications_raw:
        raise ProfileConfigError("public_speaking requires talks or publications")
    talks = []
    for index, item in enumerate(talks_raw):
        prefix = f"public_speaking.talks[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        talks.append(
            TalkItem(
                id=_require_string(item, "id", prefix=prefix),
                conference=_require_string(item, "conference", prefix=prefix),
                title=_require_string(item, "title", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                links=_parse_section_links(item, prefix),
            )
        )
    publications = []
    for index, item in enumerate(publications_raw):
        prefix = f"public_speaking.publications[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        publications.append(
            PublicationItem(
                id=_require_string(item, "id", prefix=prefix),
                title=_require_string(item, "title", prefix=prefix),
                description=_optional_string(item, "description", prefix=prefix),
                show_on_cv=_optional_bool(item, "show_on_cv", prefix=prefix),
                links=_parse_section_links(item, prefix),
            )
        )
    return tuple(talks), tuple(publications)


def _parse_values_and_interests(
    raw: dict[str, Any],
) -> tuple[tuple[ValueItem, ...], tuple[ValueItem, ...]]:
    values_raw = raw.get("values", [])
    interests_raw = raw.get("interests", [])
    if not values_raw and not interests_raw:
        raise ProfileConfigError("values requires values or interests")
    return (
        _parse_value_items(values_raw, "values.values"),
        _parse_value_items(interests_raw, "values.interests"),
    )


def _parse_value_items(raw_items: Any, name: str) -> tuple[ValueItem, ...]:
    if raw_items is None:
        return ()
    if not isinstance(raw_items, list):
        raise ProfileConfigError(f"{name} must be a list")
    items = []
    for index, item in enumerate(raw_items):
        prefix = f"{name}[{index}]"
        if not isinstance(item, dict):
            raise ProfileConfigError(f"{prefix} must be a mapping")
        items.append(
            ValueItem(
                id=_require_string(item, "id", prefix=prefix),
                title=_require_string(item, "title", prefix=prefix),
                description=_require_string(item, "description", prefix=prefix),
            )
        )
    return tuple(items)
```

- [ ] **Step 7: Run profile tests**

Run:

```bash
uv run pytest tests/test_profile_context.py -q
```

Expected: pass if the environment is available; otherwise record the `onnxruntime` wheel blocker and run the smallest available local Python/import checks.

- [ ] **Step 8: Commit**

```bash
git add src/job_hunting/profile_context.py tests/test_profile_context.py
git commit -m "Validate YAML profile sections" \
  -m "Introduce typed parsing and validation for YAML-only profile evidence sections." \
  -m "Constraint: Profile section files are the source of truth for all artifact evidence." \
  -m "Rejected: Markdown section compatibility | the approved design migrates directly to YAML-only sections." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Keep profile section validation centralized in profile_context.py." \
  -m "Tested: uv run pytest tests/test_profile_context.py -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 2: Build Structured Application And Discovery Context

**Files:**
- Modify: `src/job_hunting/profile_context.py`
- Modify: `tests/test_profile_context.py`

- [ ] **Step 1: Write failing tests for structured context**

Add:

```python
def test_application_context_formats_structured_yaml_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "work-experience.yaml").write_text(
        """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2023-01, end: present}
    industry: SaaS
    company_summary: Product analytics platform
    achievements:
      - area: Activation
        text: Grew activation by 30%.
        links:
          - label: Case study
            url: https://example.com/case-study
""",
        encoding="utf-8",
    )
    (profile_dir / "skills.yaml").write_text(
        """
skill_groups:
  - name: Product
    skills: [Product strategy, Activation]
""",
        encoding="utf-8",
    )
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        _valid_profile_yaml(
            profile_sections="""
  work_experience: profile/work-experience.yaml
  skills: profile/skills.yaml
"""
        ),
        encoding="utf-8",
    )

    context = build_application_context(profile_yaml)

    assert "## Work experience" in context.profile_sections_context
    assert "Acme - Senior Product Manager" in context.profile_sections_context
    assert "Activation: Grew activation by 30%." in context.profile_sections_context
    assert "Case study: https://example.com/case-study" in context.profile_sections_context
    assert "## Skills" in context.profile_sections_context
    assert "Product: Product strategy, Activation" in context.profile_sections_context
```

Add:

```python
def test_discovery_context_uses_structured_scoring_sections_without_summary(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "work-experience.yaml").write_text(
        """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2023-01, end: present}
    achievements:
      - area: Activation
        text: Grew activation by 30%.
""",
        encoding="utf-8",
    )
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        _valid_profile_yaml(profile_sections="work_experience: profile/work-experience.yaml"),
        encoding="utf-8",
    )

    context = build_discovery_context(profile_yaml)

    assert "Generated candidate scoring context" in context.scoring_context
    assert "Acme - Senior Product Manager" in context.scoring_context
    assert "Grew activation by 30%" in context.scoring_context
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_profile_context.py::test_application_context_formats_structured_yaml_sections tests/test_profile_context.py::test_discovery_context_uses_structured_scoring_sections_without_summary -q
```

Expected: failure because context builders still read raw section text.

- [ ] **Step 3: Add context formatting functions**

In `src/job_hunting/profile_context.py`, add:

```python
def _format_period(period: PeriodConfig | None) -> str:
    if period is None:
        return ""
    start = _format_period_value(period.start)
    end = "Present" if period.end == "present" else _format_period_value(period.end)
    return f"{start} - {end}"


def _format_period_value(value: str) -> str:
    year, month = value.split("-")
    month_name = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )[int(month) - 1]
    return f"{month_name} {year}"


def _format_links_for_context(links: tuple[SectionLink, ...]) -> str:
    if not links:
        return ""
    return " Links: " + ". ".join(f"{link.label}: {link.url}" for link in links)
```

Add section formatters:

```python
def _format_work_experience_context(roles: tuple[WorkRole, ...]) -> str:
    lines = ["## Work experience"]
    for role in roles:
        period = _format_period(role.period)
        lines.append(f"- {role.company} - {role.title} ({period})")
        if role.industry:
            lines.append(f"  Industry: {role.industry}")
        if role.company_summary:
            lines.append(f"  Company summary: {role.company_summary}")
        for achievement in role.achievements:
            lines.append(
                f"  - {achievement.area}: {achievement.text}"
                f"{_format_links_for_context(achievement.links)}"
            )
    return "\n".join(lines)
```

Add the rest of the context formatters:

```python
def _format_projects_context(projects: tuple[ProjectItem, ...]) -> str:
    lines = ["## Projects"]
    for project in projects:
        period = _format_period(project.period)
        heading = f"- {project.name}"
        if project.title:
            heading += f" - {project.title}"
        if period:
            heading += f" ({period})"
        lines.append(heading)
        lines.append(f"  Description: {project.description}{_format_links_for_context(project.links)}")
        if project.tech_stack:
            lines.append(f"  Tech stack: {', '.join(project.tech_stack)}")
    return "\n".join(lines)


def _format_education_context(education: tuple[EducationItem, ...]) -> str:
    lines = ["## Education"]
    for item in education:
        parts = [item.degree, item.field, item.institution]
        if item.period:
            parts.append(_format_period(item.period))
        if item.grade:
            parts.append(item.grade)
        lines.append(f"- {', '.join(parts)}{_format_links_for_context(item.links)}")
    return "\n".join(lines)


def _format_skills_context(skill_groups: tuple[SkillGroup, ...]) -> str:
    lines = ["## Skills"]
    for group in skill_groups:
        lines.append(f"- {group.name}: {', '.join(group.skills)}")
    return "\n".join(lines)


def _format_public_performance_context(
    talks: tuple[TalkItem, ...], publications: tuple[PublicationItem, ...]
) -> str:
    lines = ["## Public performance"]
    for talk in talks:
        lines.append(
            f"- Talk: {talk.conference}: {talk.title}"
            f"{_format_links_for_context(talk.links)}"
        )
    for publication in publications:
        text = publication.title
        if publication.description:
            text += f": {publication.description}"
        lines.append(f"- Publication: {text}{_format_links_for_context(publication.links)}")
    return "\n".join(lines)


def _format_values_context(
    values: tuple[ValueItem, ...], interests: tuple[ValueItem, ...]
) -> str:
    lines = ["## Values and interests"]
    for value in values:
        lines.append(f"- Value - {value.title}: {value.description}")
    for interest in interests:
        lines.append(f"- Interest - {interest.title}: {interest.description}")
    return "\n".join(lines)


def _format_application_sections(sections: ProfileSections) -> list[str]:
    parts: list[str] = []
    if sections.work_experience:
        parts.append(_format_work_experience_context(sections.work_experience))
    if sections.projects:
        parts.append(_format_projects_context(sections.projects))
    if sections.education:
        parts.append(_format_education_context(sections.education))
    if sections.skills:
        parts.append(_format_skills_context(sections.skills))
    if sections.talks or sections.publications:
        parts.append(_format_public_performance_context(sections.talks, sections.publications))
    if sections.values or sections.interests:
        parts.append(_format_values_context(sections.values, sections.interests))
    return parts
```

- [ ] **Step 4: Update context builders to use structured sections**

Change `build_application_context`:

```python
def build_application_context(
    path: Path | str = "knowledge/profile.yaml",
) -> ApplicationProfileContext:
    config = load_profile_config(path)
    sections = load_profile_sections(config)
    section_parts = _format_application_sections(sections)
    return ApplicationProfileContext(
        identity_context=_format_identity_context(config.identity),
        profile_sections_context="\n\n".join(section_parts),
        section_keys=tuple(config.profile_sections.keys()),
    )
```

Change `build_discovery_context`:

```python
def build_discovery_context(
    path: Path | str = "knowledge/profile.yaml",
) -> DiscoveryProfileContext:
    config = load_profile_config(path)
    sections = load_profile_sections(config)
    scoring_context = _format_discovery_scoring_context(sections)
    if not scoring_context.strip():
        raise ProfileConfigError(
            "Discovery scoring requires at least one of profile_sections: "
            + ", ".join(DISCOVERY_SCORING_SECTIONS)
        )
    return DiscoveryProfileContext(
        filter_context=_format_discovery_filter_context(config),
        scoring_context=scoring_context,
    )
```

Add:

```python
def _format_discovery_scoring_context(sections: ProfileSections) -> str:
    parts = ["Generated candidate scoring context"]
    if sections.work_experience:
        parts.append(_format_work_experience_context(sections.work_experience))
    if sections.projects:
        parts.append(_format_projects_context(sections.projects))
    if sections.skills:
        parts.append(_format_skills_context(sections.skills))
    return "\n\n".join(parts) if len(parts) > 1 else ""
```

- [ ] **Step 5: Update tests still expecting Markdown summaries**

Replace Markdown-based fixtures in `tests/test_profile_context.py` with YAML section fixtures. Delete assertions that expect `profile-summary.md` content. Add assertions that `summary` is rejected as an unsupported profile section key.

- [ ] **Step 6: Run profile context tests**

Run:

```bash
uv run pytest tests/test_profile_context.py -q
```

Expected: pass, or the known dependency install blocker if the environment cannot resolve `onnxruntime`.

- [ ] **Step 7: Commit**

```bash
git add src/job_hunting/profile_context.py tests/test_profile_context.py
git commit -m "Build contexts from structured profile facts" \
  -m "Replace raw section text assembly with deterministic context generated from typed YAML profile sections." \
  -m "Constraint: Stored profile summaries are removed from the approved profile contract." \
  -m "Rejected: Reading Markdown section content | structured facts are now the artifact evidence boundary." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Runtime summaries must be generated from typed section data, not maintained as profile files." \
  -m "Tested: uv run pytest tests/test_profile_context.py -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 3: Emit Normalized Structured Profile JSON For CV Rendering

**Files:**
- Modify: `src/job_hunting/profile_context.py`
- Modify: `src/job_hunting/tools/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 1: Write failing normalized JSON test**

In `tests/test_cv_generator.py`, update `test_cv_generator_calls_node_script` to include structured section data:

```python
profile_sections = SimpleNamespace(
    work_experience=(
        SimpleNamespace(
            id="analytical-engines",
            company="Analytical Engines Ltd",
            title="Product Lead",
            period=SimpleNamespace(start="1842-01", end="1843-12"),
            industry="Computing",
            company_summary="Mechanical computation company",
            show_on_cv=True,
            achievements=(
                SimpleNamespace(
                    area="Launch",
                    text="Shipped programmable workflows.",
                    links=(SimpleNamespace(label="Proof", url="https://example.com/proof"),),
                ),
            ),
        ),
    ),
    projects=(),
    education=(),
    skills=(),
    talks=(),
    publications=(),
    values=(),
    interests=(),
)
```

Patch `load_profile_sections` in the test:

```python
patch(
    "job_hunting.tools.cv_generator.load_profile_sections",
    return_value=profile_sections,
),
```

Assert:

```python
assert captured_profile["workExperience"][0]["position"] == "Product Lead"
assert captured_profile["workExperience"][0]["period"] == "Jan 1842 - Dec 1843"
assert captured_profile["workExperience"][0]["achievements"][0]["area"] == "Launch"
assert captured_profile["workExperience"][0]["achievements"][0]["links"][0]["label"] == "Proof"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_cv_generator.py::test_cv_generator_calls_node_script -q
```

Expected: failure because `_create_normalized_profile_json` still reads raw section files.

- [ ] **Step 3: Add normalized conversion helpers**

In `src/job_hunting/profile_context.py`, expose:

```python
def format_period_for_display(period: PeriodConfig | None) -> str:
    return _format_period(period)
```

In `src/job_hunting/tools/cv_generator.py`, import:

```python
from job_hunting.profile_context import (
    ProfileConfigError,
    format_period_for_display,
    load_profile_config,
    load_profile_sections,
)
```

Replace `_read_profile_sections` usage with helpers:

```python
def _links_to_json(links) -> list[dict[str, str]]:
    return [{"label": link.label, "url": link.url} for link in links]


def _create_normalized_profile_json() -> str | None:
    try:
        profile = load_profile_config(PROFILE_CONFIG_PATH)
        sections = load_profile_sections(profile)
    except (OSError, ProfileConfigError):
        return None

    normalized_profile = {
        "identity": {
            "fullName": profile.identity.full_name,
            "preferredName": profile.identity.preferred_name,
            "email": profile.identity.email,
            "location": profile.identity.location_base,
            "workModes": list(profile.identity.work_modes),
            "links": [
                {
                    "key": link.key,
                    "label": link.label,
                    "url": link.url,
                    "display": link.display,
                    "showOnCv": link.show_on_cv,
                }
                for link in profile.identity.links
            ],
        },
        "workExperience": _work_experience_to_json(sections.work_experience),
        "projects": _projects_to_json(sections.projects),
        "education": _education_to_json(sections.education),
        "skillGroups": _skill_groups_to_json(sections.skills),
        "talks": _talks_to_json(sections.talks),
        "publications": _publications_to_json(sections.publications),
    }
```

Implement `_work_experience_to_json`, `_projects_to_json`, `_education_to_json`, `_skill_groups_to_json`, `_talks_to_json`, and `_publications_to_json`. Keep legacy renderer keys where needed:

```python
def _work_experience_to_json(roles) -> list[dict[str, object]]:
    return [
        {
            "id": role.id,
            "company": role.company,
            "position": role.title,
            "period": format_period_for_display(role.period),
            "industry": role.industry,
            "companyDescription": role.company_summary or "",
            "showOnCv": role.show_on_cv,
            "achievements": [
                {
                    "area": achievement.area,
                    "text": achievement.text,
                    "links": _links_to_json(achievement.links),
                }
                for achievement in role.achievements
            ],
        }
        for role in roles
    ]
```

- [ ] **Step 4: Remove raw `_read_profile_sections` fallback**

Delete `_read_profile_sections` from `cv_generator.py` after normalized structured conversion covers all active section data. Keep the existing `except (OSError, ProfileConfigError): return None` fallback so tool execution can proceed without normalized data if private profile setup is missing.

- [ ] **Step 5: Run CV generator Python tests**

Run:

```bash
uv run pytest tests/test_cv_generator.py::test_cv_generator_calls_node_script tests/test_cv_generator.py::test_cv_generator_falls_back_when_profile_section_file_is_missing -q
```

Expected: pass, or the known dependency install blocker.

- [ ] **Step 6: Commit**

```bash
git add src/job_hunting/profile_context.py src/job_hunting/tools/cv_generator.py tests/test_cv_generator.py
git commit -m "Normalize structured profile data for CV rendering" \
  -m "Pass typed YAML profile sections to the CV renderer as structured JSON instead of raw Markdown strings." \
  -m "Constraint: Renderer-facing data must preserve existing selection ids while carrying structured achievements and links." \
  -m "Rejected: Serializing section Markdown | the renderer should not parse profile evidence Markdown." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Keep normalized JSON backward-aware only at renderer boundaries, not as a second profile schema." \
  -m "Tested: uv run pytest tests/test_cv_generator.py::test_cv_generator_calls_node_script tests/test_cv_generator.py::test_cv_generator_falls_back_when_profile_section_file_is_missing -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 4: Render Structured CV Sections And Underlined Links

**Files:**
- Modify: `personalized-outreach/scripts/fill-template.js`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 1: Write failing Node renderer test for underlined links**

Add to `tests/test_cv_generator.py`:

```python
def test_cv_node_renderer_underlines_structured_profile_links(tmp_path):
    template_path = Path("personalized-outreach/templates/cv-template.md").resolve()
    script_path = Path("personalized-outreach/scripts/fill-template.js").resolve()
    tailored_path = tmp_path / "tailored.json"
    output_path = tmp_path / "cv.tex"
    profile_dir = tmp_path / "profile"
    normalized_profile_path = tmp_path / "normalized-profile.json"
    profile_dir.mkdir()

    tailored_path.write_text(
        json.dumps(
            {
                "summary": "Product leader for developer infrastructure.",
                "workExperienceIds": ["blockscout"],
                "workExperienceDescriptions": {},
                "projectIds": ["hush"],
                "projectDescriptions": {},
                "skills": ["Product strategy", "DeFi"],
            }
        ),
        encoding="utf-8",
    )
    normalized_profile_path.write_text(
        json.dumps(
            {
                "identity": {
                    "fullName": "Ada Lovelace",
                    "email": "ada@example.com",
                    "location": "London, UK",
                    "links": [],
                },
                "workExperience": [
                    {
                        "id": "blockscout",
                        "company": "Blockscout",
                        "position": "Senior Product Manager",
                        "period": "Aug 2022 - Apr 2026",
                        "companyDescription": "Open-source explorer platform",
                        "showOnCv": True,
                        "achievements": [
                            {
                                "area": "AI data integration",
                                "text": "Launched a blockchain data API for LLM assistants.",
                                "links": [
                                    {"label": "MCP docs", "url": "https://example.com/mcp"},
                                    {"label": "Launch post", "url": "https://example.com/launch"},
                                ],
                            }
                        ],
                    }
                ],
                "projects": [
                    {
                        "id": "hush",
                        "name": "Hush",
                        "title": "Crypto privacy payment solution",
                        "period": "Feb 2026 - Mar 2026",
                        "description": "Privacy-focused DeFi integration for Aave.",
                        "showOnCv": True,
                        "links": [{"label": "GitHub", "url": "https://github.com/0xdeval/hush"}],
                        "techStack": ["Aave", "Smart Contracts"],
                    }
                ],
                "education": [],
                "skillGroups": [{"name": "Product", "showOnCv": True, "skills": ["Product strategy"]}],
                "talks": [],
                "publications": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "node",
            str(script_path),
            str(template_path),
            str(tailored_path),
            str(output_path),
            str(profile_dir),
            str(normalized_profile_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rendered = output_path.read_text(encoding="utf-8")
    assert "\\href{https://example.com/mcp}{\\underline{MCP docs}}" in rendered
    assert "\\href{https://example.com/launch}{\\underline{Launch post}}" in rendered
    assert "MCP docs}. \\href{https://example.com/launch}" in rendered
    assert "\\href{https://github.com/0xdeval/hush}{\\underline{GitHub}}" in rendered
    assert "https://example.com/mcp}" in rendered
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_cv_generator.py::test_cv_node_renderer_underlines_structured_profile_links -q
```

Expected: failure because renderer does not yet format structured achievement links.

- [ ] **Step 3: Add link rendering helpers to Node script**

In `personalized-outreach/scripts/fill-template.js`, add after `boldMetrics`:

```javascript
function formatLinkLabel(link) {
  if (!link || !link.url || !link.label) return "";
  return `\\href{${link.url}}{\\underline{${escapeLatex(link.label)}}}`;
}

function formatLinkLabels(links) {
  if (!Array.isArray(links)) return "";
  return links
    .map(formatLinkLabel)
    .filter(Boolean)
    .join(". ");
}

function appendLinks(text, links) {
  const renderedLinks = formatLinkLabels(links);
  if (!renderedLinks) return text;
  return `${text} ${renderedLinks}`;
}

function visibleItems(items) {
  return Array.isArray(items)
    ? items.filter((item) => item && item.showOnCv !== false)
    : [];
}
```

- [ ] **Step 4: Update role achievement formatting**

Change `mergeRoleAchievements` to return structured achievement objects:

```javascript
function normalizeAchievement(achievement) {
  if (typeof achievement === "string") {
    return { text: achievement, area: "", links: [] };
  }
  return {
    area: achievement.area || "",
    text: achievement.text || "",
    links: Array.isArray(achievement.links) ? achievement.links : [],
  };
}

function mergeRoleAchievements(role, customDescriptions = {}, minBullets = 4, maxBullets = 5) {
  const tailored = (customDescriptions[role.id] || []).map((text) => ({
    area: "",
    text,
    links: [],
  }));
  const profileAchievements = (role.achievements || []).map(normalizeAchievement);
  const seen = new Set();
  const merged = [];

  [...tailored, ...profileAchievements].forEach((achievement) => {
    const key = `${achievement.area}|${achievement.text}`.toLowerCase().trim();
    if (!achievement.text || seen.has(key)) return;
    seen.add(key);
    merged.push(achievement);
  });

  if (merged.length === 0) return [];
  return merged.slice(0, Math.max(minBullets, Math.min(maxBullets, merged.length)));
}
```

Update `formatWorkExperience` bullet rendering:

```javascript
const bullets = achievements
  .map((achievement) => {
    const label = achievement.area ? `${achievement.area}: ` : "";
    const text = `${label}${capitalizeSentenceStart(achievement.text)}`;
    return `      \\resumeItem{${boldMetrics(appendLinks(escapeLatex(text), achievement.links))}}`;
  })
  .join("\n");
```

- [ ] **Step 5: Update project rendering**

Change `formatProjects`:

```javascript
function formatProjects(projects, customDescriptions = {}) {
  return visibleItems(projects)
    .map((proj) => {
      const descriptions = dedupeStrings([
        ...(customDescriptions[proj.id] || []),
        proj.description,
      ]).slice(0, 2);
      const bullets = descriptions
        .map((desc) =>
          `    \\resumeItem{${boldMetrics(escapeLatex(capitalizeSentenceStart(desc)))}}`
        )
        .join("\n");
      const titleParts = [escapeLatex(proj.name)];
      const links = formatLinkLabels(proj.links);
      if (links) titleParts.push(links);
      const techStack = Array.isArray(proj.techStack) && proj.techStack.length
        ? `\n    \\resumeItem{\\textbf{Tech:} ${escapeLatex(proj.techStack.join(", "))}}`
        : "";

      return `\\resumeProject
{${titleParts.join(" | ")}}{${escapeLatex(proj.period || "")}}
\\resumeItemListStart
${bullets}${techStack}
\\resumeItemListEnd`;
    })
    .join("\n\n");
}
```

- [ ] **Step 6: Add structured education and public performance renderers**

Replace Markdown section rendering at the end of `fillTemplate` with:

```javascript
template = template.replace(
  /==PUBLIC_SPEAKING_SECTION==/g,
  formatPublicPerformance(profile.talks || [], profile.publications || [])
);
template = template.replace(
  /==EDUCATION_SECTION==/g,
  formatEducation(profile.education || [])
);
```

Add:

```javascript
function formatEducation(education) {
  const items = visibleItems(education).map((item) => {
    const parts = [`${item.degree}, ${item.field} - ${item.institution}`];
    if (item.period) parts.push(item.period);
    if (item.grade) parts.push(item.grade);
    return `\\resumeItem{${appendLinks(escapeLatex(parts.join(", ")), item.links)}}`;
  });
  if (items.length === 0) return "";
  return `\\section{Education}\\sectionRule
\\resumeItemListStart
${items.join("\n")}
\\resumeItemListEnd`;
}

function formatPublicPerformance(talks, publications) {
  const talkItems = visibleItems(talks).map((talk) =>
    `\\resumeItem{${appendLinks(escapeLatex(`${talk.conference}: ${talk.title}`), talk.links)}}`
  );
  const publicationItems = visibleItems(publications).map((publication) => {
    const text = publication.description
      ? `${publication.title}: ${publication.description}`
      : publication.title;
    return `\\resumeItem{${appendLinks(escapeLatex(text), publication.links)}}`;
  });
  const items = [...talkItems, ...publicationItems];
  if (items.length === 0) return "";
  return `\\section{Public performance}\\sectionRule
\\resumeItemListStart
${items.join("\n")}
\\resumeItemListEnd`;
}
```

- [ ] **Step 7: Update normalized profile loading**

In `normalizeProfile`, assign structured arrays:

```javascript
profile.education = Array.isArray(normalized.education) ? normalized.education : [];
profile.skillGroups = Array.isArray(normalized.skillGroups) ? normalized.skillGroups : [];
profile.talks = Array.isArray(normalized.talks) ? normalized.talks : [];
profile.publications = Array.isArray(normalized.publications) ? normalized.publications : [];
```

Update skill replacement:

```javascript
template = template.replace(
  /==TOOLS AND STACK==/g,
  formatSkills(tailoredData.skills || visibleSkillNames(profile.skillGroups || []))
);
```

Add:

```javascript
function visibleSkillNames(skillGroups) {
  return visibleItems(skillGroups).flatMap((group) =>
    Array.isArray(group.skills) ? group.skills : []
  );
}
```

- [ ] **Step 8: Run CV renderer tests**

Run:

```bash
uv run pytest tests/test_cv_generator.py -q
```

Expected: pass, or known dependency install blocker.

- [ ] **Step 9: Commit**

```bash
git add personalized-outreach/scripts/fill-template.js tests/test_cv_generator.py
git commit -m "Render structured profile links in CVs" \
  -m "Teach the CV renderer to consume structured YAML-backed profile sections and show proof links as underlined clickable labels." \
  -m "Constraint: Visible PDF links must be HTTPS-only labels, not raw URLs." \
  -m "Rejected: Markdown section rendering for active profile data | structured normalized JSON is now the renderer contract." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Preserve underlined \\href labels whenever artifact links are visible." \
  -m "Tested: uv run pytest tests/test_cv_generator.py -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 5: Migrate Examples And Documentation

**Files:**
- Modify: `examples/knowledge/profile.yaml`
- Create: `examples/knowledge/profile/work-experience.yaml`
- Create: `examples/knowledge/profile/personal-projects.yaml`
- Create: `examples/knowledge/profile/education.yaml`
- Create: `examples/knowledge/profile/skills.yaml`
- Create: `examples/knowledge/profile/public-performance.yaml`
- Create: `examples/knowledge/profile/values-and-interests.yaml`
- Modify: `README.md`
- Modify: `docs/setup-guide.md`
- Modify: `tests/test_profile_context.py`

- [ ] **Step 1: Update example profile index**

Change `examples/knowledge/profile.yaml`:

```yaml
profile_sections:
  work_experience: profile/work-experience.yaml
  projects: profile/personal-projects.yaml
  education: profile/education.yaml
  skills: profile/skills.yaml
  public_speaking: profile/public-performance.yaml
  values: profile/values-and-interests.yaml
```

Keep existing `identity` and `search` data.

- [ ] **Step 2: Add example work experience YAML**

Create `examples/knowledge/profile/work-experience.yaml`:

```yaml
roles:
  - id: blockscout
    company: Blockscout
    title: Senior Product Manager
    period:
      start: 2022-08
      end: 2026-04
    industry: Blockchain / DeFi Infrastructure
    company_summary: Leading open-source blockchain explorer and SaaS infrastructure platform
    achievements:
      - area: Payment product strategy
        text: Led product strategy for a privacy-focused payment solution and scaled assets under management by 350% YoY.
        links:
          - label: Hush
            url: https://github.com/0xdeval/hush
      - area: Engagement SaaS add-on
        text: Launched an upsell add-on for blockchain network operators, driving a 280% MAU surge and 15+ ecosystem partnerships.
```

- [ ] **Step 3: Add example projects YAML**

Create `examples/knowledge/profile/personal-projects.yaml`:

```yaml
projects:
  - id: hush
    name: Hush
    title: Crypto privacy payment solution
    period:
      start: 2026-02
      end: 2026-03
    description: Privacy-focused DeFi integration for Aave that supports private collateral, borrow, repayment, and withdrawal flows.
    links:
      - label: GitHub
        url: https://github.com/0xdeval/hush
    tech_stack:
      - Aave
      - Privacy Infrastructure
      - Smart Contracts
```

- [ ] **Step 4: Add example education YAML**

Create `examples/knowledge/profile/education.yaml`:

```yaml
education:
  - id: hse-applied-math
    institution: Higher School of Economics
    degree: Bachelor's degree
    field: Computational and Applied Mathematics
    period:
      start: 2016-09
      end: 2020-06
    grade: GPA 8/10
```

- [ ] **Step 5: Add example skills YAML**

Create `examples/knowledge/profile/skills.yaml`:

```yaml
skill_groups:
  - name: Product
    skills:
      - Product strategy
      - Product discovery
      - Roadmap prioritization
      - Growth product management
  - name: Web3 / FinTech
    skills:
      - Web3
      - DeFi
      - Stablecoin payments
      - Blockchain infrastructure
```

- [ ] **Step 6: Add public performance and values examples**

Create `examples/knowledge/profile/public-performance.yaml`:

```yaml
talks:
  - id: example-product-summit-discovery
    conference: Example Product Summit
    title: Product discovery in regulated markets
    links:
      - label: Event
        url: https://example.com/product-summit

publications:
  - id: privacy-compliance-white-paper
    title: DeFi privacy and self-regulatory compliance white paper
    description: Authored a white paper on selective disclosure and AML screening for privacy-preserving protocols.
    links:
      - label: White paper
        url: https://example.com/privacy-white-paper
```

Create `examples/knowledge/profile/values-and-interests.yaml`:

```yaml
values:
  - id: ownership
    title: High ownership
    description: Prefers owning ambiguous product problems from discovery through launch.

interests:
  - id: privacy-preserving-products
    title: Privacy-preserving products
    description: Interested in products that make privacy usable without sacrificing compliance or user experience.
```

- [ ] **Step 7: Update README and setup guide**

In `README.md`, add or update the profile setup section with:

```markdown
Profile evidence is YAML-only. Keep identity and profile search preferences in
`knowledge/profile.yaml`, then point `profile_sections` at YAML files under
`knowledge/profile/`.

Links inside profile sections must use `https://`. When links appear in a
generated CV PDF, the visible label is underlined and clickable; raw URLs are
not shown.
```

In `docs/setup-guide.md`, add a section for each YAML file using the examples above. Explicitly say:

```markdown
`profile-summary.md` and `general-info.md` are no longer active profile files.
Summaries are generated from structured facts at runtime, and identity comes
from `profile.yaml.identity`.
```

- [ ] **Step 8: Update example tests**

Update `tests/test_profile_context.py::test_loads_example_profile_yaml` and `test_builds_application_context_from_example_profile_yaml`:

```python
assert config.profile_sections["skills"] == Path("profile/skills.yaml")
assert "Example Product Summit" in context.profile_sections_context
assert "Product discovery in regulated markets" in context.profile_sections_context
assert "profile-summary" not in context.profile_sections_context
```

- [ ] **Step 9: Run docs/example validation tests**

Run:

```bash
uv run pytest tests/test_profile_context.py::test_loads_example_profile_yaml tests/test_profile_context.py::test_builds_application_context_from_example_profile_yaml -q
```

Expected: pass, or known dependency install blocker.

- [ ] **Step 10: Commit**

```bash
git add examples/knowledge/profile.yaml examples/knowledge/profile/*.yaml README.md docs/setup-guide.md tests/test_profile_context.py
git commit -m "Document YAML profile section setup" \
  -m "Migrate examples and user documentation to the approved YAML-only profile evidence format." \
  -m "Constraint: Setup docs must explain HTTPS links and removed summary/general-info files." \
  -m "Rejected: Keeping Markdown examples as active setup guidance | examples should match the only supported format." \
  -m "Confidence: high" \
  -m "Scope-risk: narrow" \
  -m "Directive: Keep README and setup-guide aligned with profile_context validation rules." \
  -m "Tested: uv run pytest tests/test_profile_context.py::test_loads_example_profile_yaml tests/test_profile_context.py::test_builds_application_context_from_example_profile_yaml -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

### Task 6: Final Integration And Regression Pass

**Files:**
- Modify if needed: `src/job_hunting/flows/application_flow.py`
- Modify if needed: `src/job_hunting/flows/discovery_flow.py`
- Modify if needed: `src/job_hunting/crews/application/config/tasks.yaml`
- Modify if needed: `src/job_hunting/crews/discovery/config/tasks.yaml`
- Modify: any tests broken by context wording changes.

- [ ] **Step 1: Run targeted flow/config tests**

Run:

```bash
uv run pytest tests/test_application_flow.py tests/test_discovery_flow.py tests/test_application_crew_config.py tests/test_discovery_crew_config.py -q
```

Expected: pass, or failures only where tests assert old Markdown summary behavior.

- [ ] **Step 2: Fix flow tests without changing flow contracts**

If tests fail because mocked context strings changed, update test fixtures only. Keep existing crew input keys unchanged:

- `profile_sections_context`
- `identity_context`
- `candidate_scoring_context`
- `discovery_filter_context`

The flow functions should not need new orchestration behavior because context building remains behind `build_application_context()` and `build_discovery_context()`.

- [ ] **Step 3: Run focused profile and renderer tests**

Run:

```bash
uv run pytest tests/test_profile_context.py tests/test_cv_generator.py tests/test_application_flow.py tests/test_discovery_flow.py -q
```

Expected: pass, or known dependency install blocker.

- [ ] **Step 4: Run full suite if dependency environment supports it**

Run:

```bash
uv run pytest
```

Expected: pass. If blocked by `onnxruntime==1.26.0` macOS x86_64 wheel availability, record the blocker and include the targeted test results that were possible.

- [ ] **Step 5: Inspect diff for private data and Markdown dependency leaks**

Run:

```bash
rg -n "profile-summary|general-info|\\.md|http://" src tests examples README.md docs/setup-guide.md personalized-outreach/scripts/fill-template.js
```

Expected:

- No active `profile_sections` examples point to `.md`.
- No profile section validation allows `http://`.
- Any remaining `.md` references are historical docs or non-profile-template files and are intentionally explained.

- [ ] **Step 6: Final commit**

```bash
git add src tests examples README.md docs/setup-guide.md personalized-outreach/scripts/fill-template.js
git commit -m "Complete YAML profile section migration" \
  -m "Finish integration cleanup after converting profile evidence, context builders, examples, docs, and CV rendering to structured YAML sections." \
  -m "Constraint: Existing flow input keys remain stable for CrewAI tasks." \
  -m "Rejected: Changing flow orchestration | context construction is already isolated behind profile_context builders." \
  -m "Confidence: high" \
  -m "Scope-risk: moderate" \
  -m "Directive: Do not reintroduce Markdown profile evidence as an active artifact source." \
  -m "Tested: uv run pytest tests/test_profile_context.py tests/test_cv_generator.py tests/test_application_flow.py tests/test_discovery_flow.py -q" \
  -m "Not-tested: Full suite may remain blocked by onnxruntime wheel availability on macOS x86_64." \
  -m "Co-authored-by: OmX <omx@oh-my-codex.dev>"
```

---

## Self-Review

Spec coverage:

- YAML-only section files: Task 1 and Task 5.
- Separate section files under `knowledge/profile/`: Task 5.
- `profile-summary` and `general-info` removal: Task 1, Task 2, Task 5, Task 6.
- Work/projects/education/skills/public performance/values schemas: Task 1 and Task 5.
- HTTPS-only structured links: Task 1 and Task 4.
- Underlined clickable PDF labels: Task 4.
- Runtime summaries from structured facts: Task 2.
- Docs and setup guide: Task 5.
- Tests and regression checks: all tasks, especially Task 6.

No known gaps remain in the approved spec.
