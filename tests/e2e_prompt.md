# FutureProof E2E Test Prompt

Paste the prompt below into `futureproof chat` to exercise all 39 agent tools.

**Prerequisites:**
- LinkedIn ZIP at `data/raw/Complete_LinkedInDataExport_02-07-2026.zip.zip`
- CliftonStrengths PDFs in `data/raw/` (Daza-Juan-*.pdf)
- `PORTFOLIO_URL` configured in `.env`
- `GITHUB_PERSONAL_ACCESS_TOKEN` configured in `.env`
- `glab` CLI authenticated (for GitLab tools)
- `TAVILY_API_KEY` configured (for market intelligence)

**HITL interrupts:** Steps 3, 10, and 12 trigger human-in-the-loop confirmation (answer "y").

**Expected outcome:** All tools called, knowledge base populated from 3 sources, CV generated with rich content, episodic memory stored.

---

## Prompt

```
I want to do a complete setup, data gathering, analysis, and evaluation of my career intelligence system. Execute each step fully before moving to the next. Do NOT skip any step or sub-step.

## 1. Profile Setup
- Set my name to "Juan Manuel Daza"
- Set my current role to "Senior Full-Stack Developer" with 12 years of experience
- Add these technical skills: Python, TypeScript, Vue.js, React, LangChain, LangGraph, Node.js, Docker, Azure, PostgreSQL
- Add these soft skills: Leadership, Mentoring, Strategic Thinking, Cross-functional Communication
- Set my target roles to: "Staff Engineer", "Engineering Manager", "AI/ML Engineer"
- Add a high-priority goal: "Transition into AI/ML engineering within 12 months"
- Add a medium-priority goal: "Build leadership experience through open-source contributions"
- Show me my complete profile

## 2. Knowledge Base Cleanup
- Show current knowledge base stats
- If there is any existing data, clear the entire knowledge base (I'll approve)

## 3. Data Gathering — All Sources
- Gather all career data at once using gather_all_career_data (I'll approve)
- After gathering, show knowledge base stats — I expect chunks from portfolio, linkedin, AND assessment

## 4. Verify Knowledge Base Content
- Search the knowledge base for "work experience" filtered to linkedin source
- Search the knowledge base for "strengths" filtered to assessment source
- Search the knowledge base for "projects" filtered to portfolio source
- Show the full stored career data summary

## 5. GitHub Exploration
- Look up my GitHub profile
- Search my GitHub repos (user:juanmanueldaza) and show the top 5
- Read the README.md of my most interesting repo using get_github_repo

## 6. GitLab Exploration
- Search GitLab for my projects
- Pick the most relevant project and get its details using get_gitlab_project
- Read its README.md using get_gitlab_file

## 7. Career Analysis (all 3 tools)
- Analyze my skill gaps for "AI/ML Engineer"
- Analyze my overall career alignment
- Give me strategic career advice for transitioning to "Staff Engineer"

## 8. Market Intelligence & Financial (all 8 tools)
- Gather comprehensive market data from all sources (trends, jobs, content)
- Search for remote "AI Engineer" jobs, limit to 10
- Get the latest tech trends focused on "AI"
- Get salary insights for "Staff Engineer" in remote positions
- Analyze my market fit based on current demands
- Analyze which market skills I should develop
- Convert 28138400 ARS to USD using convert_currency
- Compare a salary of 28138400 ARS in Argentina against the US using compare_salary_ppp

## 9. CV Draft
- Generate a CV draft for "AI/ML Engineer" — show me the preview

## 10. Full CV Generation
- Generate my full CV in ATS format in English targeting "AI/ML Engineer" (I'll approve)
- Then generate a second CV in Spanish creative format targeting "Staff Engineer" (I'll approve)

## 11. Knowledge Search — Cross-Source Queries
- Search knowledge base for "Python" across all sources (no source filter)
- Search knowledge base for "leadership" across all sources
- Search knowledge base for "certifications" filtered to linkedin

## 12. Episodic Memory
- Remember this decision: "Decided to focus on AI/ML transition" with context "After analyzing skill gaps and market trends, AI/ML has the strongest career trajectory" and outcome "Starting with LangChain/LangGraph agentic AI projects"
- Remember this job application: company "Anthropic", role "AI Engineer", status "applied", notes "Applied via careers page, strong alignment with agentic AI experience"
- Remember another application: company "Google DeepMind", role "Research Engineer", status "interviewing", notes "Phone screen scheduled for next week"
- Recall memories about "AI career"
- Recall memories about "job applications"
- Show memory statistics — I expect at least 1 decision and 2 applications

## 13. Final Review
- Show my complete profile one more time
- Show knowledge base stats (should have linkedin + portfolio + assessment data)
- Show memory stats (should have 3+ memories)
- Give me a comprehensive summary of everything we accomplished and your top 3 recommendations based on ALL the data you've gathered about my career
```
