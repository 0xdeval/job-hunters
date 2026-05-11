from __future__ import annotations

from itertools import product
from pathlib import Path
from string import Formatter

import yaml

SUPPORTED_TEMPLATE_FIELDS = {"role", "seniority", "industry", "domain"}


class CompanyQueryPlanner:
    def __init__(self, config_path: Path | str = "knowledge/company-source-queries.yaml"):
        self.config_path = Path(config_path)

    def plan_queries(
        self, roles: list[str], seniorities: list[str], industries: list[str]
    ) -> list[str]:
        config = self._load_config()
        source_groups = config.get("source_groups", {})

        ats_group = source_groups.get("ats_search", {})
        ats_domains = ats_group.get("domains", []) if ats_group.get("enabled") else []

        web_group = source_groups.get("web_search", {})
        templates = web_group.get("templates", []) if web_group.get("enabled") else []

        queries: list[str] = []

        for template in templates:
            fields = self._template_fields(template)
            unsupported_fields = fields - SUPPORTED_TEMPLATE_FIELDS
            if unsupported_fields:
                unsupported_list = ", ".join(sorted(unsupported_fields))
                raise ValueError(f"Unsupported template fields: {unsupported_list}")

            uses_domain = "domain" in fields

            for role, seniority, industry in product(roles, seniorities, industries):
                context = {
                    "role": role,
                    "seniority": seniority,
                    "industry": industry,
                }

                if uses_domain:
                    for domain in ats_domains:
                        query = template.format(**context, domain=domain).strip()
                        if query:
                            queries.append(query)
                else:
                    query = template.format(**context).strip()
                    if query:
                        queries.append(query)

        return self._dedupe_preserve_order(queries)

    def _load_config(self) -> dict:
        # Intentionally allow FileNotFoundError to bubble up.
        content = self.config_path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(content)
        return loaded if isinstance(loaded, dict) else {}

    @staticmethod
    def _template_fields(template: str) -> set[str]:
        formatter = Formatter()
        fields: set[str] = set()
        for _, field_name, _, _ in formatter.parse(template):
            if field_name:
                fields.add(field_name)
        return fields

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped
