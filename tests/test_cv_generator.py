import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from job_hunting.tools.cv_generator import CVGeneratorTool


SAMPLE_TAILORED_JSON = {
    "summary": "Experienced product manager with strong Web3 background.",
    "workExperienceIds": ["blockscout"],
    "workExperienceDescriptions": {
        "blockscout": ["Grew MAU by **300%** via product-led growth initiatives"]
    },
    "projectIds": [],
    "projectDescriptions": {},
    "skills": "Product strategy, Web3, DeFi, SQL, Python",
}


def test_cv_generator_calls_node_script(tmp_path):
    tool = CVGeneratorTool()
    output_path = tmp_path / "cv.tex"

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    captured_profile: dict = {}
    captured_temp_paths: list[Path] = []
    profile_config = SimpleNamespace(
        root_dir=tmp_path,
        identity=SimpleNamespace(
            full_name="Ada Lovelace",
            preferred_name="Ada",
            email="ada@example.com",
            location_base="London, UK",
            work_modes=("Remote",),
            links=(),
        ),
        profile_sections={},
    )

    def fake_run(command, **kwargs):
        if command[0] == "node":
            captured_temp_paths.extend([Path(command[3]), Path(command[6])])
            captured_profile.update(json.loads(Path(command[6]).read_text(encoding="utf-8")))
        return mock_result

    with (
        patch(
            "job_hunting.tools.cv_generator.load_profile_config",
            return_value=profile_config,
        ),
        patch("subprocess.run", side_effect=fake_run) as mock_run,
    ):
        tool._run(
            tailored_json=json.dumps(SAMPLE_TAILORED_JSON),
            output_tex_path=str(output_path),
        )
        assert mock_run.call_count >= 1
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "fill-template.js" in " ".join(first_call_args)
        assert len(first_call_args) == 7
        assert captured_profile["identity"]["fullName"] == "Ada Lovelace"
        assert all(not path.exists() for path in captured_temp_paths)


def test_cv_generator_falls_back_when_profile_section_file_is_missing(tmp_path):
    tool = CVGeneratorTool()
    output_path = tmp_path / "cv.tex"
    missing_section = tmp_path / "missing.md"
    profile_config = SimpleNamespace(
        root_dir=tmp_path,
        identity=SimpleNamespace(
            full_name="Ada Lovelace",
            preferred_name="Ada",
            email="ada@example.com",
            location_base="London, UK",
            work_modes=("Remote",),
            links=(),
        ),
        profile_sections={"education": missing_section},
    )

    with (
        patch(
            "job_hunting.tools.cv_generator.load_profile_config",
            return_value=profile_config,
        ),
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run,
    ):
        tool._run(
            tailored_json=json.dumps(SAMPLE_TAILORED_JSON),
            output_tex_path=str(output_path),
        )

    first_call_args = mock_run.call_args_list[0][0][0]
    assert "fill-template.js" in " ".join(first_call_args)
    assert len(first_call_args) == 6


def test_cv_generator_raises_on_node_error(tmp_path):
    tool = CVGeneratorTool()
    output_path = tmp_path / "cv.tex"

    mock_result = MagicMock(returncode=1, stdout="", stderr="Error: template not found")

    with patch("subprocess.run", return_value=mock_result):
        result = tool._run(
            tailored_json=json.dumps(SAMPLE_TAILORED_JSON),
            output_tex_path=str(output_path),
        )
        assert "Error" in result


def test_cv_node_renderer_uses_profile_yaml_identity_and_sections(tmp_path):
    template_path = Path("personalized-outreach/templates/cv-template.md").resolve()
    script_path = Path("personalized-outreach/scripts/fill-template.js").resolve()
    tailored_path = tmp_path / "tailored.json"
    output_path = tmp_path / "cv.tex"
    profile_dir = tmp_path / "profile"
    normalized_profile_path = tmp_path / "normalized-profile.json"
    profile_dir.mkdir()

    tailored_path.write_text(
        json.dumps(
            {
                "summary": "Product leader for analytical engines.",
                "workExperienceIds": ["analytical-engines"],
                "workExperienceDescriptions": {
                    "analytical-engines": ["Launched reliable computation products."]
                },
                "projectIds": [],
                "projectDescriptions": {},
                "skills": "Product strategy, Computing",
            }
        ),
        encoding="utf-8",
    )
    normalized_profile_path.write_text(
        json.dumps(
            {
                "identity": {
                    "fullName": "Ada Lovelace",
                    "email": "ada@example.com",
                    "location": "London, UK",
                    "links": [
                        {
                            "label": "Portfolio",
                            "url": "https://example.com/ada",
                            "display": "example.com/ada",
                            "showOnCv": True,
                        }
                    ],
                },
                "sections": {
                    "education": "## Education\n\n- University of London, Mathematics",
                    "public_speaking": "## Public speaking\n\n- ProductConf: Computing products for teams",
                },
                "workExperience": [
                    {
                        "id": "analytical-engines",
                        "company": "Analytical Engines Ltd",
                        "position": "Product Lead",
                        "location": "London, UK",
                        "period": "Jan 1842 -- Dec 1843",
                        "companyDescription": "Mechanical computation company",
                        "achievements": ["Shipped programmable workflows."],
                    }
                ],
                "projects": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "node",
            str(script_path),
            str(template_path),
            str(tailored_path),
            str(output_path),
            str(profile_dir),
            str(normalized_profile_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rendered = output_path.read_text(encoding="utf-8")
    assert "Ada Lovelace" in rendered
    assert "London, UK" in rendered
    assert "University of London" in rendered
    assert "ProductConf" in rendered
    assert "Mike" not in rendered
    assert "Higher School of Economics" not in rendered
    assert "ETHCC" not in rendered
    assert "DappCon" not in rendered
    assert "Data Science and analyst experience" not in rendered
