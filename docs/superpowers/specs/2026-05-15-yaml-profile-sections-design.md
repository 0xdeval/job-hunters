# YAML Profile Sections and Artifact Links Design

**Date:** 2026-05-15
**Status:** Pending written-spec review

## Objective

Migrate profile evidence from free-form Markdown section files to structured
YAML section files. The goal is tighter control over which facts can fill CVs,
cover letters, Q&A answers, and discovery scoring, while supporting proof links
that render cleanly in generated artifacts.

This design addresses:

- Issue #7: migrate profile section files from Markdown to YAML.
- Issue #8: support structured links in YAML-backed CV sections.

## Scope

In scope:

- Keep `knowledge/profile.yaml` as the profile index and control file.
- Keep separate profile section files under `knowledge/profile/`.
- Change active profile section files from `.md` to `.yaml`.
- Remove `profile-summary` as a maintained source-of-truth section.
- Remove `general-info` as a maintained source-of-truth section.
- Add typed schemas for work experience, projects, education, skills, public
  performance, and values/interests.
- Use structured links in section items.
- Render artifact links as underlined clickable labels in generated PDFs.
- Update examples, README, setup guide, and tests.

Out of scope:

- Markdown compatibility for profile sections. This project is currently
  single-user, so the implementation should move directly to YAML-only section
  files.
- A full CV renderer rewrite. The implementation may adapt the current Node
  renderer unless a smaller Python path is clearly safer during planning.
- Arbitrary user-defined section keys.

## Profile Index

`knowledge/profile.yaml` remains the control file for identity, job-search
criteria, and the allowlisted profile evidence files.

Example:

```yaml
profile_sections:
  work_experience: profile/work-experience.yaml
  projects: profile/personal-projects.yaml
  education: profile/education.yaml
  skills: profile/skills.yaml
  public_speaking: profile/public-performance.yaml
  values: profile/values-and-interests.yaml
```

`profile-summary.md` should not be migrated. CV summaries, cover-letter
positioning, Q&A introductions, and discovery scoring summaries should be
generated at runtime from structured profile facts.

`general-info.md` should not be migrated. CV header data, contact details,
cover-letter signature, and identity context should come from
`profile.yaml.identity`.

## Shared Rules

All section files are YAML mappings with one or more named top-level lists.

Supported cross-section rules:

- `show_on_cv` is optional and defaults to `true` where supported.
- `links` is optional.
- When `links` is present, each link requires:
  - `label`
  - `url`
- Link URLs must be `http://` or `https://`.
- Links are structured data, not Markdown inline links.
- In generated PDFs, visible link labels must be clickable and underlined.
- When multiple link labels are appended to one rendered item, separate them
  with `. `, for example `Hush. Growthcast`.
- Period values use `YYYY-MM`; end values may also be `present`.

## Work Experience Schema

File: `knowledge/profile/work-experience.yaml`

```yaml
roles:
  - id: blockscout
    company: Blockscout
    title: Senior Product Manager
    period:
      start: 2022-08
      end: 2026-04
    industry: Blockchain / DeFi Infrastructure
    company_summary: Leading open-source blockchain explorer and SaaS infrastructure platform
    show_on_cv: true

    achievements:
      - area: Payment product strategy
        text: Led the product vision for a privacy-focused payment solution, defining compliant payment mechanisms based on enterprise, retail, and regulatory feedback. Launched an experimentation framework and scaled assets under management by 350% YoY, doubled the user base, and increased transaction volume by 200% within the first few months.
        links:
          - label: Hush
            url: https://github.com/0xdeval/hush
```

Rules:

- `roles` is required.
- Each role requires `id`, `company`, `title`, `period.start`, `period.end`,
  and non-empty `achievements`.
- `industry` is optional.
- `company_summary` is optional.
- `show_on_cv` is optional and defaults to `true`.
- Each achievement requires `area` and `text`.
- Achievement `links` are optional.

Artifact usage:

- CV includes roles unless `show_on_cv: false`.
- CV renders role header from `company`, `title`, and formatted `period`.
- CV may render `company_summary` as role context.
- CV renders selected achievements as `area: text`.
- Achievement links append clickable underlined labels at the end of the bullet.
- Cover letters and Q&A can use all role facts as source evidence.
- Discovery scoring can use role titles, industries, summaries, and
  achievements.

## Projects Schema

