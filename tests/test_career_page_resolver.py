from __future__ import annotations

from job_hunting.tools.career_page_resolver import CareerPageResolver, SearchResult


def test_resolver_prefers_supported_ats_over_generic_career_url():
    resolver = CareerPageResolver()
    results = [
        SearchResult(title="Company Careers", url="https://company.com/careers"),
        SearchResult(title="Greenhouse", url="https://job-boards.greenhouse.io/company"),
    ]

    assert resolver.resolve("Company", results) == "https://job-boards.greenhouse.io/company"


def test_resolver_accepts_greenhouse_eu_and_bamboohr_careers():
    resolver = CareerPageResolver()

    greenhouse_eu = [
        SearchResult(
            title="Greenhouse EU",
            url="https://job-boards.eu.greenhouse.io/company",
        )
    ]
    bamboohr = [
        SearchResult(
            title="BambooHR",
            url="https://company.bamboohr.com/careers",
        )
    ]

    assert resolver.resolve("Company", greenhouse_eu) == greenhouse_eu[0].url
    assert resolver.resolve("Company", bamboohr) == bamboohr[0].url


def test_resolver_falls_back_to_career_like_url_then_empty():
    resolver = CareerPageResolver()

    career_like = [
        SearchResult(title="About", url="https://company.com/about"),
        SearchResult(title="Jobs", url="https://company.com/work-with-us"),
    ]
    unsupported = [
        SearchResult(title="Home", url="https://company.com"),
        SearchResult(title="Blog", url="https://company.com/blog"),
    ]

    assert resolver.resolve("Company", career_like) == "https://company.com/work-with-us"
    assert resolver.resolve("Company", unsupported) == ""


def test_resolver_skips_competitor_ats_and_picks_company_career_url():
    resolver = CareerPageResolver()
    results = [
        SearchResult(
            title="Competitor Greenhouse",
            url="https://job-boards.greenhouse.io/competitor",
        ),
        SearchResult(
            title="Acme Work With Us",
            url="https://acme.com/work-with-us",
        ),
    ]

    assert resolver.resolve("Acme Inc", results) == "https://acme.com/work-with-us"


def test_resolver_ignores_blog_jobs_report_path():
    resolver = CareerPageResolver()
    results = [
        SearchResult(
            title="Acme blog",
            url="https://acme.com/blog/jobs-report-2026",
        )
    ]

    assert resolver.resolve("Acme", results) == ""
