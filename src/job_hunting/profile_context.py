from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ALLOWED_PROFILE_SECTION_KEYS = {
    "summary",
    "work_experience",
    "projects",
    "education",
    "skills",
    "public_speaking",
    "values",
}

DISCOVERY_SCORING_SECTIONS = ("summary", "skills", "work_experience")
ALLOWED_TOP_LEVEL_KEYS = {"identity", "search", "profile_sections"}


class ProfileConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LinkConfig:
    key: str
    label: str
    url: str
    display: str
    show_on_cv: bool = False


@dataclass(frozen=True)
class IdentityConfig:
    full_name: str
    preferred_name: str
    email: str
    location_base: str
    work_modes: tuple[str, ...]
    links: tuple[LinkConfig, ...]


@dataclass(frozen=True)
class RoleSearchConfig:
    primary: str
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class SenioritySearchConfig:
    target: str
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class LocationsSearchConfig:
    accepted: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class IndustriesSearchConfig:
    preferred: tuple[str, ...]


@dataclass(frozen=True)
class SearchConfig:
    roles: RoleSearchConfig
    seniority: SenioritySearchConfig
    locations: LocationsSearchConfig
    industries: IndustriesSearchConfig
    salary: str
    dealbreakers: tuple[str, ...]


@dataclass(frozen=True)
class ProfileConfig:
    path: Path
    root_dir: Path
    identity: IdentityConfig
    search: SearchConfig
    profile_sections: dict[str, Path]


@dataclass(frozen=True)
class DiscoveryProfileContext:
    filter_context: str
    scoring_context: str


@dataclass(frozen=True)
class ApplicationProfileContext:
    identity_context: str
    profile_sections_context: str
    section_keys: tuple[str, ...]


def load_profile_config(path: Path | str = "knowledge/profile.yaml") -> ProfileConfig:
    profile_path = Path(path)
    try:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ProfileConfigError(f"profile config not found: {profile_path}") from exc
    if not isinstance(raw, dict):
        raise ProfileConfigError("profile config must be a YAML mapping")

    _reject_unsupported_top_level_keys(raw)

    identity = _parse_identity(_require_mapping(raw, "identity"))
    search = _parse_search(_require_mapping(raw, "search"))
    profile_sections = _parse_profile_sections(
        _require_mapping(raw, "profile_sections")
    )

    return ProfileConfig(
        path=profile_path,
        root_dir=profile_path.parent,
        identity=identity,
        search=search,
        profile_sections=profile_sections,
    )


def build_discovery_context(
    path: Path | str = "knowledge/profile.yaml",
) -> DiscoveryProfileContext:
    config = load_profile_config(path)
    scoring_parts: list[str] = []
    for key in DISCOVERY_SCORING_SECTIONS:
        if key in config.profile_sections:
            scoring_parts.append(_read_section(config, key))
    if not scoring_parts:
        raise ProfileConfigError(
            "Discovery scoring requires at least one of profile_sections: "
            + ", ".join(DISCOVERY_SCORING_SECTIONS)
        )
    return DiscoveryProfileContext(
        filter_context=_format_discovery_filter_context(config),
        scoring_context="\n\n".join(scoring_parts),
    )


def build_application_context(
    path: Path | str = "knowledge/profile.yaml",
) -> ApplicationProfileContext:
    config = load_profile_config(path)
    section_parts = [_read_section(config, key) for key in config.profile_sections]
    return ApplicationProfileContext(
        identity_context=_format_identity_context(config.identity),
        profile_sections_context="\n\n".join(section_parts),
        section_keys=tuple(config.profile_sections.keys()),
    )


def _reject_unsupported_top_level_keys(raw: dict[str, Any]) -> None:
    unsupported_keys = sorted(set(raw) - ALLOWED_TOP_LEVEL_KEYS)
    if unsupported_keys:
        raise ProfileConfigError(
            f"unsupported top-level profile config key: {unsupported_keys[0]}"
        )


def _parse_identity(raw: dict[str, Any]) -> IdentityConfig:
    location = _require_mapping(raw, "location", prefix="identity")
    links_raw = raw.get("links", [])
    if not isinstance(links_raw, list):
        raise ProfileConfigError("identity.links must be a list")
    return IdentityConfig(
        full_name=_require_string(raw, "full_name", prefix="identity"),
        preferred_name=_require_string(raw, "preferred_name", prefix="identity"),
        email=_require_string(raw, "email", prefix="identity"),
        location_base=_require_string(location, "base", prefix="identity.location"),
        work_modes=tuple(
            _require_string_list(location, "work_modes", prefix="identity.location")
        ),
        links=tuple(_parse_link(item, index) for index, item in enumerate(links_raw)),
    )


def _parse_link(raw: Any, index: int) -> LinkConfig:
    if not isinstance(raw, dict):
        raise ProfileConfigError(f"identity.links[{index}] must be a mapping")
    return LinkConfig(
        key=_require_string(raw, "key", prefix=f"identity.links[{index}]"),
        label=_require_string(raw, "label", prefix=f"identity.links[{index}]"),
        url=_require_string(raw, "url", prefix=f"identity.links[{index}]"),
        display=str(raw.get("display") or raw.get("url") or ""),
        show_on_cv=bool(raw.get("show_on_cv", False)),
    )


