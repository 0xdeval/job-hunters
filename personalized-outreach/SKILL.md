---
name: personalized-outreach
description: CV writing, LinkedIn outreach, and career application assistant. Use this skill whenever the user wants to generate a tailored CV, create LinkedIn outreach messages, write a cover letter, prepare job application materials, or tailor their professional profile to a specific company or role. Trigger on any mention of CV, resume, job application, LinkedIn message, cover letter, or outreach. Even vague requests like "help me apply to this company" should trigger this skill.
---

# Personalized Outreach Agent

A skill for generating tailored CVs in LaTeX (Overleaf-ready), LinkedIn outreach messages, and cover letters — personalized to a specific company and/or job description.

Tone throughout: **professional but casual** — confident, human, never robotic or stiff. Think "smart colleague who knows how to present you well," not "corporate HR template."

---

## Style Rules (CRITICAL — Apply to ALL Outputs)

**Capitalization:**

- ❌ NO PascalCase in sentences (e.g., "Private Finance", "Cross-Channel Messaging")
- ✅ ONLY capitalize first letter of sentences: "private finance", "cross-channel messaging"
- ✅ Proper nouns stay capitalized: "Blockscout", "Aave", "DeFi", company names

**Punctuation:**

- ❌ NO dots at end of paragraphs unless it ends a sentence
- ✅ Dots ONLY at end of sentences
- ✅ Bullet points: period if complete sentence; no period if fragment

**Example (WRONG):** "Led Cross-Chain Infrastructure Project. Increased User Adoption By 300%."

**Example (CORRECT):** "Led cross-chain infrastructure project, increasing user adoption by 300%."

---

## Data Files

These files live in the user's working directory and contain the real profile data:

| File                            | Contents                                                        |
| ------------------------------- | --------------------------------------------------------------- |
| `profile/profile-summary.md`    | Compact index of core facts and achievements — **loaded first** |
| `profile/work-experience.md`    | Detailed employment history                                     |
| `profile/personal-projects.md`  | Side projects and personal work                                 |
| `profile/general-info.md`       | Education, certifications, location, links, languages           |
| `profile/public-performance.md` | Conference talks, publications, community involvement           |

These files live inside the skill directory and set the quality bar:

| File                                                                  | Contents                                                         |
| --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `.claude/skills/personalized-outreach/best-practices/cv.md`           | Reference CV — the gold standard for format, density, and tone  |
| `.claude/skills/personalized-outreach/best-practices/cover-letter.md` | Reference cover letter — the gold standard for style and length |
| `.claude/skills/personalized-outreach/templates/cover-letter.md`      | LaTeX template with `==INTRO==`, `==MAIN BODY==`, `==CONCLUSION==` placeholders |

### File Loading Strategy (Token Optimization)

1. **Start with `profile-summary.md`** — embedded in CLAUDE.md, so do NOT re-read it unless a refresh is requested.
2. **Load detailed files only when needed:**
   - Summary doesn't have enough evidence to tailor accurately
   - User requests deeper tailoring
   - User asks to refresh/reload context
3. Reuse already-read file context within the same session.
4. **Detailed files are the fact validation layer.** If there's any mismatch between summary and detailed files, the detailed files win.
5. **Always read best-practices files before generating the corresponding output** — read `best-practices/cv.md` before generating a CV, `best-practices/cover-letter.md` + `templates/cover-letter.md` before generating a cover letter. These set the target quality bar.

---

## Step 1: Intake Flow

Before generating anything, collect required context in this exact sequence:

### 1a. Check for company information

If company info is missing, ask:

> "Please share the company info first (what the company does, values, product, culture, or a company URL)."

**Stop here** until company info is provided. Never fabricate company information.

### 1b. Ask for optional vacancy details

Once company info is available:

> "Optional: share the job description or role details you want me to tailor for. If you skip it, I'll generate a company-tailored CV."

### 1c. Ask what outputs are needed ← NEW REQUIRED STEP

Before proceeding, ask directly:

> "Should I also generate a **LinkedIn outreach message** and/or a **cover letter** alongside the CV? Let me know which ones you want."

Wait for explicit confirmation before generating any output. Do not assume. Do not generate extras the user didn't ask for.

---

## Step 2: Generate Outputs

Generate only what the user confirmed in Step 1c. Order: CV → LinkedIn message → Cover letter.

### CV Generation Flow (Automated with Scripts)

The CV is generated in three steps:

1. **Generate structured CV data** (JSON) tailored to company/role
2. **Fill LaTeX template** using `scripts/fill-template.ts`

This approach saves tokens by avoiding template-filling rewrites.

---

## Task A: Tailored CV (Automated Template Filling)

### Step 0: Load Quality Reference

