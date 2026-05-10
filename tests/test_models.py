import json
from job_hunting.models import VacancyStatus, vacancy_id_from


def test_vacancy_status_values():
    assert VacancyStatus.PENDING_APPROVAL == "pending_approval"
    assert VacancyStatus.APPROVED == "approved"
    assert VacancyStatus.DECLINED == "declined"
    assert VacancyStatus.DOCUMENTS_READY == "documents_ready"
    assert VacancyStatus.APPLIED == "applied"
    assert VacancyStatus.NOT_APPLIED == "not_applied"
    assert VacancyStatus.SKIPPED == "skipped"


def test_vacancy_id_from():
    assert vacancy_id_from("Acme Corp", "Senior Product Manager") == "acme-corp--senior-product-manager"
    assert vacancy_id_from("Web3 Inc.", "Head of Product") == "web3-inc--head-of-product"
    assert vacancy_id_from("A & B", "PM") == "a--b--pm"
