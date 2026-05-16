import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from job_hunting.profile_context import (
    ProfileConfigError,
    format_period_for_display,
    load_profile_config,
    load_profile_sections,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = PROJECT_ROOT / "personalized-outreach/templates/cv-template.md"
SCRIPT_PATH = PROJECT_ROOT / "personalized-outreach/scripts/fill-template.js"
PROFILE_DIR = PROJECT_ROOT / "knowledge/profile"
PROFILE_CONFIG_PATH = PROJECT_ROOT / "knowledge/profile.yaml"


class CVGeneratorInput(BaseModel):
    tailored_json: str = Field(
        description="JSON string with tailored CV data: summary, workExperienceIds, "
        "workExperienceDescriptions, projectIds, projectDescriptions, skills"
    )
    output_tex_path: str = Field(description="Absolute or relative path for the output .tex file")


class CVGeneratorTool(BaseTool):
    name: str = "CV Generator"
    description: str = (
        "Generate a tailored CV PDF from the candidate's profile. "
        "Provide tailored JSON data and the output file path. "
        "Returns the path to the generated PDF, or an error message."
    )
    args_schema: type[BaseModel] = CVGeneratorInput

    def _run(self, tailored_json: str, output_tex_path: str) -> str:
        output_path = Path(output_tex_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_paths: list[Path] = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="tailored-cv-"
        ) as f:
            f.write(tailored_json)
            json_path = f.name
        temp_paths.append(Path(json_path))

        try:
            command = [
                "node",
                str(SCRIPT_PATH),
                str(TEMPLATE_PATH),
                json_path,
                str(output_path),
                str(PROFILE_DIR),
            ]
            normalized_profile_path = _create_normalized_profile_json()
            if normalized_profile_path is not None:
                temp_paths.append(Path(normalized_profile_path))
                command.append(normalized_profile_path)

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return f"Error generating .tex: {result.stderr}"

            pdf_path = output_path.with_suffix(".pdf")
            tex_dir = str(output_path.parent)

            draft_result = subprocess.run(
                [
                    "pdflatex",
                    "-draftmode",
                    "-interaction=nonstopmode",
                    f"-output-directory={tex_dir}",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )
            if draft_result.returncode != 0:
                return (
                    f"LaTeX validation failed. Fix the .tex file before converting to PDF.\n"
                    f"Errors:\n{draft_result.stdout[-2000:]}"
                )

            compile_result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    f"-output-directory={tex_dir}",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )
            if compile_result.returncode != 0:
                return f"PDF compilation failed:\n{compile_result.stdout[-2000:]}"

            return str(pdf_path)
        finally:
            for temp_path in temp_paths:
                temp_path.unlink(missing_ok=True)


def _create_normalized_profile_json() -> str | None:
    try:
        profile = load_profile_config(PROFILE_CONFIG_PATH)
        sections = load_profile_sections(profile)
    except (OSError, ProfileConfigError):
        return None

    normalized_profile = {
        "identity": {
            "fullName": profile.identity.full_name,
            "preferredName": profile.identity.preferred_name,
            "email": profile.identity.email,
            "location": profile.identity.location_base,
            "workModes": list(profile.identity.work_modes),
            "links": [
                {
                    "key": link.key,
                    "label": link.label,
                    "url": link.url,
                    "display": link.display,
                    "showOnCv": link.show_on_cv,
                }
                for link in profile.identity.links
            ],
        },
        "workExperience": _work_experience_to_json(sections.work_experience),
        "projects": _projects_to_json(sections.projects),
        "education": _education_to_json(sections.education),
        "skillGroups": _skill_groups_to_json(sections.skills),
        "talks": _talks_to_json(sections.talks),
        "publications": _publications_to_json(sections.publications),
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="normalized-profile-"
    ) as f:
        json.dump(normalized_profile, f)
        return f.name


def _links_to_json(links: Any) -> list[dict[str, str]]:
    return [
        {
            "label": link.label,
            "url": link.url,
        }
        for link in links
    ]


def _work_experience_to_json(roles: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": role.id,
            "company": role.company,
            "position": role.title,
            "period": format_period_for_display(role.period),
            "industry": role.industry,
            "companyDescription": role.company_summary,
            "showOnCv": role.show_on_cv,
            "achievements": [
                {
                    "area": achievement.area,
                    "text": achievement.text,
                    "links": _links_to_json(achievement.links),
                }
                for achievement in role.achievements
            ],
        }
        for role in roles
    ]


def _projects_to_json(projects: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": project.id,
            "name": project.name,
            "title": project.title,
            "period": format_period_for_display(project.period),
            "description": project.description,
            "showOnCv": project.show_on_cv,
            "links": _links_to_json(project.links),
            "techStack": list(project.tech_stack),
        }
        for project in projects
    ]


def _education_to_json(education: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "institution": item.institution,
            "degree": item.degree,
            "field": item.field,
            "period": format_period_for_display(item.period),
            "grade": item.grade,
            "showOnCv": item.show_on_cv,
            "links": _links_to_json(item.links),
        }
        for item in education
    ]


def _skill_groups_to_json(skill_groups: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": group.name,
            "showOnCv": group.show_on_cv,
            "skills": list(group.skills),
        }
        for group in skill_groups
    ]


def _talks_to_json(talks: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": talk.id,
            "conference": talk.conference,
            "title": talk.title,
            "showOnCv": talk.show_on_cv,
            "links": _links_to_json(talk.links),
        }
        for talk in talks
    ]


def _publications_to_json(publications: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": publication.id,
            "title": publication.title,
            "description": publication.description,
            "showOnCv": publication.show_on_cv,
            "links": _links_to_json(publication.links),
        }
        for publication in publications
    ]