Before generating anything, read `.claude/skills/personalized-outreach/best-practices/cv.md`. This is a real finished CV — study its bullet density, phrasing style, metrics placement, and overall feel. Your output should match this bar.

### Step 1: Generate Tailored Data JSON

Analyze the company + vacancy and generate JSON selecting which profile entries to highlight + how to tailor them. The script will read real profile data and merge it with these tailored selections.

**REQUIRED: Include at least 4 professional work experiences** (from profile/work-experience.md)

Generate JSON with this exact structure:

```json
{
  "summary": "Tailored summary (max 430 chars) optimized for this vacancy and company",
  "workExperienceIds": ["blockscout", "saola--mined", "tiggy", "prisma-labs-inc"],
  "workExperienceDescriptions": {
    "blockscout": [
      "Tailored achievement 1 optimized for this vacancy",
      "Tailored achievement 2",
      "Tailored achievement 3",
      "Tailored achievement 4"
    ],
    "saola--mined": ["Tailored achievement 1", "Tailored achievement 2"],
    "tiggy": [
      "Tailored achievement 1",
      "Tailored achievement 2",
      "Tailored achievement 3"
    ],
    "prisma-labs-inc": [
      "Tailored achievement 1",
      "Tailored achievement 2",
      "Tailored achievement 3"
    ]
  },
  "projectIds": ["puppeteer---ai-avatars-automation-framework", "mycelium-sdk---b2b-finance-crypto-sdk"],
  "projectDescriptions": {
    "puppeteer---ai-avatars-automation-framework": ["Tailored project description optimized for this role"],
    "mycelium-sdk---b2b-finance-crypto-sdk": ["Tailored project description optimized for this role"]
  },
  "skills": "Tailored skill list optimized for the vacancy"
}
```

**How IDs are generated from profile files:** The script derives IDs from the company name using: lowercase → spaces to hyphens → remove non-word characters. So "Saola & Mine'd" → `saola--mined`, "Prisma Labs, Inc." → `prisma-labs-inc`, "Wildberries / EPAM / Ozon" → `wildberries--epam--ozon`. Use these exact IDs in the JSON.

**Company descriptions** are auto-parsed from `work-experience.md` — the first paragraph after the `**Industry:**` line in each role block. The CV template renders them as the subtitle under each job heading (`{Position | Company} → {Company description}`). You don't need to provide them in the JSON unless you want to override what's in the profile (e.g., to shorten a long description for space).

If needed, override with the optional field:
```json
"workExperienceCompanyDescriptions": {
  "blockscout": "Custom short description override"
}
```

**CRITICAL REQUIREMENTS:**

- **At least 4 work experiences** must be included (from available roles in profile)
- Each experience must have **tailored descriptions** optimized for the company + vacancy
- Descriptions must emphasize **relevant metrics and achievements** that match the job requirements
- Never omit experiences with strong metrics for the sake of brevity
- Keep the experience description useful for a talent team, but don't make to short or to much long

````

### Step 2: Run fill-template.js Script

