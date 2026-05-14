from pathlib import Path

import pytest

from job_hunting.profile_context import (
    ProfileConfigError,
    build_application_context,
    build_discovery_context,
    load_profile_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _valid_profile_yaml(*, profile_sections: str = "summary: profile/summary.md") -> str:
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


def test_loads_example_profile_yaml():
    config = load_profile_config(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert config.identity.full_name == "Alex Candidate"
    assert config.identity.preferred_name == "Alex"
    assert config.identity.links[0].key == "linkedin"
    assert config.search.roles.primary == "Product Manager"
    assert config.profile_sections["skills"] == Path("profile/skills.md")


def test_builds_application_context_from_example_profile_yaml():
    context = build_application_context(PROJECT_ROOT / "examples/knowledge/profile.yaml")

    assert "Alex Candidate" in context.identity_context
    assert "Example Product Summit" in context.profile_sections_context
    assert "Product discovery in regulated markets" in context.profile_sections_context


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

    with pytest.raises(
        ProfileConfigError, match="unsupported profile_sections key: unsupported"
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
  summary: profile/missing-summary.md
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ProfileConfigError,
        match=(
            "profile_sections.summary points to profile/missing-summary.md, "
            "but the file does not exist"
        ),
    ):
        build_application_context(profile_yaml)


def test_discovery_context_rejects_profile_without_scoring_sections(tmp_path):
    root = tmp_path / "knowledge"
    profile_dir = root / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "projects.md").write_text("Side project details.", encoding="utf-8")
    profile_yaml = root / "profile.yaml"
    profile_yaml.write_text(
        _valid_profile_yaml(profile_sections="projects: profile/projects.md"),
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
    (profile_dir / "profile-summary.md").write_text(
        "Senior PM with fintech and AI experience.", encoding="utf-8"
    )
    (profile_dir / "skills.md").write_text(
        "- Product strategy\n- SQL\n", encoding="utf-8"
    )
    (profile_dir / "work-experience.md").write_text(
        "## Acme -- Senior Product Manager\n\n- Grew activation by 30%.",
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
    (profile_dir / "profile-summary.md").write_text(
        "Approved summary.", encoding="utf-8"
    )
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
