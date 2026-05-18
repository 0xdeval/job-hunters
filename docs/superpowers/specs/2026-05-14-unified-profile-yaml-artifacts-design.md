# Unified Profile YAML and Artifact Personalization Design

**Date:** 2026-05-14
**Status:** Pending written-spec review

> Archival note: this design spec predates the follow-up structured profile
> section migration. Any references below to Markdown profile section files or
> a `summary` profile section are historical design context, not the current
> supported setup. Current docs live in `README.md` and `docs/setup-guide.md`.

## Objective

Introduce a structured `knowledge/profile.yaml` contract that becomes the
user-facing source of truth for identity, job-search filters, and allowlisted
profile evidence files.

The goal is to let each user personalize discovery and generated application
artifacts by editing private files under `knowledge/`, without modifying code or
templates and without relying on LLM inference from unstructured Markdown for
core control data.

## Scope

In scope:

- Replace `knowledge/profile.yaml` usage in Discovery Crew with
  `knowledge/profile.yaml.search`.
- Use `knowledge/profile.yaml.identity` for generated artifact identity fields.
- Use `knowledge/profile.yaml.profile_sections` as an explicit allowlist of
  profile evidence files available to application artifact tasks.
- Keep detailed factual evidence in `knowledge/profile/*.md`.
- Add `skills` as a first-class optional profile section.
- Remove person-specific hardcoding from current CV and cover letter rendering.
- Commit `examples/knowledge/profile.yaml` as the template/example.
- Keep real `knowledge/profile.yaml` private and untracked.

Out of scope:

- Full CV renderer migration from Node to Python. The first implementation
  should keep current renderers and remove hardcoding. A later phase may move
  CV rendering into Python.
- Arbitrary custom `profile_sections` keys. The supported section set should
  stay small and predictable.

## Current State

Discovery currently has two agents:

- `vacancy_scout`
  - receives `today`, `company`, and `career_page`
  - reads `knowledge/profile.yaml`
  - scrapes career pages and job pages
  - writes vacancy JSON files under `data/<date>/vacancies/`
- `fit_analyst`
  - reads vacancy JSON files
  - reads `knowledge/profile.yaml`
  - reads `knowledge/profile/profile-summary.md`
  - writes score JSON files under `data/<date>/scores/`

Application currently has four agents:

- `profile_steward`
  - reads a hardcoded set of `knowledge/profile/*.md` files
  - produces a tailored profile brief
- `qa_analyst`
  - uses the profile brief and vacancy questions
- `cv_architect`
  - uses the profile brief and `CVGeneratorTool`
- `cover_letter_writer`
  - uses the profile brief and `CoverLetterTool`

Hardcoded personalization currently exists in:

- `personalized-outreach/templates/cv-template.md`
  - fixed public speaking content
  - fixed education content
- `personalized-outreach/scripts/fill-template.js`
  - forced `Remote` work location
  - fixed skill categories
  - forced data-science role/bullet injection
  - contact parsing from Markdown instead of structured identity
- `personalized-outreach/templates/cover-letter.md`
  - hardcoded `Mike` signature

## Profile YAML Contract

`knowledge/profile.yaml` has three user-facing top-level sections:

```yaml
identity:
  full_name: Mike Krupin
  preferred_name: Mike
  email: krupin.mihailw@gmail.com
  location:
    base: Lisbon, Portugal
    work_modes:
      - Remote
      - Remote Europe
      - Hybrid Lisbon
  links:
    - key: linkedin
      label: LinkedIn
      url: https://www.linkedin.com/in/mike-krupin/
      display: mike-krupin
      show_on_cv: true
    - key: github
      label: GitHub
      url: https://github.com/0xdeval
      display: 0xdeval
      show_on_cv: true
    - key: x
      label: X
      url: https://twitter.com/mike_krupin
      display: "@mike_krupin"
      show_on_cv: true

search:
  roles:
    primary: Product Manager
    accepted:
      - Product Manager
      - AI Product Manager
      - Crypto Product Manager
    excluded:
      - Product Owner
      - Project Manager
  seniority:
    target: Senior
    accepted:
      - Middle
      - Senior
      - Lead
      - Staff
      - Associate
    excluded:
      - Intern
      - Junior
      - Director
  locations:
    accepted:
      - Remote
      - Remote Europe
      - Portugal
      - Lisbon
      - Spain Remote
    excluded:
      - US-only remote
      - Canada-only remote
      - Non-Portugal hybrid
  industries:
    preferred:
      - FinTech
      - AI
      - Crypto
      - SaaS
  salary: "$120000+"
  dealbreakers:
    - Requires relocation outside Portugal
    - Requires onsite outside Lisbon

profile_sections:
  summary: profile/profile-summary.md
  work_experience: profile/work-experience.md
  projects: profile/personal-projects.md
  education: profile/education.md
  skills: profile/skills.md
  public_speaking: profile/public-speaking.md
  values: profile/values-and-interests.md
```

### Identity

`identity` contains stable person metadata used by renderers and crews:

- `full_name`
- `preferred_name`
- `email`
- `location.base`
- `location.work_modes`
- `links`

Links are a list of objects, not fixed keys, so users can add LinkedIn, GitHub,
X, portfolio, blog, personal site, Calendly, or other links without schema
changes. Renderers use `show_on_cv` and list order to decide which links appear
in the CV header.

### Search

`search` is structured only. It replaces free-form `profile.yaml.search` for
Discovery Crew filtering and scoring.

It contains:

- role preferences
- seniority preferences
- location preferences and exclusions
- preferred industries
- salary threshold string
- dealbreakers

No free-form notes field should be added. Search criteria should remain explicit
and machine-validatable.

### Profile Sections

