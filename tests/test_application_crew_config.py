from pathlib import Path

import yaml


def _tasks_config() -> dict:
    return yaml.safe_load(
        Path("src/job_hunting/crews/application/config/tasks.yaml").read_text(
            encoding="utf-8"
        )
    )


def test_profile_brief_task_uses_prepared_application_context():
    description = _tasks_config()["profile_brief_task"]["description"]

    assert "{identity_context}" in description
    assert "{profile_sections_context}" in description
    assert "Read all profile files from knowledge/profile/" not in description
    assert "general-info.md" not in description


def test_application_artifact_tasks_do_not_read_profile_files_directly():
    tasks = _tasks_config()

    for task_name in ("cv_task", "cover_letter_task"):
        description = tasks[task_name]["description"]
        assert "Do not read files under knowledge/profile/" in description
        assert "knowledge/profile/work-experience.md" not in description
        assert "projects.md" not in description


def test_cv_and_cover_letter_tasks_receive_identity_context():
    tasks = _tasks_config()

    assert "{identity_context}" in tasks["cv_task"]["description"]
    assert "{identity_context}" in tasks["cover_letter_task"]["description"]


def test_artifact_tasks_use_company_title_filename_base():
    tasks = _tasks_config()

    assert "data/{date}/applications/{vacancy_id}/{artifact_filename_base}-QA.md" in (
        tasks["qa_task"]["description"]
    )
    assert "data/{date}/applications/{vacancy_id}/{artifact_filename_base}-CV.tex" in (
        tasks["cv_task"]["description"]
    )
    assert (
        "data/{date}/applications/{vacancy_id}/{artifact_filename_base}-CoverLetter.tex"
        in tasks["cover_letter_task"]["description"]
    )
