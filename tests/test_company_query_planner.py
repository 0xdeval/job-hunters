from pathlib import Path

import pytest

from job_hunting.tools.company_query_planner import CompanyQueryPlanner


def _write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "company-source-queries.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_enabled_domains_and_templates_expand_to_deduped_queries(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
      - jobs.lever.co
  web_search:
    enabled: true
    templates:
      - "site:{domain} {role} {seniority} {industry}"
      - "site:{domain} {role} {seniority} {industry}"
      - "{role} {seniority} {industry} remote Europe"
""",
    )

    planner = CompanyQueryPlanner(config_path)

    queries = planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Senior"],
        industries=["FinTech"],
    )

    assert queries == [
        "site:jobs.ashbyhq.com Product Manager Senior FinTech",
        "site:jobs.lever.co Product Manager Senior FinTech",
        "Product Manager Senior FinTech remote Europe",
    ]


def test_disabled_groups_are_ignored(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
source_groups:
  ats_search:
    enabled: false
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: false
    templates:
      - "site:{domain} {role}"
      - "{role} remote"
""",
    )

    planner = CompanyQueryPlanner(config_path)

    queries = planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Senior"],
        industries=["FinTech"],
    )

    assert queries == []


def test_missing_config_raises_file_not_found_error(tmp_path):
    planner = CompanyQueryPlanner(tmp_path / "missing-company-source-queries.yaml")

    with pytest.raises(FileNotFoundError):
        planner.plan_queries(
            roles=["Product Manager"],
            seniorities=["Senior"],
            industries=["FinTech"],
        )


def test_unsupported_template_field_raises_value_error(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: true
    templates:
      - "{role} {location}"
""",
    )

    planner = CompanyQueryPlanner(config_path)

    with pytest.raises(ValueError, match="Unsupported template fields: location"):
        planner.plan_queries(
            roles=["Product Manager"],
            seniorities=["Senior"],
            industries=["FinTech"],
        )


def test_default_config_path_reads_knowledge_file(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "company-source-queries.yaml").write_text(
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: true
    templates:
      - "site:{domain} {role} {industry}"
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    planner = CompanyQueryPlanner()

    assert planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Senior"],
        industries=["FinTech"],
    ) == ["site:jobs.ashbyhq.com Product Manager FinTech"]


def test_blank_queries_are_filtered(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
source_groups:
  ats_search:
    enabled: true
    domains:
      - jobs.ashbyhq.com
  web_search:
    enabled: true
    templates:
      - "   "
      - "{role} remote"
""",
    )

    planner = CompanyQueryPlanner(config_path)

    assert planner.plan_queries(
        roles=["Product Manager"],
        seniorities=["Senior"],
        industries=["FinTech"],
    ) == ["Product Manager remote"]


def test_query_planner_rejects_unsafe_yaml_tags(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
!!python/object/apply:os.system ["echo unsafe"]
""",
    )

    with pytest.raises(Exception):
        CompanyQueryPlanner(config_path).plan_queries(
            roles=["Product Manager"],
            seniorities=["Senior"],
            industries=["FinTech"],
        )
