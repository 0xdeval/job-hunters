from pathlib import Path
from job_hunting.utils import vacancies_dir, scores_dir, applications_dir


def test_vacancies_dir():
    assert vacancies_dir("2026-05-10") == Path("data/2026-05-10/vacancies")


def test_scores_dir():
    assert scores_dir("2026-05-10") == Path("data/2026-05-10/scores")


def test_applications_dir():
    result = applications_dir("2026-05-10", "acme--senior-pm")
    assert result == Path("data/2026-05-10/applications/acme--senior-pm")
