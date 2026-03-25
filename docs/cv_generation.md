# CV Generation Guide

Generate ATS-optimized CVs in Markdown and PDF formats.

## Quick Start

Tell the agent in natural language:

```
> generate my CV
> generate a CV targeting Senior Python Developer roles
> create an ATS-optimized CV for Staff Engineer at a tech company
```

The agent will ask for confirmation before generating (HITL). Press Enter or `y` to proceed.

---

## Output Formats

FutureProof generates two formats:

| Format | Extension | Use Case |
|--------|-----------|----------|
| **Markdown** | `.md` | Editable, version control, plain text |
| **PDF** | `.pdf` | Submitting to employers, printing |

### File Locations

Generated files are saved to:
```
~/.fu7ur3pr00f/data/output/
├── cv_en_ats.md      # Markdown version
└── cv_en_ats.pdf     # PDF version
```

---

## CV Templates

### ATS-Optimized Template (Default)

Designed to pass Applicant Tracking Systems:

- Clean, simple formatting
- Standard section headings
- No graphics or images
- Keyword-rich content
- Reverse chronological order

### Structure

```markdown
# Your Name

**Target Role:** Software Engineer

**Location:** Remote | **Email:** your.email@example.com

## Summary

Results-driven software engineer with 5+ years of experience...

## Experience

### Company Name
**Senior Software Engineer**
*January 2022 – Present*

- Led development of X using Python, Django, and PostgreSQL
- Improved system performance by 40% through optimization
- Mentored 3 junior developers...

### Previous Company
**Software Engineer**
*June 2019 – December 2021*

- Developed RESTful APIs serving 1M+ requests daily
- Implemented CI/CD pipeline reducing deployment time by 60%...

## Education

### University Name
**Bachelor of Science in Computer Science**
*Graduated: May 2019*

## Skills

**Languages:** Python, JavaScript, TypeScript, SQL

**Frameworks:** Django, FastAPI, React, Node.js

**Tools:** Git, Docker, AWS, Kubernetes, PostgreSQL

## Projects

### Project Name
*Personal Project | 2023*

- Built a real-time chat application using WebSockets and Redis
- Deployed on AWS with auto-scaling...

## Certifications

- AWS Certified Solutions Architect (2023)
- Certified Kubernetes Administrator (2022)
```

---

## Generation Requests

### Basic CV

```
> generate my CV
> create my resume
```

Generates CV using your current profile and indexed career data.

### Targeted CV

```
> generate my CV for a Staff Engineer position
> generate a CV targeting remote Python developer roles
> create my CV for Google Senior Software Engineer
```

Customizes CV content for a specific role or company.

### Draft Mode

```
> generate a draft CV for me to review
```

Generates a draft without final formatting.

---

## Before Generating: Prepare Your Data

Better data → better CV. Run these before generating:

```bash
# 1. Index your career data
/gather

# 2. Tell the agent your targets (natural language)
> my target role is Staff Software Engineer
> I specialize in Python, Kubernetes, and distributed systems
> my goal is to lead an engineering team building ML infrastructure
```

Or use the profile tools directly:

```
> update my target role to Staff Software Engineer
> update my skills to Python, Kubernetes, AWS, PostgreSQL, Go
> set my career goal to lead a backend infrastructure team
```

---

## After Generating: Edit and Re-export

Edit the Markdown file directly:

```bash
nano ~/.fu7ur3pr00f/data/output/cv_en_ats.md
# or
$EDITOR ~/.fu7ur3pr00f/data/output/cv_en_ats.md
```

Then ask the agent to regenerate the PDF:

```
> regenerate the PDF from my edited CV file
```

---

## PDF Styling

The PDF uses professional styling via WeasyPrint:

- **Font:** Georgia (serif, ATS-friendly)
- **Size:** 11pt body, 24pt name
- **Margins:** 1.8cm top/bottom, 2.2cm sides
- **Page:** A4 standard
- **Colors:** Dark gray text, subtle accent colors

### System Dependencies

PDF generation requires WeasyPrint system libraries:

```bash
# Debian/Ubuntu
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libfontconfig1 libgdk-pixbuf-2.0-0

# macOS
brew install pango cairo gdk-pixbuf
```

---

## ATS Optimization

### What is ATS?

Applicant Tracking Systems scan and parse CVs before humans see them.

### How FutureProof Optimizes

| Feature | Benefit |
|---------|---------|
| Standard headings | ATS can parse sections |
| No tables/graphics | Prevents parsing errors |
| Keyword matching | Matches job description |
| Clean formatting | Consistent parsing |
| Reverse chronological | ATS-preferred format |

### Best Practices

1. **Use standard job titles** — Avoid internal titles
2. **Include keywords** — Match job description language
3. **Quantify achievements** — Use numbers and percentages
4. **Keep it concise** — 1–2 pages maximum
5. **Use full words** — "Bachelor" not "Bach."

---

## Troubleshooting

### PDF generation fails

**Error:** `WeasyPrint not available` or PDF not created

**Solution:**
```bash
# Install system dependencies
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libfontconfig1 libgdk-pixbuf-2.0-0

# Verify weasyprint
python -c "import weasyprint; print(weasyprint.__version__)"
```

### CV content incomplete

**Issue:** Missing sections or thin content

**Solution:**
1. Gather all data first: `/gather`
2. Ask agent: *"show me knowledge base statistics"*
3. Tell the agent what's missing: *"I have 8 years of Python experience at X, Y, Z companies"*

### CV too long

```
> generate my CV keeping it to 2 pages maximum
> create a concise 1-page CV for startup applications
```

Or edit `~/.fu7ur3pr00f/data/output/cv_en_ats.md` manually and remove older positions.

---

## Examples by Seniority

### Entry-Level CV

```
> generate a CV for an entry-level software engineer role
> emphasize my projects, education, and internships
```

### Senior/Staff CV

```
> generate a CV for a Staff Engineer role at a large tech company
> highlight leadership, architecture decisions, and team impact
```

### Career Change CV

```
> generate a CV for transitioning from finance to software engineering
> emphasize my Python projects, bootcamp, and transferable analytical skills
```

---

## Version Control

Track CV changes with Git:

```bash
cd ~/.fu7ur3pr00f/data/output

git init
git add cv_en_ats.md
git commit -m "CV for Staff Engineer applications — March 2025"
```

---

## See Also

- [Data Gathering](gatherers.md) — Import your career data
- [Tools Reference](tools.md) — CV generation tools
- [Troubleshooting](troubleshooting.md) — Common issues
