# CV Generation Guide

Generate ATS-optimized CVs in Markdown and PDF formats.

## Quick Start

```bash
fu7ur3pr00f
/generate cv
```

Or target a specific role:

```bash
/generate cv for Senior Python Developer position at tech company
```

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
data/output/
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

## Generation Commands

### Basic CV

```bash
/generate cv
```

Generates CV using your current profile and target role.

### Targeted CV

```bash
/generate cv for Staff Engineer position
/generate cv targeting remote Python developer roles
/generate cv for Google Senior Software Engineer position
```

Customizes CV for specific role or company.

### Draft Mode

```bash
/generate cv draft
```

Generates a draft for review before finalizing.

---

## Customization

### Before Generation

Update your profile for better results:

```bash
# Set target role
/set target_role Staff Software Engineer

# Update skills
/update skills Python, Kubernetes, AWS, Machine Learning

# Update current role
/update current_role Senior Software Engineer at Tech Corp

# Set career goal
/set goal Lead engineering team building distributed systems
```

### After Generation

Edit the Markdown file directly:

```bash
# Edit generated CV
nano data/output/cv_en_ats.md

# Or with your editor
$EDITOR data/output/cv_en_ats.md
```

Then regenerate PDF:

```bash
# Regenerate PDF from edited Markdown
/generate cv from-file data/output/cv_en_ats.md
```

---

## PDF Styling

The PDF uses professional styling:

- **Font:** Georgia (serif, ATS-friendly)
- **Size:** 11pt body, 24pt name
- **Margins:** 1.8cm top/bottom, 2.2cm sides
- **Page:** A4 standard
- **Colors:** Dark gray text, subtle accent colors

### Requirements

PDF generation requires:
- `weasyprint` (Python package, included)
- System dependencies (see below)

### System Dependencies

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
2. **Include keywords** — Match job description
3. **Quantify achievements** — Use numbers and percentages
4. **Keep it concise** — 1-2 pages maximum
5. **Use full words** — "Bachelor" not "Bach."

---

## Troubleshooting

### PDF generation fails

**Error:** `WeasyPrint not available` or PDF missing

**Solution:**
```bash
# Install system dependencies
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libfontconfig1 libgdk-pixbuf-2.0-0

# Reinstall weasyprint
pip install weasyprint
```

### CV content incomplete

**Issue:** Missing sections or data

**Solution:**
1. Ensure data is gathered: `/gather`
2. Check knowledge base: `/knowledge stats`
3. Update profile: `/get profile`

### Formatting issues in PDF

**Issue:** Weird spacing or broken layout

**Solution:**
1. Edit Markdown file to fix content
2. Remove any custom formatting
3. Regenerate PDF

### CV too long

**Solution:**
```bash
# Generate with length constraint
/generate cv keeping it to 2 pages maximum
```

Or edit manually:
- Remove older positions (10+ years)
- Consolidate similar roles
- Trim project descriptions

---

## Examples

### Entry-Level CV

```
/generate cv for entry-level software engineer position

# Emphasizes:
- Education
- Projects
- Internships
- Relevant coursework
```

### Senior CV

```
/generate cv for Staff Engineer role

# Emphasizes:
- Leadership experience
- Architecture decisions
- Team mentoring
- Technical impact
```

### Career Change CV

```
/generate cv transitioning from finance to software engineering

# Emphasizes:
- Transferable skills
- Projects and bootcamps
- Domain expertise
- Technical skills
```

---

## Version Control

Track CV changes with Git:

```bash
cd ~/Projects/fu7ur3pr00f/data/output

# Initialize git (if not already)
git init

# Track CV
git add cv_en_ats.md
git commit -m "Update CV for Staff Engineer applications"
```

---

## See Also

- [Data Gathering](gatherers.md) — Import your career data
- [Tools Reference](tools.md) — CV generation tools
- [Troubleshooting](troubleshooting.md) — Common issues
