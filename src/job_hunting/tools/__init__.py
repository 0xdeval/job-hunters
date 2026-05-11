from importlib import import_module
from typing import Any

__all__ = [
    "DedupTool",
    "TelegramNotifierTool",
    "CVGeneratorTool",
    "CoverLetterTool",
    "SafeSeleniumScrapingTool",
    "CompanyCandidate",
    "CompanyCandidateStore",
]


def __getattr__(name: str) -> Any:
    module_map = {
        "DedupTool": "job_hunting.tools.dedup_tool",
        "TelegramNotifierTool": "job_hunting.tools.telegram_notifier",
        "CVGeneratorTool": "job_hunting.tools.cv_generator",
        "CoverLetterTool": "job_hunting.tools.cover_letter_tool",
        "SafeSeleniumScrapingTool": "job_hunting.tools.safe_selenium_scraper",
        "CompanyCandidate": "job_hunting.tools.company_candidate_store",
        "CompanyCandidateStore": "job_hunting.tools.company_candidate_store",
    }
    if name not in module_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_map[name])
    return getattr(module, name)
