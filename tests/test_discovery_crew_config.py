from pathlib import Path

import yaml


def _tasks_config() -> dict:
    config_path = Path("src/job_hunting/crews/discovery/config/tasks.yaml")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _scrape_task_description() -> str:
    return _tasks_config()["scrape_vacancies_task"]["description"]


def _scrape_task_expected_output() -> str:
    return _tasks_config()["scrape_vacancies_task"]["expected_output"]


def _vacancy_scout_max_iter() -> int:
    config_path = Path("src/job_hunting/crews/discovery/config/agents.yaml")
    agents_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return agents_config["vacancy_scout"]["max_iter"]


def test_scrape_task_handles_one_provided_company():
    description = _scrape_task_description().lower()

    assert "one company only" in description
    assert "{company}" in description
    assert "{career_page}" in description
    assert "{discovery_filter_context}" in description


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


def test_scrape_task_does_not_read_or_loop_through_company_csv():
    description = _scrape_task_description().lower()

    assert "companies.csv" not in description
    assert "run window" not in description
    assert "for each company" not in description
    assert "every company" not in description
    assert "batching" not in description
    assert "not_attempted" not in description


def test_scrape_task_requires_skipped_and_failed_coverage_reasons():
    description = _scrape_task_description().lower()

    assert 'status: "skipped"' in description
    assert "provided career_page is unusable" in description
    assert "notes: specific reason" in description

    assert 'status: "failed"' in description
    assert "tool error, timeout, http error, or unexpected page failure" in description
    assert "notes: specific reason" in description


def test_scrape_task_requires_completed_coverage_fields():
    description = _scrape_task_description().lower()

    assert 'status: "completed"' in description
    assert "jobs_found" in description
    assert "matched_jobs" in description
    assert "notes: useful summary notes" in description


def test_scrape_task_expected_output_is_single_company():
    expected_output = _scrape_task_expected_output().lower()

    assert "{company}" in expected_output
    assert "saved for this kickoff's {company}" in expected_output


def test_vacancy_scout_iteration_budget_is_per_company():
    assert _vacancy_scout_max_iter() == 30
