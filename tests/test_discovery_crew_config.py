from pathlib import Path

import yaml


def _scrape_task_description() -> str:
    config_path = Path("src/job_hunting/crews/discovery/config/tasks.yaml")
    tasks_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return tasks_config["scrape_vacancies_task"]["description"]


def test_scrape_task_handles_one_provided_company():
    description = _scrape_task_description()

    assert "{company}" in description
    assert "{career_page}" in description
    assert "one company" in description.lower()


def test_scrape_task_does_not_read_or_loop_through_company_csv():
    description = _scrape_task_description().lower()

    assert "read knowledge/companies.csv" not in description
    assert "for each company" not in description
    assert "every company from knowledge/companies.csv" not in description
    assert "run window" not in description
    assert "batch" not in description
    assert "not_attempted" not in description