Save the tailored JSON to `.tmp/tailored-data.json` (not the project root — it's gitignored there). Then run:

```bash
mkdir -p .tmp && node .claude/skills/personalized-outreach/scripts/fill-template.js \
  .claude/skills/personalized-outreach/templates/cv-template.md \
  .tmp/tailored-data.json \
  output/cv-{company}.tex \
  profile/
```

This script:

- Reads real profile data from `profile/` folder (work-experience.md, personal-projects.md, general-info.md)
- Reads your tailored JSON selections
- Merges profile data + tailored achievements
- Replaces all placeholders with content
- Escapes special LaTeX characters automatically
- Saves filled `.tex` file

**Result:** Filled LaTeX file ready for compilation

**Important:** The final file should be fully ready for the compilations and shouldn't contain any issues. Make sure the latex file will be compiled without critical issue

### Content Rules — CRITICAL

**Metrics-first philosophy:** Metrics are MORE important than matching JD keywords. Never abstract experience to match job description phrasing if it means losing the actual achievements.

**Never invent facts.** Every achievement, metric, or skill must come from profile files.

**ALWAYS include metrics.** If the profile includes measurable outcomes (e.g., "increased TVL by 300%", "reduced churn by 15%"), MUST include in tailored descriptions. Never drop metrics for brevity.

**Tailor through selection and emphasis, NOT rewriting:**

- Select the 4+ most relevant roles from available work experience
- Order achievements with most relevant FIRST for this specific vacancy
- LEAD WITH METRICS: "Increased user retention by 25%" not "Collaborated on retention initiatives"
- Keep actual achievement phrasing from profile — don't abstract it
- Match specific JD requirements while preserving real numbers and outcomes

**CRITICAL: Never replace real metrics with JD keywords.**

- ❌ WRONG: Replace "increased TVL by 350%" with "drove user adoption"
- ✅ RIGHT: Keep "increased TVL by 350% and user base by 100%" and explain how it's relevant to this vacancy

**No vacancy provided?** Generate general CV highlighting profile alignment with company mission/industry. Still include 4+ roles and prioritize ones with strong metrics.

---

### Anti-AI Slop Filter — MANDATORY

After drafting every description, scan it for AI slop and rewrite any sentence that contains it. AI slop in CVs is hollow fluency: language that sounds professional but conveys nothing a real person couldn't fabricate in two seconds. It destroys credibility — recruiters and hiring managers recognize it immediately.

**Banned words and phrases — delete or replace on sight:**

| Slop | What to use instead |
|---|---|
| spearheaded, orchestrated, championed | led, built, launched, ran, shipped |
| leveraged | used |
| streamlined, optimized processes | cut X from Y to Z, reduced by N% |
| drove value, created synergies | concrete outcome with a number |
| transformative, innovative, cutting-edge | describe the actual thing |
| robust, seamless, scalable | describe behavior, not adjectives |
| best-in-class, world-class | specific metric or comparison |
| stakeholder alignment, cross-functional | name the actual teams |
| played a key role in, contributed to | state what you specifically did |
| in a fast-paced environment | leave out — means nothing |
| delve, realm, multifaceted, nuanced, pivotal | plain language |
| responsible for | did, built, owned |
| ensured, facilitated, liaised | specific verb describing the action |

**Pattern-level slop to cut:**

- Buzzword chains: "leveraged cutting-edge AI solutions to drive scalable outcomes" → "built an AI pipeline that cut experiment cycles by 7x"
- Abstract impact: "drove user growth" → "grew MAU by 300%"
- Passive attribution: "was part of a team that launched" → "launched" (if you did it)
- Vague time words: "rapidly", "significantly", "dramatically" → use actual numbers or remove

**The anti-slop test:** Read each bullet point and ask: could someone copy this sentence and paste it onto a CV for a completely different job at a different company and have it still make sense? If yes, it's slop. Make it specific enough that it only makes sense for this person.

**Self-check step:** After generating all descriptions in the JSON, re-read each bullet. Flag any that contain a banned word or could pass the anti-slop test, then rewrite them before finalising.

---

### Bold Key Metrics (REQUIRED)

Wrap the most important metrics and outcomes in `**double asterisks**` inside your JSON strings. The script converts these to `\textbf{}` in the final LaTeX, making them bold in the PDF.

**What to bold:** numbers, percentages, multipliers, and key proper nouns that a recruiter scanning the CV should notice first — the proof that something worked.

**Rule:** Bold 1–2 things per bullet maximum. The goal is to guide the eye, not highlight everything.

**Example:**
```json
"Grew MAU by **300%** via retail onboarding framework, zero traffic drop-off"
"Cut experiment cycles by **7x** using AI-powered hypothesis testing"
"Coordinated **20+** strategic partners across Optimism and Ink ecosystems"
```

Do NOT bold generic verbs, role titles, or company names. Only bold the metric or outcome itself.

---

### Special Notes

- **Minimum 4 professional experiences:** Always select at least 4 roles from work-experience.md
- **LaTeX characters:** Automatically escaped by fill-template.js (% → \%, $ → \$, etc.)
- **Target length:** Compiled PDF will be 1–2 pages
- **No manual assembly:** Script handles all template filling

---

## Task B: LinkedIn Outreach Message

Only generate if the user confirmed this in Step 1c. Also ask for a which limits you need to generate a outreach message for LinkedIn: free or premium

### Character Limits (Hard Limits)

| Account type | Limit          |
| ------------ | -------------- |
| Free         | 200 characters |
| Premium      | 300 characters |

Generate only the **Long version** (Premium, under 300 characters). Count exactly — 1 character over means the message won't send.

### Content Rules

- **Always open with a greeting**, e.g. "Hi, I'm [first name], nice to meet you"
- **Reference something specific** about the company — a product, value, mission element, or recent achievement from the provided company info
- **Mention the role or team** naturally if a vacancy was provided
- **Base the message on overall experience** — show broad professional background
- **End with a soft call to action**, e.g. "Would love to connect and chat" or "Happy to share more"
- **Do NOT include:** full name (LinkedIn shows it automatically), links, email, phone
- **Do NOT use:** "I came across your profile", "I hope this message finds you well", or any other generic openers
- **Style: Apply capitalization rules** — no PascalCase in sentences, only first letter capitalized. "private finance" not "Private Finance"
- Not a sales pitch. Human reaching out to human. Warm, genuine, direct.

### Output Format

```
===MSG_START===
### Long version (premium LinkedIn — under 300 characters)
[message here]
Character count: [exact count]
===MSG_END===
```

### Save Output

Save to: `output/outreach/{company}.md`

---

## Task C: Cover Letter

Only generate if the user confirmed this in Step 1c.

### Step 0: Load References

Read both files before writing a single word:

1. `.claude/skills/personalized-outreach/best-practices/cover-letter.md` — a finished cover letter at the target quality bar. Study its tone, paragraph structure, opening hook, how it uses metrics, and how it closes. Match this energy.
2. `.claude/skills/personalized-outreach/templates/cover-letter.md` — the LaTeX template you will fill. It has three placeholders: `==INTRO==`, `==MAIN BODY==`, and `==CONCLUSION==`.

### Step 1: Draft the Three Sections

Fill each placeholder with content tailored to the company and vacancy:

**`==INTRO==`** — one paragraph, ~60–80 words. Open with a hook tied to something specific in the job description or company mission — not a generic "I want to apply" opener. The best-practices example shows what a strong hook looks like: it quotes or mirrors the company's own language, then bridges directly to a matching part of your background.

**`==MAIN BODY==`** — one or two paragraphs, ~150–200 words total. Pick 2–3 experiences or outcomes from the profile files that most directly address what this company cares about. Lead with the metric or outcome, not the task. Keep the energy of the best-practices example — direct, confident, specific. Never abstract an achievement into a keyword.

**`==CONCLUSION==`** — one short paragraph, ~40–60 words. Soft call to action. Genuine interest without being sycophantic. Offer something concrete (decision memos, prototypes, experiment logs) if it fits.

### Content Rules

- **Never invent facts.** Every claim must trace back to the profile files.
- **Metrics come first.** If the profile has a number, use it.
- **Apply capitalization rules** — no PascalCase in sentences. Dots only at end of sentences.
- **Total length:** ~300–400 words across all three sections. Tight and human, not a wall of text.
- **Tone:** professional but casual. Speak like a real person. No "I am writing to express my keen interest in…"
- **Apply the anti-slop filter** — same banned words as the CV section apply here too.

### Step 2: Fill the Template and Save

Take the template content from `templates/cover-letter.md`, replace `==INTRO==`, `==MAIN BODY==`, and `==CONCLUSION==` with your drafted content, and save the result as a `.tex` file.

Save to: `output/cover-letters/cover-letter-{company}.tex`

---

## Execution Order

1. Read `profile-summary.md` (already embedded — do NOT re-read)
2. Run intake flow: collect company info → optional vacancy → confirm which outputs are needed
3. If deeper evidence is needed, read relevant detailed data files
4. Analyze company information and vacancy (if provided)
5. Generate confirmed outputs in this order:
   - **CV:** Read `best-practices/cv.md` → Generate JSON → Run `fill-template.js` → Output filled `.tex` file
   - **LinkedIn message:** Generate directly as markdown
   - **Cover letter:** Read `best-practices/cover-letter.md` + `templates/cover-letter.md` → Draft three sections → Fill template → Output filled `.tex` file
6. Save all files to their respective output paths
7. Provide user with file paths to outputs

---

## Final Response

After all files are saved, reply with a single short confirmation only — something like:

> "Done. Files saved."

Do NOT summarize what was generated, list the files, explain what was tailored, or repeat content back. Just confirm it's done.

---

## Rules Summary

| Rule                          | Description                                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- |
| ❌ Never invent               | No experience, skills, metrics, or achievements not in data files                                             |
| ✅ Metrics-first, always      | Real metrics > JD keywords. Never abstract experience to match keywords if it loses the achievement           |
| ✅ Always include all roles   | Every employer from work-experience.md must appear — never omit entries. Order them based on the work periods |
| ✅ Focus on recent roles      | The main focus almost on the recent job from the list. Reorder the experience in side the job if necessary    |
| ✅ Always include metrics     | If the data has a number, use it. Lead with metrics, not abstract descriptions                                |
| ✅ Always tailor              | Never produce a generic one-size-fits-all output                                                              |
| ✅ No PascalCase in sentences | Only capitalize first letter of sentences. "private finance" not "Private Finance"                            |
| ✅ Dots only at sentence ends | No dots at end of paragraphs unless ending a sentence                                                         |
| ✅ Ask first                  | Confirm which outputs to generate before proceeding                                                           |
| ✅ Preserve LaTeX structure   | Only fill in content, never modify template formatting                                                        |
| ✅ Respect LinkedIn limits    | Count characters exactly, hard limits, no exceptions                                                          |
| ✅ Stay in character          | Professional but casual throughout, no corporate fluff                                                        |
