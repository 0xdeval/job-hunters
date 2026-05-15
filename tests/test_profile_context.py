from pathlib import Path

import pytest

from job_hunting.profile_context import (
    ProfileConfigError,
    build_application_context,
    build_discovery_context,
    load_profile_config,
    load_profile_sections,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _valid_profile_yaml(
    *, profile_sections: str = "work_experience: profile/work-experience.yaml"
) -> str:
    return f"""
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
  {profile_sections}
"""


def _write_valid_profile_yaml(path: Path, content: str | None = None) -> Path:
    path.write_text(content or _valid_profile_yaml(), encoding="utf-8")
    return path


def _write_profile_section(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_loads_example_profile_yaml():
    config = load_profile_config(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert config.identity.full_name == "Alex Candidate"
    assert config.identity.preferred_name == "Alex"
    assert config.identity.links[0].key == "linkedin"
    assert config.search.roles.primary == "Product Manager"
    assert config.profile_sections["skills"] == Path("profile/skills.yaml")
    assert "summary" not in config.profile_sections


def test_profile_sections_must_point_to_yaml_files(tmp_path):
    profile_yaml = tmp_path / "profile.yaml"
    _write_valid_profile_yaml(
        profile_yaml,
        _valid_profile_yaml(
            profile_sections="work_experience: profile/work-experience.md"
        ),
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
    assert config.profile_sections["work_experience"] == Path(
        "profile/work-experience.yaml"
    )
    assert "summary" not in config.profile_sections


def test_load_profile_sections_parses_yaml_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(
        root,
        "profile/work-experience.yaml",
        """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2024-01, end: present}
    industry: SaaS
    company_summary: Product analytics platform
    show_on_cv: false
    achievements:
      - area: Activation
        text: Grew activation by 30%.
        links:
          - label: Case study
            url: https://example.com/case-study
""",
    )
    _write_profile_section(
        root,
        "profile/projects.yaml",
        """
projects:
  - id: launch-kit
    name: Launch Kit
    title: Founder
    period: {start: 2023-02, end: 2023-11}
    description: Product launch automation.
    links:
      - label: Demo
        url: https://example.com/demo
    tech_stack: [Python, SQL]
""",
    )
    _write_profile_section(
        root,
        "profile/skills.yaml",
        """
skill_groups:
  - name: Product
    show_on_cv: false
    skills: [Discovery, Roadmapping]
""",
    )
    _write_valid_profile_yaml(
        profile_yaml,
        _valid_profile_yaml(
            profile_sections="""
  work_experience: profile/work-experience.yaml
  projects: profile/projects.yaml
  skills: profile/skills.yaml
"""
        ),
    )

    sections = load_profile_sections(load_profile_config(profile_yaml))

    role = sections.work_experience[0]
    assert role.company == "Acme"
    assert role.period.start == "2024-01"
    assert role.period.end == "present"
    assert role.show_on_cv is False
    assert role.achievements[0].links[0].url == "https://example.com/case-study"

    project = sections.projects[0]
    assert project.name == "Launch Kit"
    assert project.period is not None
    assert project.period.end == "2023-11"
    assert project.show_on_cv is True
    assert project.links[0].label == "Demo"
    assert project.tech_stack == ("Python", "SQL")

    skill_group = sections.skills[0]
    assert skill_group.name == "Product"
    assert skill_group.show_on_cv is False
    assert skill_group.skills == ("Discovery", "Roadmapping")


@pytest.mark.parametrize(
    ("period", "expected_message"),
    [
        ("{start: 2026-00, end: present}", "period.start must use YYYY-MM"),
        ("{start: 2026-13, end: present}", "period.start must use YYYY-MM"),
        ("{start: present, end: present}", "period.start must use YYYY-MM"),
    ],
)
def test_load_profile_sections_rejects_invalid_period_start_values(
    tmp_path, period, expected_message
):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(
        root,
        "profile/work-experience.yaml",
        f"""
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {period}
    achievements:
      - area: Activation
        text: Grew activation by 30%.
""",
    )
    _write_valid_profile_yaml(profile_yaml)

    with pytest.raises(ProfileConfigError, match=expected_message):
        load_profile_sections(load_profile_config(profile_yaml))


def test_load_profile_sections_allows_present_period_end(tmp_path):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(
        root,
        "profile/work-experience.yaml",
        """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2026-12, end: present}
    achievements:
      - area: Activation
        text: Grew activation by 30%.
""",
    )
    _write_valid_profile_yaml(profile_yaml)

    sections = load_profile_sections(load_profile_config(profile_yaml))

    assert sections.work_experience[0].period.start == "2026-12"
    assert sections.work_experience[0].period.end == "present"


@pytest.mark.parametrize(
    ("section_content", "expected_message"),
    [
        (
            """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2024-01, end: present}
    show_on_cv: "false"
    achievements:
      - area: Activation
        text: Grew activation by 30%.
""",
            "work_experience.roles\\[0\\].show_on_cv must be a boolean",
        ),
        (
            """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2024-01, end: 2026-99}
    achievements:
      - area: Activation
        text: Grew activation by 30%.
""",
            "work_experience.roles\\[0\\].period.end must use YYYY-MM",
        ),
        (
            """
roles:
  - id: acme
    company: Acme
    title: Senior Product Manager
    period: {start: 2024-01, end: present}
    achievements:
      - area: Activation
        text: Grew activation by 30%.
        links:
          - label: Case study
            url: http://example.com/case-study
""",
            "work_experience.roles\\[0\\].achievements\\[0\\].links\\[0\\].url "
            "must be an https URL",
        ),
        (
            "roles: []\n",
            "work_experience.roles must be a non-empty list",
        ),
    ],
)
def test_load_profile_sections_rejects_invalid_work_experience(
    tmp_path, section_content, expected_message
):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(root, "profile/work-experience.yaml", section_content)
    _write_valid_profile_yaml(profile_yaml)

    with pytest.raises(ProfileConfigError, match=expected_message):
        load_profile_sections(load_profile_config(profile_yaml))


def test_load_profile_sections_rejects_non_mapping_section_yaml(tmp_path):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(root, "profile/work-experience.yaml", "- not a mapping\n")
    _write_valid_profile_yaml(profile_yaml)

    with pytest.raises(
        ProfileConfigError,
        match="profile_sections.work_experience must be a YAML mapping",
    ):
        load_profile_sections(load_profile_config(profile_yaml))


def test_optional_period_present_but_malformed_reports_mapping_error(tmp_path):
    root = tmp_path / "knowledge"
    profile_yaml = root / "profile.yaml"
    root.mkdir()
    _write_profile_section(
        root,
        "profile/projects.yaml",
        """
projects:
  - id: launch-kit
    name: Launch Kit
    period: 2024-01
    description: Product launch automation.
""",
    )
    _write_valid_profile_yaml(
        profile_yaml,
        _valid_profile_yaml(profile_sections="projects: profile/projects.yaml"),
    )

    with pytest.raises(
        ProfileConfigError,
        match="projects.projects\\[0\\].period must be a mapping",
    ):
        load_profile_sections(load_profile_config(profile_yaml))


def test_builds_application_context_from_example_profile_yaml():
    context = build_application_context(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert "Alex Candidate" in context.identity_context
    assert "Example Product Summit" in context.profile_sections_context
    assert "Product discovery in regulated markets" in context.profile_sections_context


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
    assert (
        "Case study: https://example.com/case-study"
        in context.profile_sections_context
    )
    assert "## Skills" in context.profile_sections_context
    assert "Product: Product strategy, Activation" in context.profile_sections_context


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
  unsupported: profile/unsupported.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ProfileConfigError, match="unsupported profile_sections key: unsupported"
    ):
        load_profile_config(profile_yaml)


def test_rejects_summary_profile_section_key(tmp_path):
    profile_yaml = tmp_path / "profile.yaml"
    profile_yaml.write_text(
        _valid_profile_yaml(profile_sections="summary: profile/profile-summary.yaml"),
        encoding="utf-8",
    )

    with pytest.raises(
        ProfileConfigError, match="unsupported profile_sections key: summary"
    ):
        load_profile_config(profile_yaml)


def test_missing_profile_yaml_raises_profile_config_error(tmp_path):
    missing_profile = tmp_path / "knowledge" / "profile.yaml"

    with pytest.raises(
        ProfileConfigError, match=f"profile config not found: {missing_profile}"
    ):
        load_profile_config(missing_profile)


def test_rejects_unsupported_top_level_key(tmp_path):
    profile_yaml = tmp_path / "profile.yaml"
    _write_valid_profile_yaml(
        profile_yaml,
        _valid_profile_yaml()
        + """
discovery_scoring_sections:
  - projects
""",
    )

    with pytest.raises(
        ProfileConfigError,
        match="unsupported top-level profile config key: discovery_scoring_sections",
    ):
        load_profile_config(profile_yaml)


@pytest.mark.parametrize("missing_key", ["identity", "search", "profile_sections"])
def test_rejects_missing_top_level_required_mappings(tmp_path, missing_key):
    profile_yaml = tmp_path / "profile.yaml"
    lines = _valid_profile_yaml().splitlines()
    section_starts = {
        index
        for index, line in enumerate(lines)
        if line and not line.startswith(" ") and line.endswith(":")
    }
    start = next(index for index, line in enumerate(lines) if line == f"{missing_key}:")
    later_starts = sorted(index for index in section_starts if index > start)
    end = later_starts[0] if later_starts else len(lines)
    profile_yaml.write_text("\n".join(lines[:start] + lines[end:]), encoding="utf-8")

    with pytest.raises(
        ProfileConfigError,
        match=f"{missing_key} is required and must be a mapping",
    ):
        load_profile_config(profile_yaml)


@pytest.mark.parametrize(
    ("profile_yaml", "expected_message"),
    [
        (
            _valid_profile_yaml().replace("  full_name: Alex Candidate\n", ""),
            "identity.full_name is required",
        ),
        (
            _valid_profile_yaml().replace("    primary: Product Manager\n", ""),
            "search.roles.primary is required",
        ),
        (
            _valid_profile_yaml().replace("    work_modes: [Remote]\n", ""),
            "identity.location.work_modes is required",
        ),
    ],
)
def test_rejects_missing_required_nested_fields(
    tmp_path, profile_yaml, expected_message
):
    config_path = _write_valid_profile_yaml(tmp_path / "profile.yaml", profile_yaml)

    with pytest.raises(ProfileConfigError, match=expected_message):
        load_profile_config(config_path)


def test_application_context_rejects_listed_missing_profile_section_file(tmp_path):
    root = tmp_path / "knowledge"
    (root / "profile").mkdir(parents=True)
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
  work_experience: profile/missing-work-experience.yaml
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ProfileConfigError,
        match=(
            "profile_sections.work_experience points to "
            "profile/missing-work-experience.yaml, "
            "but the file does not exist"
        ),
    ):
        build_application_context(profile_yaml)


def test_discovery_context_rejects_profile_without_scoring_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "education.yaml").write_text(
        """
education:
  - id: degree
    institution: Example University
    degree: MBA
    field: Business
""",
        encoding="utf-8",
    )
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        _valid_profile_yaml(profile_sections="education: profile/education.yaml"),
        encoding="utf-8",
    )

    with pytest.raises(
        ProfileConfigError,
        match="Discovery scoring requires at least one of profile_sections",
    ):
        build_discovery_context(profile_yaml)


def test_discovery_context_uses_search_and_system_owned_scoring_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "skills.yaml").write_text(
        """
skill_groups:
  - name: Product
    skills: [Product strategy, SQL]
""",
        encoding="utf-8",
    )
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
  skills: profile/skills.yaml
  work_experience: profile/work-experience.yaml
