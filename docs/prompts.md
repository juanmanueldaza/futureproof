# Prompts System

How FutureProof uses prompts to guide LLM responses.

---

## Overview

FutureProof uses a modular prompt system. Prompts are Markdown files in `src/fu7ur3pr00f/prompts/md/`, loaded at runtime by `prompts/loader.py`.

| Prompt File | Purpose |
|-------------|---------|
| `system.md` | Main system prompt (injected on every model call) |
| `analyze_career.md` | Career alignment analysis |
| `analyze_gaps.md` | Skill gap analysis |
| `generate_cv.md` | CV generation |
| `market_fit.md` | Market fit analysis |
| `market_skill_gap.md` | Market skill gaps |
| `strategic_advice.md` | Strategic career advice |
| `synthesis.md` | Response synthesis (used by `AnalysisSynthesisMiddleware`) |
| `trending_skills.md` | Tech trends analysis |

---

## System Prompt

**File:** `prompts/md/system.md`

The system prompt defines:
- Assistant identity (FutureProof)
- User profile injection
- Critical behaviors
- Tool usage guidelines
- Knowledge base sources
- Human-in-the-loop rules

### Dynamic Injection

The system prompt is regenerated on every model call via `build_dynamic_prompt` middleware. It uses a 5-second TTL cache to avoid repeated disk I/O and ChromaDB queries across the 3–5 model calls per user message.

At runtime, the following is injected:
- `{user_profile}` — Current user profile (from `~/.fu7ur3pr00f/profile.yaml`), PII-anonymized
- Live knowledge base stats — Appended as a "Data Availability (live)" section showing source → chunk counts

If the profile is empty but the knowledge base has data, `build_dynamic_prompt` will auto-populate the profile from indexed career data.

**Security:** Profile content is passed through `anonymize_career_data()` and `sanitize_for_prompt()` before injection to prevent PII leakage and XML boundary injection.

---

## Analysis Prompts

### Career Alignment (`analyze_career.md`)

Analyzes how well current career aligns with goals.

**Used by:** `analyze_career_alignment` tool  
**Orchestrator action:** `analyze_full`

### Skill Gaps (`analyze_gaps.md`)

Identifies skill gaps between current and target role.

**Used by:** `analyze_skill_gaps` tool

### Market Fit (`market_fit.md`)

Analyzes market fit for target roles.

**Used by:** `analyze_market_fit` tool  
**Orchestrator action:** `analyze_market_fit`

### Market Skill Gap (`market_skill_gap.md`)

Identifies in-demand skills for target market.

**Used by:** `analyze_market_skills` tool  
**Orchestrator action:** `analyze_skills`

---

## Generation Prompts

### CV Generation (`generate_cv.md`)

Generates ATS-optimized CV content from indexed career data.

**Used by:** `generate_cv` tool

**Key requirements enforced:**
- ATS-friendly formatting (no tables, no graphics)
- Standard section headings
- Quantified achievements
- Reverse chronological order
- Keyword density matching target role

---

## Synthesis Prompt

**File:** `prompts/md/synthesis.md`

Used by `AnalysisSynthesisMiddleware` to generate the final response when analysis tools have been called.

**Why this exists:** GPT-4o tends to genericize analysis tool results when writing its final response. The synthesis middleware:

1. **Pass 1 (before model):** Replaces analysis tool messages with a short `[Detailed analysis was displayed directly to the user...]` marker. The agent model cannot see or rewrite the actual results.
2. **Pass 2 (after model):** If the agent's final response (no tool calls remaining) was produced with masked analysis data, it is **discarded** and replaced with a fresh synthesis call using a reasoning model (e.g., `o4-mini`) that sees the actual tool data.

The synthesis prompt receives:
- `{user_question}` — The original user message
- `{tool_results}` — All analysis + other tool results from the current turn (PII-anonymized)

---

## Strategic Advice Prompt

**File:** `prompts/md/strategic_advice.md`

Generates long-term career strategy.

