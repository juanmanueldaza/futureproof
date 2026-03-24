# Data Gathering Guide

How to import your career data into FutureProof. All data is indexed to ChromaDB for RAG search and analysis.

## Quick Start

```bash
# Place your data files in ~/.fu7ur3pr00f/data/raw/
mkdir -p ~/.fu7ur3pr00f/data/raw

# Then run
fu7ur3pr00f
/gather
```

---

## LinkedIn Export

**File:** `linkedin.zip` (ZIP export from LinkedIn)

### How to Export

1. Go to LinkedIn → **Me** → **Settings & Privacy**
2. Click **Data privacy** → **Get a copy of your data**
3. Select **Want something in particular?** → Check these boxes:
   - Profile
   - Positions (work history)
   - Education
   - Skills
   - Certifications
   - Languages
   - Projects
   - Recommendations
   - Connections
   - Messages (optional)
   - Job applications (optional)
4. Click **Request archive**
5. Wait for email (usually 10-30 minutes)
6. Download ZIP and place in `~/.fu7ur3pr00f/data/raw/`

### What Gets Imported

| Tier | Data | Description |
|------|------|-------------|
| **Tier 1** | Profile, Summary | Name, headline, location, industry |
| | Experience | All positions with dates, descriptions |
| | Education | Schools, degrees, dates |
| | Skills | All endorsed skills |
| | Certifications | Certifications with dates, links |
| | Languages | Languages with proficiency |
| | Projects | Projects with descriptions |
| | Recommendations | Given and received |
| **Tier 2** | Learning | LinkedIn Learning courses |
| | Job applications | Applications submitted |
| | Posts | Shares and posts |
| | Connections | Full network with companies |
| | Messages | Message history (optional) |

### File Format

The ZIP contains multiple CSV files. FutureProof parses:
- `Profile.csv`
- `Positions.csv`
- `Education.csv`
- `Skills.csv`
- `Certifications.csv`
- `Languages.csv`
- `Projects.csv`
- `Recommendations_*.csv`
- `Connections.csv`
- `messages.csv`

---

## CliftonStrengths Assessment

**File:** `*.pdf` (Gallup CliftonStrengths PDF report)

### Supported Report Types

- Top 5 (`SF_TOP_5`)
- Top 10 (`TOP_10`)
- All 34 (`ALL_34`)
- Action Planning (`ACTION_PLANNING_TOP_10`)
- Leadership Insight (`LEADERSHIP_INSIGHT_TOP_10`)
- Discovery Development (`DISCOVERY_DEVELOPMENT`)

### How to Get Your Report

1. Log in to Gallup Access (access.gallup.com)
2. Go to **Strengths** → **Download Reports**
3. Select your assessment
4. Download PDF (choose "Top 10" or "All 34" for best results)
5. Place in `~/.fu7ur3pr00f/data/raw/`

### What Gets Imported

| Data | Description |
|------|-------------|
| Top 5 strengths | Ranked with domain (Executing, Influencing, etc.) |
| Top 10 strengths | Extended ranking |
| All 34 strengths | Complete ranking (if available) |
| Strength insights | Personalized descriptions |
| Action items | Ideas for leveraging each strength |
| Blind spots | Potential weaknesses |
| Quotes | "Sounds like this" examples |

### Requirements

**System:** `poppler-utils` for PDF text extraction

```bash
# Debian/Ubuntu
sudo apt install poppler-utils

# macOS
brew install poppler
```

---

## CV/Resume Import

**File:** `*.pdf`, `*.md`, or `*.txt`

### Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Requires poppler-utils |
| Markdown | `.md` | ATS-optimized format |
| Plain text | `.txt` | Simple format |

### What Gets Imported

FutureProof detects these sections automatically:

- Profile / Summary / Objective
- Experience / Work History
- Education
- Skills / Technical Skills
- Projects
- Certifications
- Languages
- Publications
- Awards / Achievements
- Volunteer Experience
- References

### Markdown Template

For best results, use this Markdown structure:

```markdown
# Your Name

**Headline:** Software Engineer

**Location:** Remote

## Summary

Experienced software engineer with...

## Experience

### Company Name
**Software Engineer**
*2020 – Present*

- Built X using Y
- Improved Z by 40%

### Previous Company
**Junior Developer**
*2018 – 2020*

- Developed features...

## Education

### University Name
**Bachelor of Science in Computer Science**
*2014 – 2018*

## Skills

Python, JavaScript, React, AWS, Docker...

## Projects

### Project Name
Description of project...

## Certifications

- AWS Certified Solutions Architect (2023)
```

---

## Portfolio Website

**URL:** Configured in `.env` as `PORTFOLIO_URL`

### How to Configure

1. Edit `~/.fu7ur3pr00f/.env`:
   ```bash
   PORTFOLIO_URL=https://your-portfolio.com
   ```
2. Restart the chat client

### What Gets Scraped

| Content | Description |
|---------|-------------|
| About page | Bio, background |
| Projects | Project descriptions, tech stack |
| Blog posts | Articles and tutorials |
| Contact | Contact information |
| Resume | Downloadable resume |

### Supported Portfolio Sites

- Personal websites (any domain)
- GitHub Pages
- Vercel / Netlify deployments
- WordPress sites
- Webflow sites

### Requirements

- Portfolio must be publicly accessible (no auth)
- SSRF protection blocks private IP addresses
- Respects `robots.txt`

---

## GitHub Integration

**Auth:** `GITHUB_PERSONAL_ACCESS_TOKEN` in `.env`

### How to Configure

1. Create token at: https://github.com/settings/tokens
2. Required scopes:
   - `repo` (full repo access)
   - `read:user` (read user profile)
   - `user:email` (read email addresses)
3. Add to `.env`:
   ```bash
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
   ```

### What Gets Imported

| Data | Description |
|------|-------------|
| Profile | Bio, location, company |
| Repositories | All public and private repos |
| Contributions | Commit history |
| Languages | Top languages used |
| README files | Project documentation |

---

## GitLab Integration

**Auth:** `glab` CLI authentication

### How to Configure

1. Install `glab`:
   ```bash
   # Debian/Ubuntu
   sudo apt install glab
   
   # macOS
   brew install glab
   ```
2. Authenticate:
   ```bash
   glab auth login
   ```

### What Gets Imported

| Data | Description |
|------|-------------|
| Projects | All accessible projects |
| Repositories | Git repositories |
| Files | Source code files |
| Merge requests | MR history |

---

## Data Directory Structure

```
~/.fu7ur3pr00f/
├── .env                    # Configuration
└── data/
    └── raw/                # Place your data files here
        ├── linkedin.zip    # LinkedIn export
        ├── *.pdf           # CliftonStrengths, CV
        └── resume.md       # CV in Markdown
```

---

## Gathering Commands

In the chat client:

```bash
# Gather all data sources
/gather

# Gather specific sources
/gather linkedin
/gather github
/gather portfolio
/gather cliftonstrengths
/gather cv

# Check what data is indexed
/knowledge stats
```

---

## Troubleshooting

### LinkedIn ZIP not found

**Error:** `FileNotFoundError: LinkedIn export not found`

**Solution:**
1. Ensure ZIP is in `~/.fu7ur3pr00f/data/raw/`
2. File must be named `linkedin.zip` or specify full path

### CliftonStrengths PDF not detected

**Error:** `No Gallup CliftonStrengths PDFs found`

**Solution:**
1. PDF filename must contain: `top_5`, `top_10`, `all_34`, `cliftonstrengths`, or `gallup`
2. Rename if needed: `mv your-report.pdf Top_5_CliftonStrengths.pdf`

### pdftotext not installed

**Error:** `pdftotext is not installed`

**Solution:**
```bash
# Debian/Ubuntu
sudo apt install poppler-utils

# macOS
brew install poppler
```

### GitHub token invalid

**Error:** `401 Unauthorized`

**Solution:**
1. Regenerate token at https://github.com/settings/tokens
2. Ensure scopes: `repo`, `read:user`, `user:email`
3. Update `.env` and restart

### Portfolio scraping fails

**Error:** `SSRF protection` or `Connection refused`

**Solution:**
1. Portfolio must be publicly accessible
2. Cannot scrape localhost or private IPs
3. Check firewall settings

---

## See Also

- [Configuration](configuration.md) — Setting up `.env`
- [Tools Reference](tools.md) — Gathering tools details
- [Troubleshooting](troubleshooting.md) — Common issues