""",
        encoding="utf-8",
    )

    context = build_discovery_context(profile_yaml)

    assert "Product Manager" in context.filter_context
    assert "US-only remote" in context.filter_context
    assert "Product strategy" in context.scoring_context
    assert "Grew activation by 30%" in context.scoring_context


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
        _valid_profile_yaml(
            profile_sections="work_experience: profile/work-experience.yaml"
        ),
        encoding="utf-8",
    )

    context = build_discovery_context(profile_yaml)

    assert "Generated candidate scoring context" in context.scoring_context
    assert "Acme - Senior Product Manager" in context.scoring_context
    assert "Grew activation by 30%" in context.scoring_context


def test_search_salary_is_optional_and_omitted_from_discovery_context_when_absent(
    tmp_path,
):
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
      - area: Fintech
        text: Built fintech products.
""",
        encoding="utf-8",
    )
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
  dealbreakers: []
profile_sections:
  work_experience: profile/work-experience.yaml
""",
        encoding="utf-8",
    )

    config = load_profile_config(profile_yaml)
    context = build_discovery_context(profile_yaml)
    application_context = build_application_context(profile_yaml)

    assert config.search.salary is None
    assert "Salary threshold:" not in context.filter_context
    assert "Alex Candidate" in application_context.identity_context


def test_application_context_reads_only_allowlisted_sections(tmp_path):
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
      - area: Evidence
        text: Approved work evidence.
""",
        encoding="utf-8",
    )
    (profile_dir / "hidden.yaml").write_text("Hidden fact.", encoding="utf-8")
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
  work_experience: profile/work-experience.yaml
""",
        encoding="utf-8",
    )

    context = build_application_context(profile_yaml)

    assert "Alex Candidate" in context.identity_context
    assert "Approved work evidence." in context.profile_sections_context
    assert "Hidden fact." not in context.profile_sections_context