def _parse_search(raw: dict[str, Any]) -> SearchConfig:
    roles = _require_mapping(raw, "roles", prefix="search")
    seniority = _require_mapping(raw, "seniority", prefix="search")
    locations = _require_mapping(raw, "locations", prefix="search")
    industries = _require_mapping(raw, "industries", prefix="search")
    return SearchConfig(
        roles=RoleSearchConfig(
            primary=_require_string(roles, "primary", prefix="search.roles"),
            accepted=tuple(
                _require_string_list(roles, "accepted", prefix="search.roles")
            ),
            excluded=tuple(
                _string_list(roles.get("excluded", []), "search.roles.excluded")
            ),
        ),
        seniority=SenioritySearchConfig(
            target=_require_string(seniority, "target", prefix="search.seniority"),
            accepted=tuple(
                _require_string_list(
                    seniority, "accepted", prefix="search.seniority"
                )
            ),
            excluded=tuple(
                _string_list(
                    seniority.get("excluded", []), "search.seniority.excluded"
                )
            ),
        ),
        locations=LocationsSearchConfig(
            accepted=tuple(
                _require_string_list(
                    locations, "accepted", prefix="search.locations"
                )
            ),
            excluded=tuple(
                _string_list(
                    locations.get("excluded", []), "search.locations.excluded"
                )
            ),
        ),
        industries=IndustriesSearchConfig(
            preferred=tuple(
                _require_string_list(
                    industries, "preferred", prefix="search.industries"
                )
            ),
        ),
        salary=_require_string(raw, "salary", prefix="search"),
        dealbreakers=tuple(
            _string_list(raw.get("dealbreakers", []), "search.dealbreakers")
        ),
    )


def _parse_profile_sections(raw: dict[str, Any]) -> dict[str, Path]:
    sections: dict[str, Path] = {}
    for key, value in raw.items():
        if key not in ALLOWED_PROFILE_SECTION_KEYS:
            raise ProfileConfigError(f"unsupported profile_sections key: {key}")
        if not isinstance(value, str) or not value.strip():
            raise ProfileConfigError(f"profile_sections.{key} must be a non-empty path")
        sections[key] = Path(value.strip())
    return sections


def _read_section(config: ProfileConfig, key: str) -> str:
    relative_path = config.profile_sections[key]
    full_path = config.root_dir / relative_path
    try:
        content = full_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ProfileConfigError(
            f"profile_sections.{key} points to {relative_path}, "
            "but the file does not exist"
        ) from exc
    return f"## {key}\n\n{content}"


def _format_identity_context(identity: IdentityConfig) -> str:
    links = "\n".join(
        f"- {link.label}: {link.url} ({link.display})" for link in identity.links
    )
    return (
        f"Full name: {identity.full_name}\n"
        f"Preferred name: {identity.preferred_name}\n"
        f"Email: {identity.email}\n"
        f"Location: {identity.location_base}\n"
        f"Work modes: {', '.join(identity.work_modes)}\n"
        f"Links:\n{links}"
    )


def _format_discovery_filter_context(config: ProfileConfig) -> str:
    search = config.search
    return "\n".join(
        [
            f"Primary role: {search.roles.primary}",
            f"Accepted roles: {', '.join(search.roles.accepted)}",
            f"Excluded roles: {', '.join(search.roles.excluded)}",
            f"Target seniority: {search.seniority.target}",
            f"Accepted seniority: {', '.join(search.seniority.accepted)}",
            f"Excluded seniority: {', '.join(search.seniority.excluded)}",
            f"Accepted locations: {', '.join(search.locations.accepted)}",
            f"Excluded locations: {', '.join(search.locations.excluded)}",
            f"Preferred industries: {', '.join(search.industries.preferred)}",
            f"Salary threshold: {search.salary}",
            f"Dealbreakers: {', '.join(search.dealbreakers)}",
            f"Candidate base location: {config.identity.location_base}",
            f"Candidate work modes: {', '.join(config.identity.work_modes)}",
        ]
    )


def _require_mapping(
    raw: dict[str, Any], key: str, prefix: str = ""
) -> dict[str, Any]:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, dict):
        raise ProfileConfigError(f"{name} is required and must be a mapping")
    return value


def _require_string(raw: dict[str, Any], key: str, prefix: str = "") -> str:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise ProfileConfigError(f"{name} is required")
    return value.strip()


def _require_string_list(
    raw: dict[str, Any], key: str, prefix: str = ""
) -> list[str]:
    value = raw.get(key)
    name = f"{prefix}.{key}" if prefix else key
    if value is None:
        raise ProfileConfigError(f"{name} is required")
    return _string_list(value, name)


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ProfileConfigError(f"{name} must be a list of strings")
    return [item.strip() for item in value]
