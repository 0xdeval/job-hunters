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
    profile_sections = SimpleNamespace(
        work_experience=(
            SimpleNamespace(
                id="analytical-engines",
                company="Analytical Engines Ltd",
                title="Product Lead",
                period=SimpleNamespace(start="1842-01", end="1843-12"),
                industry="Computing",
                company_summary="Mechanical computation company",
                show_on_cv=True,
                achievements=(
                    SimpleNamespace(
                        area="Launch",
                        text="Shipped programmable workflows.",
                        links=(
                            SimpleNamespace(
                                label="Proof", url="https://example.com/proof"
                            ),
                        ),
                    ),
                ),
            ),
        ),
        projects=(),
        education=(),
        skills=(),
        talks=(),
        publications=(),
        values=(),
        interests=(),
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
        patch(
            "job_hunting.tools.cv_generator.load_profile_sections",
            return_value=profile_sections,
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
        assert captured_profile["workExperience"][0]["position"] == "Product Lead"
        assert captured_profile["workExperience"][0]["period"] == "Jan 1842 - Dec 1843"
        assert captured_profile["workExperience"][0]["achievements"][0]["area"] == "Launch"
        assert (
            captured_profile["workExperience"][0]["achievements"][0]["links"][0]["label"]
            == "Proof"
        )
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
        patch(
            "job_hunting.tools.cv_generator.load_profile_sections",
            side_effect=OSError("profile section missing"),
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


def test_cv_node_renderer_renders_structured_profile_artifacts(tmp_path):
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
                "workExperienceIds": ["hidden-role", "early-role", "analytical-engines"],
                "workExperienceDescriptions": {},
                "projectIds": ["hidden-project", "hush"],
                "projectDescriptions": {
                    "hush": ["Built private collaboration workflows."]
                },
                "skills": "",
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
                    "links": [],
                },
                "sections": {
                    "education": "## Education\n\n- Legacy University should not render",
                    "public_speaking": "## Public speaking\n\n- LegacyConf should not render",
                },
                "workExperience": [
                    {
                        "id": "early-role",
                        "company": "Early Engines",
                        "position": "Analyst",
                        "location": "London, UK",
                        "period": "Jan 1842 - Dec 1843",
                        "companyDescription": "Computing research lab",
                        "achievements": [
                            "Documented early computing programs [cite: 1].",
                            "Documented early computing programs.",
                        ],
                    },
                    {
                        "id": "hidden-role",
                        "company": "Hidden Engines",
                        "position": "Hidden Role",
                        "period": "Jan 1845 - Dec 1845",
                        "companyDescription": "Hidden company",
                        "showOnCv": False,
                        "achievements": ["Hidden achievement."],
                    },
                    {
                        "id": "analytical-engines",
                        "company": "Analytical Engines Ltd",
                        "position": "Product Lead",
                        "location": "London, UK",
                        "period": "Feb 1844 - Present",
                        "companyDescription": "Mechanical computation company",
                        "achievements": [
                            {
                                "area": "Launch",
                                "text": "Shipped programmable workflows",
                                "links": [
                                    {
                                        "label": "Hush",
                                        "url": "https://example.com/hush",
                                    },
                                    {
                                        "label": "Growthcast",
                                        "url": "https://example.com/growthcast",
                                    },
                                ],
                            }
                        ],
                    },
                ],
                "projects": [
                    {
                        "id": "hush",
                        "name": "Hush",
                        "period": "Mar 1844 - Apr 1844",
                        "description": "Encrypted team notes.",
                        "techStack": ["Node.js", "PostgreSQL"],
                        "links": [
                            {
                                "label": "Demo",
                                "url": "https://example.com/demo?x=50%25&ok=1#frag",
                            }
                        ],
                    },
                    {
                        "id": "hidden-project",
                        "name": "Hidden Project",
                        "description": "Hidden project description.",
                        "showOnCv": False,
                        "links": [],
                    },
                ],
                "education": [
                    {
                        "institution": "University of London",
                        "degree": "Certificate",
                        "field": "Mathematics",
                        "period": "1841 - 1842",
                        "grade": "Distinction",
                        "links": [
                            {
                                "label": "Transcript",
                                "url": "https://example.com/transcript",
                            }
                        ],
                    },
                    {
                        "institution": "Hidden University",
                        "degree": "Hidden Degree",
                        "field": "Hidden Field",
                        "showOnCv": False,
                        "links": [],
                    }
                ],
                "skillGroups": [
                    {
                        "label": "Product",
                        "skills": ["Roadmaps", "Launch strategy"],
                    },
                    {
                        "label": "Technical",
                        "skills": ["SQL", "Node.js"],
                    },
                    {
                        "label": "Hidden Skills",
                        "skills": ["Hidden skill"],
                        "showOnCv": False,
                    },
                ],
                "talks": [
                    {
                        "conference": "ProductConf",
                        "title": "Computing products for teams",
                        "links": [
                            {
                                "label": "Slides",
                                "url": "https://example.com/slides",
                            }
                        ],
                    },
                    {
                        "conference": "HiddenConf",
                        "title": "Hidden talk",
                        "showOnCv": False,
                        "links": [],
                    }
                ],
                "publications": [
                    {
                        "title": "Notes on the Analytical Engine",
                        "description": "A practical computing reference.",
                        "links": [
                            {
                                "label": "Paper",
                                "url": "https://example.com/paper",
                            }
                        ],
                    },
                    {
                        "title": "Hidden Publication",
                        "description": "Hidden publication description.",
                        "showOnCv": False,
                        "links": [],
                    }
                ],
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
    assert "Product Lead | Analytical Engines Ltd" in rendered
    assert "Analyst | Early Engines" in rendered
    assert "Hidden Engines" not in rendered
    assert "Hidden Project" not in rendered
    assert "Hidden University" not in rendered
    assert "Hidden Skills" not in rendered
    assert "HiddenConf" not in rendered
    assert "Hidden Publication" not in rendered
    assert rendered.count("Documented early computing programs") == 1
    assert rendered.index("Product Lead | Analytical Engines Ltd") < rendered.index(
        "Analyst | Early Engines"
    )
    assert (
        "Launch: Shipped programmable workflows "
        "\\href{https://example.com/hush}{\\underline{Hush}}. "
        "\\href{https://example.com/growthcast}{\\underline{Growthcast}}"
    ) in rendered
    assert "{Hush}{Mar 1844 - Apr 1844}" in rendered
    assert (
        "\\href{https://example.com/demo?x=50\\%25\\&ok=1\\#frag}{\\underline{Demo}}"
        in rendered
    )
    assert "Node.js, PostgreSQL" in rendered
    assert "University of London --- Certificate, Mathematics --- 1841 - 1842 --- Distinction" in rendered
    assert "\\href{https://example.com/transcript}{\\underline{Transcript}}" in rendered
    assert "ProductConf --- Computing products for teams" in rendered
    assert "\\href{https://example.com/slides}{\\underline{Slides}}" in rendered
    assert "Notes on the Analytical Engine --- A practical computing reference." in rendered
    assert "\\href{https://example.com/paper}{\\underline{Paper}}" in rendered
    assert "\\textbf{Product:} Roadmaps, Launch strategy" in rendered
    assert "\\textbf{Technical:} SQL, Node.js" in rendered
    assert "Legacy University should not render" not in rendered
    assert "LegacyConf should not render" not in rendered


def test_cv_node_renderer_formats_public_speaking_markdown_as_cv_bullets(tmp_path):
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
                "summary": "Product leader for protocol economics.",
                "workExperienceIds": ["protocol-labs"],
                "workExperienceDescriptions": {
                    "protocol-labs": ["Launched node economics programs."]
                },
                "projectIds": [],
                "projectDescriptions": {},
                "skills": "Product strategy, Web3",
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
                    "links": [],
                },
                "sections": {
                    "public_speaking": """# Public Performance

## Conferences & Talks

### Speaker at EthCC

**Topic:** Scaling DeFi and Privacy Infrastructure.

### Speaker at DappCon

**Topic:** Web3 Growth and Protocol Adoption.

### Other Speaking Engagements

- **ETH Dam**
- **ETH Belgrade**
- **Gnosis meetup**

---

## Publications / Articles

- **White Paper: Blockchain privacy and self-regulatory compliance: methods and applications** — Focuses on private payment solutions and zk-based compliance.
""",
                },
                "workExperience": [
                    {
                        "id": "protocol-labs",
                        "company": "Protocol Labs",
                        "position": "Product Lead",
                        "location": "Remote",
                        "period": "Jan 2024 -- Present",
                        "companyDescription": "Protocol infrastructure company",
                        "achievements": ["Designed token economics workflows."],
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
    assert "Speaker at EthCC --- Scaling DeFi and Privacy Infrastructure." in rendered
    assert "Speaker at DappCon --- Web3 Growth and Protocol Adoption." in rendered
    assert "ETH Dam" in rendered
    assert "White Paper: Blockchain privacy" in rendered
    assert "\\resumeItem{\\textbf{Topic:}" not in rendered
    assert "\\resumeItem{---}" not in rendered