File: `knowledge/profile/personal-projects.yaml`

```yaml
projects:
  - id: hush
    name: Hush
    title: Crypto privacy payment solution
    period:
      start: 2026-02
      end: 2026-03
    show_on_cv: true

    description: A privacy-focused DeFi integration for Aave that allows users to supply USDC as collateral, borrow WETH, and manage repayment/withdrawal flows privately, ensuring strategy identity remains confidential.

    links:
      - label: GitHub
        url: https://github.com/0xdeval/hush

    tech_stack:
      - DeFi Protocols
      - Aave
      - Privacy Infrastructure
      - Smart Contracts
```

Rules:

- `projects` is required.
- Each project requires `id`, `name`, and `description`.
- `title` is optional.
- `period` is optional; when present, period values follow shared period rules.
- `show_on_cv` is optional and defaults to `true`.
- `links` is optional but expected for proof-bearing projects.
- `tech_stack` is optional.

Artifact usage:

- CV includes projects unless `show_on_cv: false`.
- CV renders project links near the project name as underlined clickable labels.
- CV can render `title`, formatted `period`, `description`, and compact
  `tech_stack`.
- Cover letters and Q&A use projects as proof of domain and technical work.

## Education Schema

File: `knowledge/profile/education.yaml`

```yaml
education:
  - id: hse-applied-math
    institution: Higher School of Economics
    degree: Bachelor's degree
    field: Computational and Applied Mathematics
    period:
      start: 2016-09
      end: 2020-06
    grade: GPA 8/10
    show_on_cv: true

    links:
      - label: Program
        url: https://example.com/program
```

Rules:

- `education` is required.
- Each item requires `id`, `institution`, `degree`, and `field`.
- `period` is optional.
- `grade` is optional.
- `show_on_cv` is optional and defaults to `true`.
- `links` is optional.

Artifact usage:

- CV includes education items unless `show_on_cv: false`.
- CV renders degree, field, institution, optional formatted period, optional
  grade, and appended underlined link labels.
- Cover letters and Q&A use education facts when relevant.

## Skills Schema

File: `knowledge/profile/skills.yaml`

```yaml
skill_groups:
  - name: Product
    show_on_cv: true
    skills:
      - Product strategy
      - Product discovery
      - Roadmap prioritization
      - Growth product management

  - name: Web3 / FinTech
    show_on_cv: true
    skills:
      - Web3
      - DeFi
      - Stablecoin payments
      - Crypto payments
```

Rules:

- `skill_groups` is required.
- Each group requires `name` and a non-empty `skills` list.
- `show_on_cv` is optional and defaults to `true`.
- Per-skill links are not part of v1. Proof should live in work achievements,
  projects, public performance, or education.

Artifact usage:

- The LLM may choose the most relevant skills for a vacancy from visible skill
  groups.
- The renderer must not invent skills outside the YAML-backed skill pool.
- If the LLM does not provide a valid skill selection, the renderer may use a
  deterministic fallback from visible skill groups.
- Cover letters, Q&A, and discovery scoring can use all skill groups as source
  evidence unless a group has a later artifact-specific exclusion.

## Public Performance Schema

File: `knowledge/profile/public-performance.yaml`

```yaml
talks:
  - id: ethcc-building-trusted-web3-spaces
    conference: ETHCC
    title: Building trusted Web3 spaces
    show_on_cv: true
    links:
      - label: Event
        url: https://example.com/ethcc
      - label: Video
        url: https://example.com/video

publications:
  - id: defi-privacy-self-regulatory-compliance
    title: DeFi privacy and self-regulatory compliance white paper
    description: Authored a white paper analyzing the intersection of zero-knowledge privacy and regulation, proposing a framework of selective disclosure and AML screening to mitigate illicit use in protocols like zkBob and RAILGUN.
    show_on_cv: true
    links:
      - label: White paper
        url: https://example.com/white-paper
```

Rules:

- `talks` is optional.
- Each talk requires `id`, `conference`, and `title`.
- `publications` is optional.
- Each publication requires `id` and `title`.
- Publication `description` is optional and intentionally flexible
  human-readable text.
- At least one of `talks` or `publications` must be present when the section is
  referenced.
- `show_on_cv` is optional and defaults to `true`.
- `links` is optional.

Artifact usage:

- CV renders visible talks and publications.
- Talks render as `Conference: Title` with appended underlined link labels.
- Publications render from `title`, optional `description`, and appended
  underlined link labels.