**Used by:** `get_career_advice` tool  
**Orchestrator action:** `advise`

---

## Trending Skills Prompt

**File:** `prompts/md/trending_skills.md`

Analyzes technology trends from multiple sources.

**Used by:** `get_tech_trends` tool

**Sources:** Hacker News "Who's Hiring", job postings, Stack Overflow trends, Dev.to articles

---

## Prompt Loading

### In Code

```python
from fu7ur3pr00f.prompts import load_prompt, get_prompt_builder

# Load specific prompt
cv_prompt = load_prompt("generate_cv")

# Get builder for dynamic prompts
builder = get_prompt_builder()
prompt = builder.build_analysis_prompt("analyze_full", career_data)
```

### Lazy Loading

Prompts are loaded lazily from `prompts/md/*.md`:

```python
from fu7ur3pr00f.prompts.loader import load_prompt

# Loads generate_cv.md on first access, caches thereafter
text = load_prompt("generate_cv")
```

---

## Customization

### Modify Existing Prompts

Edit files directly in `src/fu7ur3pr00f/prompts/md/`:

```bash
nano src/fu7ur3pr00f/prompts/md/generate_cv.md
```

Changes take effect on the next model call (subject to the 5-second system prompt TTL cache for `system.md`; other prompts are loaded fresh each call).

### Add New Prompts

1. Create `prompts/md/my_prompt.md`
2. Load via:
   ```python
   from fu7ur3pr00f.prompts.loader import load_prompt
   text = load_prompt("my_prompt")
   ```
3. Register in `prompts/__init__.py` if you need it accessible as a named export

---

## Prompt Variables

Variables available for injection (via `str.format()` in code):

| Variable | Description | Used In |
|----------|-------------|---------|
| `{user_profile}` | Current user profile (PII-anonymized) | `system.md` |
| `{target_role}` | Target job title | `analyze_gaps.md`, `generate_cv.md` |
| `{career_data}` | Indexed career data chunks | `generate_cv.md`, analysis prompts |
| `{market_context}` | Market intelligence data | `market_fit.md`, `market_skill_gap.md` |
| `{user_question}` | Original user message | `synthesis.md` |
| `{tool_results}` | Tool execution results | `synthesis.md` |

---

## Best Practices

### Writing Prompts

1. **Be specific** — Clear, unambiguous instructions
2. **Specify output format** — Markdown sections, lists, tables
3. **Set constraints** — Length, tone, what NOT to do
4. **Use variables sparingly** — Only inject data that changes per call

### Prompt Engineering Notes

- **Analysis prompts** are used by tools, not the main system prompt — changes here affect specific tool outputs
- **Synthesis prompt** is critical: it controls what the user sees as the final response after analysis tools run. Tune this if synthesis feels off.
- **System prompt** controls the agent's general behavior. Avoid making it too long — it's injected on every model call and contributes to token cost.

---

## Troubleshooting

### Prompt not found

**Error:** `FileNotFoundError: No such file: prompts/md/my_prompt.md`

**Solution:**
1. Check file exists: `ls src/fu7ur3pr00f/prompts/md/`
2. Use exact filename without `.md` extension in `load_prompt()`

### Variables not injected

**Issue:** `{variable}` appears literally in output

**Solution:**
1. Call `str.format(variable=value)` after loading the prompt
2. Use `get_prompt_builder()` for complex cases with multiple variables

### Generic responses despite analysis tools

**Issue:** Agent rewrites analysis results into generic advice

**Solution:**
1. Check `AnalysisSynthesisMiddleware` is in the middleware list in `career_agent.py`
2. Verify the synthesis prompt (`synthesis.md`) is specific enough
3. Confirm a reasoning model is configured for synthesis (`SYNTHESIS_MODEL=o4-mini`)

---

## See Also

- [Architecture](architecture.md) — Middleware and synthesis design
- [Tools Reference](tools.md) — Which tools use which prompts
- [CV Generation](cv_generation.md) — CV prompt details
