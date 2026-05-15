const fs = require("fs");
const path = require("path");

/**
 * Fills a LaTeX CV template with profile data + LLM-tailored selections.
 *
 * Reads from profile/ folder and merges with LLM-generated tailored JSON.
 *
 * Profile files expected:
 * - profile/general-info.md
 * - profile/profile-summary.md
 * - profile/work-experience.md
 * - profile/personal-projects.md
 *
 * Tailored JSON structure:
 * {
 *   "summary": "Tailored summary for this role",
 *   "workExperienceIds": ["blockscout", "tiggy"],
 *   "workExperienceDescriptions": {
 *     "blockscout": ["Achievement 1", "Achievement 2"]
 *   },
 *   "projectIds": ["hush"],
 *   "projectDescriptions": {
 *     "hush": ["Custom description"]
 *   },
 *   "skills": "Tailored skills list"
 * }
 */

function escapeLatex(text) {
  if (!text) return "";
  return text
    .replace(/\\/g, "\\textbackslash{}")
    .replace(/[&%$#_{}~^]/g, (char) => {
      const escapeMap = {
        "&": "\\&",
        "%": "\\%",
        $: "\\$",
        "#": "\\#",
        _: "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
      };
      return escapeMap[char] || char;
    })
    .replace(/—/g, "---")   // em dash → LaTeX em dash
    .replace(/–/g, "--")    // en dash → LaTeX en dash
    .replace(/’/g, "'")     // right single quotation mark → apostrophe
    .replace(/‘/g, "`")     // left single quotation mark → backtick
    .replace(/“/g, "``")    // left double quotation mark
    .replace(/”/g, "''");   // right double quotation mark
}

function sanitizeGeneratedText(text) {
  if (!text) return "";
  return text
    .replace(/\[cite:\s*[^\]]+\]/gi, "")
    .replace(/\[cite_start\]/gi, "")
    .replace(/\[cite_end\]/gi, "")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/([.?!]){2,}/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function capitalizeSentenceStart(text) {
  if (!text) return "";
  const trimmed = text.trim();
  if (!trimmed) return "";
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
}

