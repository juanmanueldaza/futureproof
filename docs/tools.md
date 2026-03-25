# Tools Reference

The career agent has **41 tools** organized by domain. All tools are defined in `src/fu7ur3pr00f/agents/tools/`.

## Tool Categories

| Category | Count | Description |
|----------|-------|-------------|
| Profile | 7 | User profile, goals, salary info |
| Gathering | 5 | LinkedIn, portfolio, assessments, CV |
| GitHub | 3 | GitHub repos and profile |
| GitLab | 3 | GitLab projects and files |
| Knowledge | 4 | RAG search and indexing |
| Analysis | 3 | Skill gaps, career alignment, advice |
| Market | 6 | Job search, trends, salary, market fit |
| Financial | 2 | Currency conversion, PPP comparison |
| Generation | 2 | CV generation |
| Memory | 4 | Episodic memory (decisions, applications) |
| Settings | 2 | Configuration management |

---

## Profile Tools (7)

Manage user profile, career goals, and personal information.

| Tool | Description |
|------|-------------|
| `get_user_profile` | Get complete user profile |
| `update_user_name` | Update user's name |
| `update_current_role` | Update current job title/role |
| `update_salary_info` | Update salary and compensation |
| `update_user_skills` | Update skills list |
| `set_target_roles` | Set target job titles |
| `update_user_goal` | Update career goals |

**File:** `tools/profile.py`

---

## Gathering Tools (5)

Collect career data from various sources and index to ChromaDB.

| Tool | Description |
|------|-------------|
| `gather_portfolio_data` | Scrape portfolio website |
| `gather_linkedin_data` | Import LinkedIn CSV export |
| `gather_assessment_data` | Import CliftonStrengths PDF |
| `gather_cv_data` | Import existing CV (PDF/MD/TXT) |
| `gather_all_career_data` | Run all gatherers at once (HITL confirmation) |

**File:** `tools/gathering.py`

---

## GitHub Tools (3)

Access GitHub data via MCP.

| Tool | Description |
|------|-------------|
| `search_github_repos` | Search user's repositories |
| `get_github_repo` | Get specific repository details |
| `get_github_profile` | Get GitHub profile and contributions |

**File:** `tools/github.py`  
**Requires:** `GITHUB_PERSONAL_ACCESS_TOKEN` in `.env`

---

## GitLab Tools (3)

Access GitLab data via `glab` CLI.

| Tool | Description |
|------|-------------|
| `search_gitlab_projects` | Search user's projects |
| `get_gitlab_project` | Get specific project details |
| `get_gitlab_file` | Get file contents from GitLab |

**File:** `tools/gitlab.py`  
**Requires:** `glab` CLI installed and authenticated

---

## Knowledge Tools (4)

RAG search and indexing over career data (ChromaDB at `~/.fu7ur3pr00f/episodic/`).

| Tool | Description |
|------|-------------|
| `search_career_knowledge` | Search indexed career data |
| `get_knowledge_stats` | Get knowledge base statistics |
| `index_career_knowledge` | Index new data to ChromaDB |
| `clear_career_knowledge` | Clear all knowledge base data (HITL confirmation) |

**File:** `tools/knowledge.py`

---

## Analysis Tools (3)

Career analysis and guidance. Results are displayed directly to the user in Rich panels. The agent's final text response is replaced by `AnalysisSynthesisMiddleware` with focused reasoning-model synthesis.

| Tool | Description |
|------|-------------|
| `analyze_skill_gaps` | Analyze gaps between current and target role |
| `analyze_career_alignment` | Analyze career alignment with goals |
| `get_career_advice` | Get personalized strategic career advice |

**File:** `tools/analysis.py`

---

## Market Tools (6)

Job market intelligence via MCP clients.

| Tool | Description |
|------|-------------|
| `search_jobs` | Search 7 job boards + Hacker News |
| `get_tech_trends` | Get technology trends (HN, Stack Overflow, Dev.to) |
| `get_salary_insights` | Get salary data for roles/locations (Tavily) |
| `analyze_market_fit` | Analyze market fit for target roles |
| `analyze_market_skills` | Analyze in-demand skills for market |
| `gather_market_data` | Gather market data from multiple sources |

**File:** `tools/market.py`

---

## Financial Tools (2)

Real-time financial data via the Financial MCP client.

| Tool | Description |
|------|-------------|
| `convert_currency` | Real-time currency conversion |
| `compare_salary_ppp` | Compare salary purchasing power parity |

**File:** `tools/financial.py`

---

## Generation Tools (2)

CV and document generation.

| Tool | Description |
|------|-------------|
| `generate_cv` | Generate ATS-optimized CV (Markdown + PDF, HITL confirmation) |
| `generate_cv_draft` | Generate CV draft for review |

**File:** `tools/generation.py`  
**Output:** `~/.fu7ur3pr00f/data/output/cv_en_ats.md` and `.pdf`

---

## Memory Tools (4)

Episodic memory stored in ChromaDB (`~/.fu7ur3pr00f/episodic/`).

| Tool | Description |
|------|-------------|
| `remember_decision` | Save career decision to memory |
| `remember_job_application` | Save job application to memory |
| `recall_memories` | Recall memories by query |
| `get_memory_stats` | Get memory statistics |

**File:** `tools/memory.py`

---

## Settings Tools (2)

Configuration management.

| Tool | Description |
|------|-------------|
| `get_current_config` | Get current agent configuration |
| `update_setting` | Update agent settings |

**File:** `tools/settings.py`

---

## Adding New Tools

1. Create function in appropriate domain file (e.g., `tools/market.py`)
2. Add `@tool` decorator with name and description
3. Add to `_ALL_TOOLS` list in `tools/__init__.py`
4. Write tests in `tests/agents/tools/`

```python
from langchain.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """Tool description.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
    """
    ...
```

---

## See Also

- [Architecture](architecture.md) — Single agent design and middleware
- [Development](development.md) — Adding tools guide
- [QWEN.md](../QWEN.md) — Qwen Code instructions