- Cover letters and Q&A use talks/publications as credibility, writing,
  research, and public-proof evidence.

## Values And Interests Schema

File: `knowledge/profile/values-and-interests.yaml`

```yaml
values:
  - id: ownership
    title: High ownership
    description: I prefer roles where I can own ambiguous problems from discovery through launch.

interests:
  - id: privacy-preserving-products
    title: Privacy-preserving products
    description: Interested in products that make privacy usable without sacrificing compliance or user experience.
```

Rules:

- `values` is optional.
- `interests` is optional.
- At least one of `values` or `interests` must be present when the section is
  referenced.
- Each item requires `id`, `title`, and `description`.
- This section has no `show_on_cv` in v1 because it is not rendered in the CV.

Artifact usage:

- Cover letters use values and interests for tone, motivation, and
  why-this-company framing.
- Q&A uses values and interests for culture, motivation, leadership style, and
  interest questions.
- Discovery scoring and CV do not use this section in v1.

## Runtime Summaries

Stored profile summaries are removed. When a concise summary improves prompt
quality, it should be generated at runtime from structured YAML facts.

Examples:

- CV summary generated from identity, target roles, work achievements, projects,
  and skills.
- Cover-letter positioning summary generated from identity, values/interests,
  target roles, and selected proof points.
- Discovery candidate scoring summary generated from search criteria, work
  experience, projects, and skills.

Generated summaries are disposable prompt context, not source-of-truth profile
files.

## Validation

Validation should happen before crews or renderers run.

Required validation:

- `profile.yaml.profile_sections` points only to `.yaml` section files.
- Unknown profile section keys fail with `ProfileConfigError`.
- Missing referenced section files fail with clear `ProfileConfigError`
  messages.
- Each section validates its required top-level list and required item fields.
- Required string fields must be non-empty strings.
- Required lists must be non-empty lists.
- `show_on_cv`, when present, must be boolean.
- Period values must be `YYYY-MM`; `period.end` may be `present`.
- Links require `label` and `url`.
- Link URLs must start with `http://` or `https://`.

Example errors:

- `profile_sections.work_experience must point to a .yaml file`
- `profile_sections.education points to profile/education.yaml, but the file does not exist`
- `work_experience.roles[0].achievements[0].text is required`
- `projects.projects[1].links[0].url must be an http(s) URL`

## Documentation

Update `README.md`:

- Explain that profile evidence lives in YAML section files.
- Show the new `.yaml` `profile_sections` example.
- Remove active-format references to Markdown profile section files.
- Mention that generated PDF links render as underlined clickable labels.

Update `docs/setup-guide.md`:

- Document how to create and edit `knowledge/profile.yaml`.
- Document each section file and schema.
- Explain that `show_on_cv` defaults to `true`.
- Explain structured `links` and PDF rendering behavior.
- Remove `profile-summary.md` and `general-info.md` from the required setup
  path.

Update `examples/knowledge/`:

- Change example `profile.yaml` paths to `.yaml`.
- Add representative YAML section files.
- Remove `summary` and general-info-style sections from active examples.

## Testing Strategy

Tests should cover:

- Profile index parsing with `.yaml` profile section paths.
- Rejection of Markdown profile section paths.
- Rejection of unknown profile section keys.
- Rejection of missing referenced section files.
- Section schema parsing for work experience, projects, education, skills,
  public performance, and values/interests.
- Missing required field errors with actionable `ProfileConfigError` messages.
- Invalid period and invalid link validation.
- `show_on_cv` defaulting to `true`.
- Application context construction from structured YAML evidence.
- Discovery context construction from structured YAML evidence and generated
  runtime summary context when needed.
- CV renderer output with underlined clickable `\href` labels.
- Multiple rendered links separated by `. `.
- `show_on_cv: false` hiding CV items.
- No raw URL noise in visible PDF text.
- Regression coverage proving `profile-summary` and `general-info` are no
  longer required.

## Implementation Notes

The implementation should prefer typed internal structures over passing raw YAML
through the system. The current `profile_context.py` is the natural boundary for
loading, validating, and preparing profile context for crews and renderers.

The renderer-facing normalized profile JSON should contain structured sections,
not Markdown strings. Existing renderer logic can be adapted incrementally, but
the prompt and rendering layers should no longer parse profile Markdown as the
source of truth.

