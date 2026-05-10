# Personalized Outreach Skill

Generate tailored CVs in LaTeX, LinkedIn outreach messages, and cover letters for specific companies and job roles.

## Setup

### Required Directories

Create the following directory structure in your project root:

```
profile/
├── profile-summary.md          # 1-2 paragraph career overview
├── work-experience.md          # Employment history with metrics
├── personal-projects.md        # Side projects and open-source work
├── general-info.md             # Education, location, email, links
└── public-performance.md       # (Optional) Talks, publications, community involvement

output/
├── cv/                         # Generated LaTeX CVs
├── cover-letters/              # Generated cover letters
└── outreach/                   # Generated LinkedIn messages
```

### Profile File Contents

**profile-summary.md**

- 1-2 paragraph overview of your career and key achievements

**work-experience.md**

- Company name, role title, employment dates
- Industry/context description
- Key achievements with metrics (% growth, revenue, MAU increase, TVL scaling, etc.)

**personal-projects.md**

- Project name and GitHub URL
- Description and tech stack
- Impact or outcomes
- Work dates

**general-info.md**

- Full name, location, email
- Education (degree, school, graduation year)
- Languages spoken
- Links (LinkedIn, GitHub, X, portfolio, etc.)

**public-performance.md** (optional)

- Conference talks and speaking engagements
- Publications or blog posts
- Community contributions

## How to Use

### Step 1: Invoke the Skill

```
/personalized-outreach
```

### Step 2: Provide Company Information

Share details about the company:

- What the company does
- Key products/services
- Company values or culture
- Company mission or focus areas
- URL (optional)

### Step 3: Share Role Details (Optional)

If you have a specific job posting:

- Job title
- Job description
- Key responsibilities
- Required experience

Skip if the role is open or general.

### Step 4: Confirm Output Types

Specify which materials you need:

- CV (always generated)
- Cover letter
- LinkedIn message (specify if free or premium account: free=200 chars, premium=300 chars)

### Step 5: Receive Tailored Materials

Files are generated and saved to:

- `output/cv/cv-{company}.tex`
- `output/cover-letters/cover-letter-{company}.md`
- `output/outreach/{company}.md`

### Step 6: [Optional] Convert to PDF

You can use [Overleaf](https://www.overleaf.com/) service to convert the generated `.tex` file to a PDF

## Output Details

### CV (cv-{company}.tex)

LaTeX file ready for PDF compilation via Overleaf or local compiler.

Includes:

- Tailored professional summary (optimized for company focus)
- 4+ work experiences with tailored achievements
- 2-3 personal projects (selected and tailored)
- Skills section (tailored to company needs)
- Education and certifications
- Contact information and links

### Cover Letter (cover-letter-{company}.md)

Markdown formatted letter, 300-400 words.

Structure:

- Opening: specific reference to company mission/products
- Body: 2-3 most relevant experiences with actual metrics
- Closing: soft call to action and genuine interest

### LinkedIn Outreach Message ({company}.md)

Short, compelling message for LinkedIn connection requests.

Details:

- Under 200 characters (free account) or 300 characters (premium)
- Specific company reference
- Relevant background mention
- Soft call to action
- Exact character count included

## Tone & Style

All outputs follow these principles:

- Professional but casual (human, confident, not corporate)
- Metrics-first (real numbers before keywords)
- No invented facts (everything from your profile files)
- No generic phrases ("I came across your profile", "I hope this message finds you well")
- Capitalization: only first letter of sentences, proper nouns stay capitalized

## Example Workflow

1. Create `profile/` directory with your background
2. Invoke `/personalized-outreach`
3. Provide company info:
   - "Gnosis - Web3 infrastructure, Safe ($100B+ AUM), CoW Protocol, Zodiac, Gnosis Chain"
4. Provide job info (optional):
   - "Product Manager role, no specific JD provided"
5. Confirm outputs:
   - "Generate CV and cover letter"
6. Receive:
   - `output/cv/cv-gnosis.tex` - Ready for Overleaf
   - `output/cover-letters/cover-letter-gnosis.md` - Tailored to Gnosis mission

All materials are company-specific, metric-driven, and based on your actual background.
