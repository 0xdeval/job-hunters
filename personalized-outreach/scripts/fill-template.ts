import * as fs from "fs";
import * as path from "path";

/**
 * Fills a LaTeX CV template with generated CV content.
 * Replaces placeholders (e.g., ==PLACEHOLDER==) with actual values.
 *
 * Input JSON structure:
 * {
 *   "name": "John Doe",
 *   "email": "john@example.com",
 *   "linkedin": "john-doe",
 *   "twitter": "@johndoe",
 *   "github": "johndoe",
 *   "location": "San Francisco, CA",
 *   "summary": "Short professional summary",
 *   "experience": [
 *     {
 *       "company": "Company Name",
 *       "location": "Remote",
 *       "position": "Position Title",
 *       "period": "2020 - 2023",
 *       "description": ["Bullet 1", "Bullet 2"]
 *     }
 *   ],
 *   "projects": [
 *     {
 *       "name": "Project Name",
 *       "period": "2023",
 *       "description": ["Bullet 1"]
 *     }
 *   ],
 *   "skills": "Skill 1, Skill 2, Skill 3"
 * }
 */

interface CVData {
  name: string;
  email: string;
  linkedin: string;
  twitter: string;
  github: string;
  location: string;
  summary: string;
  experience: Array<{
    company: string;
    location: string;
    position: string;
    period: string;
    description: string[];
  }>;
  projects: Array<{
    name: string;
    period: string;
    description: string[];
  }>;
  skills: string;
}

function escapeLatex(text: string): string {
  return text
    .replace(/\\/g, "\\textbackslash{}")
    .replace(/[&%$#_{}~^]/g, (char) => {
      const escapeMap: { [key: string]: string } = {
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
    });
}

function formatExperience(experience: CVData["experience"]): string {
  return experience
    .map((job) => {
      const bullets = job.description
        .map((desc) => `      \\resumeItem{${escapeLatex(desc)}}`)
        .join("\n");

      return `    \\resumeSubheading
      {${escapeLatex(job.company)}}{${escapeLatex(job.location)}}
      {${escapeLatex(job.position)}}{${escapeLatex(job.period)}}
      \\resumeItemListStart
${bullets}
      \\resumeItemListEnd`;
    })
    .join("\n\n");
}

function formatProjects(projects: CVData["projects"]): string {
  return projects
    .map((proj) => {
      const bullets = proj.description
        .map((desc) => `    \\resumeItem{${escapeLatex(desc)}}`)
        .join("\n");

      return `\\resumeProject
{${escapeLatex(proj.name)}}{${escapeLatex(proj.period)}}
\\resumeItemListStart
${bullets}
\\resumeItemListEnd`;
    })
    .join("\n\n");
}

export function fillTemplate(
  templatePath: string,
  cvData: CVData,
  outputPath: string
): void {
  let template = fs.readFileSync(templatePath, "utf-8");

  // Replace contact information
  template = template.replace(
    /\\textbf\{\\Huge \\scshape [^}]+\}/,
    `\\textbf{\\Huge \\scshape ${escapeLatex(cvData.name)}}`
  );

  template = template.replace(
    /\\href\{mailto:[^}]+\}\{Email: \\underline\{[^}]+\}\}/,
    `\\href{mailto:${cvData.email}}{Email: \\underline{${cvData.email}}}`
  );

  template = template.replace(
    /\\href\{https:\/\/www\.linkedin\.com\/in\/[^}]+\}\{LinkedIn: \\underline\{[^}]+\}\}/,
    `\\href{https://www.linkedin.com/in/${cvData.linkedin}/}{LinkedIn: \\underline{${cvData.linkedin}}}`
  );

  template = template.replace(
    /\\href\{https:\/\/twitter\.com\/[^}]+\}\{X: \\underline\{[^}]+\}\}/,
    `\\href{https://twitter.com/${cvData.twitter.replace("@", "")}}{X: \\underline{${cvData.twitter}}}`
  );

  template = template.replace(
    /\\href\{https:\/\/github\.com\/[^}]+\}\{GitHub: \\underline\{[^}]+\}\}/,
    `\\href{https://github.com/${cvData.github}}{GitHub: \\underline{${cvData.github}}}`
  );

  // Replace location
  template = template.replace(/Portugal, Lisbon/, escapeLatex(cvData.location));

  // Replace summary
  template = template.replace(
    /==SHORT SUMMARY==/,
    escapeLatex(cvData.summary)
  );

  // Replace experience
  const experienceSection = formatExperience(cvData.experience);
  template = template.replace(
    /    \\resumeSubheading\s+\{==COMPANY NAME==\}.*?\\resumeItemListEnd/s,
    experienceSection
  );

  // Replace projects
  if (cvData.projects.length > 0) {
    const projectsSection = formatProjects(cvData.projects);
    template = template.replace(
      /\\resumeProject\s+\{==PERSONAL PROJECT NAME==\}.*?\\resumeItemListEnd/s,
      projectsSection
    );
  }

  // Replace skills
  template = template.replace(
    /==TOOLS AND STACK==/,
    escapeLatex(cvData.skills)
  );

  // Write to output
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, template, "utf-8");

  console.log(`✓ CV template filled and saved to: ${outputPath}`);
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 3) {
    console.error("Usage: npx ts-node fill-template.ts <template> <data.json> <output.tex>");
    process.exit(1);
  }

  const [templatePath, dataPath, outputPath] = args;
  const cvData = JSON.parse(fs.readFileSync(dataPath, "utf-8")) as CVData;

  fillTemplate(templatePath, cvData, outputPath);
}
