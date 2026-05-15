import subprocess
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from job_hunting.profile_context import load_profile_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = PROJECT_ROOT / "personalized-outreach/templates/cover-letter.md"


class CoverLetterInput(BaseModel):
    intro: str = Field(description="Opening paragraph, 60-80 words")
    main_body: str = Field(description="Main body paragraphs, 150-200 words total")
    conclusion: str = Field(description="Closing paragraph, 40-60 words")
    output_tex_path: str = Field(description="Path for the output .tex file")


def profile_preferred_name() -> str:
    return load_profile_config(PROJECT_ROOT / "knowledge/profile.yaml").identity.preferred_name


def escape_latex(text: str) -> str:
    if not text:
        return ""
    return (
        text
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
        .replace("—", "---")
        .replace("–", "--")
        .replace("’", "'")
        .replace("‘", "`")
        .replace("“", "``")
        .replace("”", "''")
    )


class CoverLetterTool(BaseTool):
    name: str = "Cover Letter Generator"
    description: str = (
        "Fill the cover letter LaTeX template with the provided content sections "
        "and compile to PDF. Returns the PDF path or an error message."
    )
    args_schema: type[BaseModel] = CoverLetterInput

    def _run(self, intro: str, main_body: str, conclusion: str, output_tex_path: str) -> str:
        output_path = Path(output_tex_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        template = TEMPLATE_PATH.read_text()
        filled = (
            template
            .replace("==INTRO==", escape_latex(intro))
            .replace("==MAIN BODY==", escape_latex(main_body))
            .replace("==CONCLUSION==", escape_latex(conclusion))
            .replace("==SIGNATURE==", escape_latex(profile_preferred_name()))
        )
        output_path.write_text(filled)

        tex_dir = str(output_path.parent)

        draft = subprocess.run(
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
        if draft.returncode != 0:
            return (
                f"LaTeX validation failed. Fix the cover letter before converting to PDF.\n"
                f"Errors:\n{draft.stdout[-2000:]}"
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

        return str(output_path.with_suffix(".pdf"))