function readProfileFiles(profileDir, options = {}) {
  const includeGeneralInfo = options.includeGeneralInfo !== false;
  const profile = {
    generalInfo: {},
    summary: "",
    workExperience: [],
    projects: [],
    sections: {},
    source: "markdown",
  };

  // Parse general-info.md
  if (includeGeneralInfo && fs.existsSync(path.join(profileDir, "general-info.md"))) {
    const generalContent = fs.readFileSync(
      path.join(profileDir, "general-info.md"),
      "utf-8"
    );
    const nameMatch = generalContent.match(/\*\*Full Name:\*\*\s*(.+)/);
    const locationMatch = generalContent.match(/\*\*Location:\*\*\s*(.+)/);
    const emailMatch = generalContent.match(/\*\*Email:\*\*\s*(.+)/);
    const linkedinUrlMatch = generalContent.match(/\*\*LinkedIn:\*\*\s*(https?:\/\/[^\s]+)/);
    const linkedinMatch = generalContent.match(/\*\*LinkedIn:\*\*\s*https?:\/\/[^\/]+\/in\/([^\/?]+)/);
    const xUrlMatch = generalContent.match(/\*\*X:\*\*\s*(https?:\/\/[^\s]+)/);
    const xMatch = generalContent.match(/\*\*X:\*\*\s*https?:\/\/twitter\.com\/([^\s\/]+)/);
    const githubUrlMatch = generalContent.match(/\*\*GitHub:\*\*\s*(https?:\/\/[^\s]+)/);
    const githubMatch = generalContent.match(/\*\*GitHub:\*\*\s*https?:\/\/github\.com\/([^\s\/]+)/);

    if (nameMatch) profile.generalInfo.name = nameMatch[1].trim();
    if (locationMatch) profile.generalInfo.location = locationMatch[1].trim();
    if (emailMatch) profile.generalInfo.email = emailMatch[1].trim();
    if (linkedinUrlMatch) profile.generalInfo.linkedinUrl = linkedinUrlMatch[1].trim();
    if (linkedinMatch) profile.generalInfo.linkedin = linkedinMatch[1].trim();
    if (xUrlMatch) profile.generalInfo.xUrl = xUrlMatch[1].trim();
    if (xMatch) profile.generalInfo.twitter = xMatch[1].trim();
    if (githubUrlMatch) profile.generalInfo.githubUrl = githubUrlMatch[1].trim();
    if (githubMatch) profile.generalInfo.github = githubMatch[1].trim();
  }

  // Parse profile-summary.md
  if (fs.existsSync(path.join(profileDir, "profile-summary.md"))) {
    const summaryContent = fs.readFileSync(
      path.join(profileDir, "profile-summary.md"),
      "utf-8"
    );
    // Extract first paragraph after the heading
    const match = summaryContent.match(/# Person Summary\s*\n\n(.+?)(?:\n\n|$)/s);
    if (match) {
      profile.summary = match[1].trim();
    }
  }

  // Parse work-experience.md
  if (fs.existsSync(path.join(profileDir, "work-experience.md"))) {
    const workContent = fs.readFileSync(
      path.join(profileDir, "work-experience.md"),
      "utf-8"
    );
    // Split by role (## Company — Title)
    const roleBlocks = workContent.split(/^##\s+/m).slice(1);

    roleBlocks.forEach((block) => {
      const lines = block.split("\n");
      const firstLine = lines[0].trim();
      const [company, position] = firstLine.split(" — ");

      const periodMatch = block.match(/\*\*Period:\*\*\s*(.+)/);
      const period = periodMatch ? periodMatch[1].trim() : "";

      // Extract achievements
      const achievements = [];
      const achievementLines = block.match(/^-\s+(.+)$/gm);
      if (achievementLines) {
        achievementLines.forEach((line) => {
          const achievement = line.replace(/^-\s+/, "").trim();
          achievements.push(achievement);
        });
      }

      // Find company description — paragraph between metadata and achievements
      const descriptionMatch = block.match(/\*\*Industry:\*\*[^\n]+\n\n([^#\n][^\n]+)/);
      const companyDescription = descriptionMatch ? descriptionMatch[1].trim() : "";

      // Create ID from company name (lowercase, hyphenated)
      const id = company
        ? company
            .toLowerCase()
            .replace(/\s+/g, "-")
            .replace(/[^\w-]/g, "")
        : "";

      profile.workExperience.push({
        id,
        company: company ? company.trim() : "",
        position: position ? position.trim() : "",
        period,
        companyDescription,
        achievements,
      });
    });
  }

  // Parse personal-projects.md
  if (fs.existsSync(path.join(profileDir, "personal-projects.md"))) {
    const projectsContent = fs.readFileSync(
      path.join(profileDir, "personal-projects.md"),
      "utf-8"
    );
    // Split by project (## Project Name)
    const projectBlocks = projectsContent.split(/^##\s+/m).slice(1);

    projectBlocks.forEach((block) => {
      const lines = block.split("\n");
      const projectName = lines[0].trim();

      const periodMatch = block.match(/\*\*Worked period:\*\*\s*(.+)/);
      const period = periodMatch ? periodMatch[1].trim() : "";

      const urlMatch = block.match(/\*\*URL:\*\*\s*(.+)/);
      const url = urlMatch ? urlMatch[1].trim() : "";

      const descMatch = block.match(/### Description\s*\n\n(.+?)(?:\n###|$)/s);
      const description = descMatch ? descMatch[1].trim() : "";

      const techMatch = block.match(/### Tech Stack\s*\n\n(.+?)(?:\n###|$)/s);
      const techStack = techMatch ? techMatch[1].trim() : "";

      // Create ID from project name
      const id = projectName
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^\w-]/g, "");

      profile.projects.push({
        id,
        name: projectName,
        period,
        url,
        description,
        techStack,
      });
    });
  }

  return profile;
}

function loadNormalizedProfile(normalizedProfilePath) {
  if (!normalizedProfilePath) return null;
  if (!fs.existsSync(normalizedProfilePath)) return null;
  return JSON.parse(fs.readFileSync(normalizedProfilePath, "utf-8"));
}

function normalizeProfile(profileDir, normalizedProfilePath) {
  const normalized = loadNormalizedProfile(normalizedProfilePath);
  const profile = readProfileFiles(profileDir, { includeGeneralInfo: !normalized });
  if (!normalized) return profile;

  const identity = normalized.identity || {};
  profile.source = "normalized";
  profile.generalInfo = {
    name: identity.fullName || identity.name || "",
    email: identity.email || "",
    location: identity.location || identity.locationBase || "",
    contactLinks: Array.isArray(identity.links)
      ? identity.links.filter((link) => link && link.showOnCv === true)
      : [],
  };
  profile.sections = normalized.sections || {};
  if (Array.isArray(normalized.workExperience)) {
    profile.workExperience = normalized.workExperience;
  }
  if (Array.isArray(normalized.projects)) {
    profile.projects = normalized.projects;
  }
  if (typeof normalized.summary === "string" && normalized.summary.trim()) {
    profile.summary = normalized.summary.trim();
  }

  return profile;
}

function boldMetrics(text) {
  return text.replace(/\*\*(.+?)\*\*/g, "\\textbf{$1}");
}

function slugifyId(value) {
  return (value || "")
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]/g, "");
}

function dedupeStrings(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const normalized = (item || "").trim().toLowerCase();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(sanitizeGeneratedText(item.trim()));
  }
  return result;
}

function formatNormalizedContactLine(identity) {
  const parts = [];
  if (identity.email) {
    parts.push(
      `\\href{mailto:${identity.email}}{Email: \\underline{${escapeLatex(identity.email)}}}`
    );
  }

  (identity.contactLinks || []).forEach((link) => {
    if (!link.url) return;
    const label = link.label || link.key || "Link";
    const display = link.display || link.url;
    parts.push(
      `\\href{${link.url}}{${escapeLatex(label)}: \\underline{${escapeLatex(display)}}}`
    );
  });

  return parts.join(" $|$ ");
}

function formatLegacyContactLine(identity) {
  const parts = [];
  if (identity.email) {
    parts.push(
      `\\href{mailto:${identity.email}}{Email: \\underline{${escapeLatex(identity.email)}}}`
    );
  }
  if (identity.linkedinUrl || identity.linkedin) {
    parts.push(
      `\\href{${identity.linkedinUrl || ""}}{LinkedIn: \\underline{${escapeLatex(identity.linkedin || "")}}}`
    );
  }
  if (identity.xUrl || identity.twitter) {
    const display = identity.twitter ? identity.twitter.replace("@", "") : "";
    parts.push(
      `\\href{${identity.xUrl || ""}}{X: \\underline{@${escapeLatex(display)}}}`
    );
  }
  if (identity.githubUrl || identity.github) {
    parts.push(
      `\\href{${identity.githubUrl || ""}}{GitHub: \\underline{${escapeLatex(identity.github || "")}}}`
    );
  }
  return parts.join(" $|$ ");
}

function markdownSectionToLatex(title, content) {
  const lines = String(content || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith("#"));

  const items = lines
    .map((line) => line.replace(/^[-*]\s+/, ""))
    .filter(Boolean)
    .map((line) => `\\resumeItem{${boldMetrics(escapeLatex(line))}}`);

  if (items.length === 0) return "";

  return `\\section{${escapeLatex(title)}}\\sectionRule
\\resumeItemListStart
${items.join("\n")}
\\resumeItemListEnd`;
}

function resolveEntitiesByIds(entities, requestedIds = []) {
  if (!Array.isArray(requestedIds) || requestedIds.length === 0) return [];

  const byId = new Map(entities.map((entity) => [entity.id, entity]));
  const entitiesBySlug = new Map(
    entities.map((entity) => [slugifyId(entity.id), entity])
  );

  const resolved = [];
  const used = new Set();

  requestedIds.forEach((rawId) => {
    const direct = byId.get(rawId);
    if (direct && !used.has(direct.id)) {
      resolved.push(direct);
      used.add(direct.id);
      return;
    }

    const normalized = slugifyId(rawId);
    const normalizedMatch = entitiesBySlug.get(normalized);
    if (normalizedMatch && !used.has(normalizedMatch.id)) {
      resolved.push(normalizedMatch);
      used.add(normalizedMatch.id);
      return;
    }

    const fuzzy = entities.find((entity) => {
      if (used.has(entity.id)) return false;
      const entitySlug = slugifyId(entity.id);
      return (
        entitySlug.includes(normalized) ||
        normalized.includes(entitySlug)
      );
    });
    if (fuzzy) {
      resolved.push(fuzzy);
      used.add(fuzzy.id);
    }
  });

  return resolved;
}

function mergeRoleAchievements(role, customDescriptions = {}, minBullets = 4, maxBullets = 5) {
  const tailored = customDescriptions[role.id] || [];
  const merged = dedupeStrings([...(tailored || []), ...(role.achievements || [])]);

  if (merged.length === 0) return [];
  return merged.slice(0, Math.max(minBullets, Math.min(maxBullets, merged.length)));
}

const MONTH_TO_INDEX = {
  january: 1,
  february: 2,
  march: 3,
  april: 4,
  may: 5,
  june: 6,
  july: 7,
  august: 8,
  september: 9,
  october: 10,
  november: 11,
  december: 12,
};

function parsePeriodStart(period) {
  if (!period) return Number.MAX_SAFE_INTEGER;
  const normalized = period
    .replace(/–/g, "-")
    .replace(/—/g, "-")
    .toLowerCase();
  const [startPart] = normalized.split("-").map((part) => part.trim());
  const match = startPart.match(
    /(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})/
  );
  if (!match) return Number.MAX_SAFE_INTEGER;
  const monthIndex = MONTH_TO_INDEX[match[1]] || 12;
  const year = Number(match[2]);
  return year * 12 + monthIndex;
}

function parsePeriodEnd(period) {
  if (!period) return Number.MAX_SAFE_INTEGER;
  const normalized = period
    .replace(/–/g, "-")
    .replace(/—/g, "-")
    .toLowerCase();
  const parts = normalized.split("-").map((part) => part.trim()).filter(Boolean);
  const endPart = parts.length > 1 ? parts[parts.length - 1] : parts[0];

  if (endPart.includes("present") || endPart.includes("now")) {
    return Number.MAX_SAFE_INTEGER;
  }

  const match = endPart.match(
    /(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})/
  );
  if (!match) return parsePeriodStart(period);
  const monthIndex = MONTH_TO_INDEX[match[1]] || 12;
  const year = Number(match[2]);
  return year * 12 + monthIndex;
}

function sortRolesChronologically(roles) {
  // Deterministic resume order:
  // 1) by end date (newest -> oldest, "Present/Now" first)
  // 2) by start date (newest -> oldest)
  // 3) by company name
  return [...roles].sort((a, b) => {
    const endDiff = parsePeriodEnd(b.period) - parsePeriodEnd(a.period);
    if (endDiff !== 0) return endDiff;
    const startDiff = parsePeriodStart(b.period) - parsePeriodStart(a.period);
    if (startDiff !== 0) return startDiff;
    return a.company.localeCompare(b.company);
  });
}

function formatSkills(skillsInput) {
  const skillItems = Array.isArray(skillsInput)
    ? skillsInput
    : String(skillsInput || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

  const cleanedSkills = dedupeStrings(skillItems).map((skill) =>
    sanitizeGeneratedText(skill)
  );

  const categoryRules = [
    {
      label: "Product",
      keywords: [
        "product strategy",
        "roadmap",
        "launch",
        "go-to-market",
        "gtm",
        "monetization",
        "discovery",
        "workflow design",
      ],
    },
    {
      label: "Domain",
      keywords: [
        "digital asset",
        "web3",
        "defi",
        "payments",
        "privacy",
        "compliance",
        "account abstraction",
        "cross-chain",
        "blockchain",
      ],
    },
    {
      label: "Technical",
      keywords: [
        "api",
        "sdk",
        "sql",
        "data",
        "analytics",
        "infrastructure",
        "mcp",
      ],
    },
    {
      label: "Leadership",
      keywords: [
        "cross-functional",
        "leadership",
        "stakeholder",
        "partnership",
        "partner engagement",
      ],
    },
  ];

  const grouped = new Map(categoryRules.map((rule) => [rule.label, []]));
  const uncategorized = [];

  cleanedSkills.forEach((skill) => {
    const normalized = skill.toLowerCase();
    const matched = categoryRules.find((rule) =>
      rule.keywords.some((keyword) => normalized.includes(keyword))
    );
    if (matched) {
      grouped.get(matched.label).push(skill);
    } else {
      uncategorized.push(skill);
    }
  });

  if (uncategorized.length) {
    grouped.set("Additional", uncategorized);
  }

  const orderedLabels = ["Product", "Domain", "Technical", "Leadership", "Additional"];
  const lines = orderedLabels
    .filter((label) => grouped.has(label) && grouped.get(label).length > 0)
    .map((label) => {
      const values = dedupeStrings(grouped.get(label));
      return `\\resumeItem{\\textbf{${label}:} ${escapeLatex(values.join(", "))}}`;
    });

  return lines.length > 0 ? lines.join("\n") : "\\resumeItem{}";
}

function formatWorkExperience(roles, customDescriptions = {}, customCompanyDescriptions = {}) {
  return roles
    .map((role) => {
      const achievements = mergeRoleAchievements(role, customDescriptions, 4, 5);
      const companyDescription =
        role.id in customCompanyDescriptions
          ? customCompanyDescriptions[role.id]
          : role.companyDescription;
      const bullets = achievements
        .map((desc) =>
          `      \\resumeItem{${boldMetrics(escapeLatex(capitalizeSentenceStart(desc)))}}`
        )
        .join("\n");

      return `    \\resumeSubheading
      {${escapeLatex(role.position)} | ${escapeLatex(role.company)}}{${escapeLatex(role.location || "")}}
      {${escapeLatex(companyDescription)}}{${escapeLatex(role.period)}}
      \\resumeItemListStart
${bullets}
      \\resumeItemListEnd`;
    })
    .join("\n\n");
}

function formatProjects(projects, customDescriptions = {}) {
  return projects
    .map((proj) => {
      const descriptions = dedupeStrings([
        ...(customDescriptions[proj.id] || []),
        proj.description,
      ]).slice(0, 2);
      const bullets = descriptions
        .map((desc) =>
          `    \\resumeItem{${boldMetrics(escapeLatex(capitalizeSentenceStart(desc)))}}`
        )
        .join("\n");

      return `\\resumeProject
{${escapeLatex(proj.name)}}{${escapeLatex(proj.period)}}
\\resumeItemListStart
${bullets}
\\resumeItemListEnd`;
    })
    .join("\n\n");
}

function fillTemplate(templatePath, tailoredDataPath, outputPath, profileDir, normalizedProfilePath) {
  const profile = normalizeProfile(profileDir, normalizedProfilePath);

  // Read tailored data from LLM
  const tailoredData = JSON.parse(fs.readFileSync(tailoredDataPath, "utf-8"));

  // Read template
  let template = fs.readFileSync(templatePath, "utf-8");

  // Replace contact information using new placeholders
  template = template.replace(
    /==PROFILE NAME==/g,
    escapeLatex(profile.generalInfo.name || "")
  );
  template = template.replace(
    /==CONTACT_LINE==/g,
    profile.source === "normalized"
      ? formatNormalizedContactLine(profile.generalInfo)
      : formatLegacyContactLine(profile.generalInfo)
  );

  // Replace location
  template = template.replace(
    /==PLACE==/g,
    escapeLatex(profile.generalInfo.location || "")
  );

  // Replace summary
  template = template.replace(
    /==SHORT SUMMARY==/g,
    boldMetrics(
      escapeLatex(
        capitalizeSentenceStart(
          sanitizeGeneratedText(tailoredData.summary || profile.summary)
        )
      )
    )
  );

  // Replace experience
  let selectedRoles = resolveEntitiesByIds(
    profile.workExperience,
    tailoredData.workExperienceIds
  );
  if (selectedRoles.length < 4) {
    const selectedIds = new Set(selectedRoles.map((role) => role.id));
    const fallbackRoles = profile.workExperience.filter((role) => !selectedIds.has(role.id));
    selectedRoles = [...selectedRoles, ...fallbackRoles].slice(0, 4);
  }
  selectedRoles = sortRolesChronologically(selectedRoles);
  if (selectedRoles.length > 0) {
    const experienceSection = formatWorkExperience(
      selectedRoles,
      tailoredData.workExperienceDescriptions || {},
      tailoredData.workExperienceCompanyDescriptions || {}
    );
    // Match the placeholder block and replace it
    template = template.replace(
      /\\resumeSubheading\s*\n\{==POSITION TITLE==[^}]*\}[\s\S]*?\\resumeItemListEnd/m,
      experienceSection
    );
  }

  // Replace projects
  let selectedProjects = resolveEntitiesByIds(profile.projects, tailoredData.projectIds);
  if (selectedProjects.length === 0) {
    selectedProjects = profile.projects.slice(0, 2);
  }
  const projectsSection = formatProjects(
    selectedProjects,
    tailoredData.projectDescriptions || {}
  );
  // Match the project placeholder block and replace it
  template = template.replace(
    /\\resumeProject\s+\{==PROJECT NAME==\}[\s\S]*?\\resumeItemListEnd/m,
    projectsSection
  );

  // Replace skills
  template = template.replace(
    /==TOOLS AND STACK==/g,
    formatSkills(tailoredData.skills || "")
  );

  template = template.replace(
    /==PUBLIC_SPEAKING_SECTION==/g,
    markdownSectionToLatex("Public speaking", profile.sections.public_speaking || "")
  );
  template = template.replace(
    /==EDUCATION_SECTION==/g,
    markdownSectionToLatex("Education", profile.sections.education || "")
  );

  // Write output
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, template, "utf-8");

  console.log(`✓ CV filled and saved to: ${outputPath}`);
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 4) {
    console.error(
      "Usage: node fill-template.js <template.tex> <tailored-data.json> <output.tex> <profile-dir> [normalized-profile.json]"
    );
    console.error("Example: node fill-template.js cv-template.md data.json output.tex profile/ normalized-profile.json");
    process.exit(1);
  }

  const [templatePath, tailoredDataPath, outputPath, profileDir, normalizedProfilePath] = args;

  fillTemplate(templatePath, tailoredDataPath, outputPath, profileDir, normalizedProfilePath);
}

module.exports = { fillTemplate };
