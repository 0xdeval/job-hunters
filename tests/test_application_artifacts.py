from job_hunting.application_artifacts import artifact_filename, artifact_filename_base


def test_artifact_filename_base_uses_company_and_title_pascal_case():
    assert (
        artifact_filename_base("Kraken", "Senior Product Manager")
        == "Kraken-SeniorProductManager"
    )


def test_artifact_filename_removes_punctuation_from_company_and_title():
    assert (
        artifact_filename("Chainlink Labs", "Product Manager - Compliance", "CV", ".pdf")
        == "ChainlinkLabs-ProductManagerCompliance-CV.pdf"
    )
