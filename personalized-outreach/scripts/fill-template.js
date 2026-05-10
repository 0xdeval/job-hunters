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

function readProfileFiles(profileDir) {
  const profile = {
    generalInfo: {},
    summary: "",
    workExperience: [],
    projects: [],
  };

  // Parse general-info.md
  if (fs.existsSync(path.join(profileDir, "general-info.md"))) {
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

function boldMetrics(text) {
  return text.replace(/\*\*(.+?)\*\*/g, "\\textbf{$1}");
}

function formatWorkExperience(roles, customDescriptions = {}, customCompanyDescriptions = {}) {
  return roles
    .map((role) => {
      const achievements = customDescriptions[role.id] || role.achievements;
      const companyDescription =
        role.id in customCompanyDescriptions
          ? customCompanyDescriptions[role.id]
          : role.companyDescription;
      const bullets = achievements
        .map((desc) => `      \\resumeItem{${boldMetrics(escapeLatex(desc))}}`)
        .join("\n");

      return `    \\resumeSubheading
      {${escapeLatex(role.position)} | ${escapeLatex(role.company)}}{Remote}
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
      const descriptions = customDescriptions[proj.id] || [proj.description];
      const bullets = descriptions
        .map((desc) => `    \\resumeItem{${boldMetrics(escapeLatex(desc))}}`)
        .join("\n");

      return `\\resumeProject
{${escapeLatex(proj.name)}}{${escapeLatex(proj.period)}}
\\resumeItemListStart
${bullets}
\\resumeItemListEnd`;
    })
    .join("\n\n");
}

function fillTemplate(templatePath, tailoredDataPath, outputPath, profileDir) {
  // Read profile files
  const profile = readProfileFiles(profileDir);

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
    /==EMAIL==/g,
    profile.generalInfo.email || ""
  );

  template = template.replace(
    /==LINKEDIN URL==/g,
    profile.generalInfo.linkedinUrl || ""
  );

  template = template.replace(
    /==LINKEDIN NAME PROFILE==/g,
    escapeLatex(profile.generalInfo.linkedin || "")
  );

  template = template.replace(
    /==X URL==/g,
    profile.generalInfo.xUrl || ""
  );

  template = template.replace(
    /==X PROFILE NAME==/g,
    escapeLatex(profile.generalInfo.twitter ? profile.generalInfo.twitter.replace("@", "") : "")
  );

  template = template.replace(
    /==GITHUB URL==/g,
    profile.generalInfo.githubUrl || ""
  );

  template = template.replace(
    /==GITHUB NICKNAME==/g,
    escapeLatex(profile.generalInfo.github || "")
  );

  // Replace location
  template = template.replace(
    /==PLACE==/g,
    escapeLatex(profile.generalInfo.location || "")
  );

  // Replace summary
  template = template.replace(
    /==SHORT SUMMARY==/g,
    escapeLatex(tailoredData.summary || profile.summary)
  );

  // Replace experience
  const selectedRoles = profile.workExperience.filter((role) =>
    tailoredData.workExperienceIds?.includes(role.id)
  );
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
  const selectedProjects = profile.projects.filter((proj) =>
    tailoredData.projectIds?.includes(proj.id)
  );
  if (selectedProjects.length > 0) {
    const projectsSection = formatProjects(
      selectedProjects,
      tailoredData.projectDescriptions || {}
    );
    // Match the project placeholder block and replace it
    template = template.replace(
      /\\resumeProject\s+\{==PROJECT NAME==\}[\s\S]*?\\resumeItemListEnd/m,
      projectsSection
    );
  }

  // Replace skills
  template = template.replace(
    /==TOOLS AND STACK==/g,
    escapeLatex(tailoredData.skills || "")
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
      "Usage: node fill-template.js <template.tex> <tailored-data.json> <output.tex> <profile-dir>"
    );
    console.error("Example: node fill-template.js cv-template.md data.json output.tex profile/");
    process.exit(1);
  }

  const [templatePath, tailoredDataPath, outputPath, profileDir] = args;

  fillTemplate(templatePath, tailoredDataPath, outputPath, profileDir);
}

module.exports = { fillTemplate };
