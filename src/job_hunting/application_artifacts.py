import re


def artifact_filename_base(company: str, title: str) -> str:
    return f"{_pascal_case(company)}-{_pascal_case(title)}"


def artifact_filename(company: str, title: str, label: str, extension: str) -> str:
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    return f"{artifact_filename_base(company, title)}-{label}{normalized_extension}"


def artifact_filename_candidates(
    company: str,
    title: str,
    label: str,
    extensions: list[str],
    legacy_names: list[str],
) -> list[str]:
    return [
        artifact_filename(company, title, label, extension)
        for extension in extensions
    ] + legacy_names


def _pascal_case(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    if not words:
        return "Unknown"
    return "".join(word[:1].upper() + word[1:] for word in words)