`profile_sections` is an explicit allowlist of profile evidence files. Only
listed files may be used by application artifact tasks.

Supported keys:

- `summary`
- `work_experience`
- `projects`
- `education`
- `skills`
- `public_speaking`
- `values`

If a section key is missing, that topic is unavailable. The system should not
fall back to conventional filenames. If a listed file is missing, validation
should fail before crews run.

Other material should live inside the supported files instead of adding custom
top-level section keys:

- certifications, courses, awards -> `education`
- publications, talks, media -> `public_speaking`
- portfolio, case studies, open-source -> `projects`
- interests, work style, motivation -> `values`

## Real vs Example Profile Files

The real user profile remains private:

- `knowledge/profile.yaml`
- `knowledge/profile/*.md`

The repository should commit:

- `examples/knowledge/profile.yaml`
- existing or updated example `examples/knowledge/profile/*` files as needed

This lets users copy and adapt an example without committing private candidate
data.

## Discovery Crew Design

Discovery should receive context prepared by code, not decide which files to
read on its own.

Add a profile context builder that:

1. Reads and validates `knowledge/profile.yaml`.
2. Validates `identity`, `search`, and `profile_sections`.
3. Validates any profile files needed by the selected crew context.
4. Builds deterministic context strings or objects for crew kickoff inputs.

### Vacancy Scout

The Vacancy Scout should receive:

- `today`
- `company`
- `career_page`
- `discovery_filter_context`

`discovery_filter_context` should be built from:

- `profile.yaml.search`
- `profile.yaml.identity.location`

The Vacancy Scout should not receive full work history, projects, education,
public speaking, values, or long profile prose. Its job is to find and filter
plausible job listings from watched-company career pages.

### Fit Analyst

The Fit Analyst should receive:

- vacancy JSON content
- `discovery_filter_context`
- `candidate_scoring_context`

`candidate_scoring_context` is selected by system-owned code, not user YAML.
Default scoring sections should be:

- `summary`
- `skills`
- `work_experience`

The builder should include whichever of these system-owned scoring sections are
present in `profile_sections`. If none of `summary`, `skills`, or
`work_experience` is present, Discovery validation should fail because the Fit
Analyst would have no candidate profile context for scoring.

## Application Crew Design

Application should use a brief plus structured metadata model.

Add an application context builder that:

1. Reads and validates `knowledge/profile.yaml`.
2. Reads only files listed under `profile_sections`.
3. Builds:
   - identity context
   - profile section content context
   - vacancy context
   - artifact policy context

### Profile Steward

Profile Steward remains the central distillation point.

It receives:

- vacancy context
- identity context
- allowlisted profile section content

It produces a tailored profile brief for downstream agents. It may summarize and
select evidence, but it must not invent achievements, education, links, public
proof, or candidate facts not present in the structured identity or allowlisted
profile files.

### Q&A Analyst

Q&A Analyst receives:

- vacancy questions
- vacancy description
- profile brief

It writes answers using only facts from the profile brief.

### CV Architect

CV Architect receives:

- profile brief
- identity context
- section availability metadata
- CV best-practices guidance

It produces CV tailoring JSON. The renderer fills identity and supported
sections from structured context and tailored content.

### Cover Letter Writer

Cover Letter Writer receives:

- profile brief
- identity context
- cover letter requirement flag
- cover letter best-practices guidance

It produces intro/body/conclusion content. The renderer signs the letter with
`identity.preferred_name`, not a hardcoded name.

## Artifact Rendering Rules

Phase 1 should adapt current renderers and remove hardcoding in place.

CV rendering must:

- render header from `identity`
- render only links where `show_on_cv` is true
- render public speaking only if `public_speaking` exists and has usable content
- render education only if `education` exists and has usable content
- avoid hardcoded location values such as `Remote`
- remove forced data-science role inclusion and injected data-science bullet
- avoid fixed Mike-specific school, talks, publications, or narrative content

Cover letter rendering must:

- keep generated intro/body/conclusion behavior
- render signature from `identity.preferred_name`
- avoid hardcoded candidate names

Phase 2 may migrate CV rendering from Node to Python after tests cover current
behavior and the hardcoding removal.

## Validation and Errors

Before running Discovery or Application crews:

- `profile.yaml` must exist.
- Required `identity` and `search` fields must be present for Discovery.
- Required `identity` and `profile_sections` fields must be present for
  Application.
- Every path listed in `profile_sections` and needed by the current crew context
  must exist.
- Unknown profile section keys should fail validation.
- Missing optional sections should omit those sections from artifacts.

Validation errors should be explicit and actionable, for example:

- `profile_sections.education points to profile/education.md, but the file does not exist`
- `search.roles.primary is required`
- `identity.links[2].url is required`

## Testing Strategy

Tests should cover:

- parsing and validating `examples/knowledge/profile.yaml`
- rejecting unknown `profile_sections` keys
- rejecting listed-but-missing profile files
- Discovery context builder output
- Application context builder output
- CV output with a synthetic second candidate
- cover letter signature with a synthetic second candidate
- absence of Mike-specific strings when synthetic profile data is used

Synthetic candidate tests should assert that output does not contain:

- `Mike`
- `Krupin`
- `Higher School of Economics`
- hardcoded ETHCC/DappCon/public-speaking content
- forced `Remote`
- forced data-science injected bullet

## Implementation Planning Handoff

The implementation plan should preserve this design boundary:

- user-owned YAML defines identity, search, and allowed profile evidence files
- code-owned policies decide which sections each crew receives
- Discovery replaces `profile.yaml.search` with `profile.yaml.search`
- Application keeps Profile Steward as the central brief builder
- renderers remove hardcoded personal content before any larger renderer
  migration
