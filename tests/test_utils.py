from pathlib import Path
from job_hunting.utils import (
    applications_dir,
    discovery_coverage_file,
    scores_dir,
    vacancies_dir,
)


def test_vacancies_dir():
    assert vacancies_dir("2026-05-10") == Path("data/2026-05-10/vacancies")


def test_scores_dir():
    assert scores_dir("2026-05-10") == Path("data/2026-05-10/scores")


def test_applications_dir():
    result = applications_dir("2026-05-10", "acme--senior-pm")
    assert result == Path("data/2026-05-10/applications/acme--senior-pm")


def test_discovery_coverage_file_uses_run_date():
    assert discovery_coverage_file("2026-05-12") == Path(
        "data/2026-05-12/discovery_coverage.csv"
    )
