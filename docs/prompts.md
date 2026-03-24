# Prompts System

How FutureProof uses prompts to guide LLM responses.

---

## Overview

FutureProof uses a modular prompt system:

| Prompt | Purpose |
|--------|---------|
| `system.md` | Main system prompt (always active) |
| `analyze_career.md` | Career alignment analysis |
| `analyze_gaps.md` | Skill gap analysis |
| `generate_cv.md` | CV generation |
| `market_fit.md` | Market fit analysis |
| `market_skill_gap.md` | Market skill gaps |
| `strategic_advice.md` | Strategic career advice |
| `synthesis.md` | Response synthesis |
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

### Key Sections

```markdown
## About FutureProof
You are FutureProof, a career intelligence assistant...

## User Profile
<user_data>
{user_profile}
</user_data>

## Critical Behaviors
1. Data fidelity: Use only data from knowledge base
2. Search before claiming: Always search first
3. Complete multi-step requests
4. Auto-index after gathering
...
```

### Dynamic Injection

The following are injected at runtime:
- `{user_profile}` — Current user profile
- `{career_data}` — Indexed career data
- `{market_data}` — Market intelligence
- `{tool_results}` — Tool execution results

---

## Analysis Prompts

### Career Alignment (`analyze_career.md`)

Analyzes how well current career aligns with goals.

**Used by:** `analyze_career_alignment` tool

**Template:**
```markdown
Analyze career alignment considering:
1. Current role vs target role
2. Skills vs requirements
3. Industry trends
4. Growth opportunities
```

### Skill Gaps (`analyze_gaps.md`)

Identifies skill gaps between current and target role.

**Used by:** `analyze_skill_gaps` tool

**Template:**
```markdown
Compare current skills to target role requirements:
1. Missing skills
2. Skills to strengthen
3. Learning resources
4. Timeline estimates
```

### Market Fit (`market_fit.md`)

Analyzes market fit for target roles.

**Used by:** `analyze_market_fit` tool

### Market Skill Gap (`market_skill_gap.md`)

Identifies in-demand skills for target market.

**Used by:** `analyze_market_skills` tool

---

## Generation Prompts

### CV Generation (`generate_cv.md`)

Generates ATS-optimized CV.

**Used by:** `generate_cv` tool

**Key requirements:**
- ATS-friendly formatting
- Keyword optimization
- Quantified achievements
- Reverse chronological order

**Template:**
```markdown
Generate an ATS-optimized CV with:
1. Contact information
2. Professional summary
3. Experience (reverse chronological)
4. Education
5. Skills
6. Certifications
7. Projects

Use data from: {career_data}
Target role: {target_role}
```

---

## Synthesis Prompt

**File:** `prompts/md/synthesis.md`

Used by `AnalysisSynthesisMiddleware` to replace generic LLM responses with focused synthesis.

**Purpose:**
- GPT-4o tends to genericize responses
- Synthesis prompt forces specific, data-backed insights
- Uses reasoning models (o4-mini, etc.)

**Flow:**
```
Agent → Tool execution → Generic response → Middleware → Synthesis → Final response
```

---

## Strategic Advice Prompt

**File:** `prompts/md/strategic_advice.md`

Generates long-term career strategy.

**Used by:** `get_career_advice` tool

**Template:**
```markdown
Provide strategic career advice:
1. Short-term actions (0-6 months)
2. Medium-term goals (6-18 months)
3. Long-term vision (18+ months)
4. Risk mitigation
5. Success metrics
```

---

## Trending Skills Prompt

**File:** `prompts/md/trending_skills.md`

Analyzes technology trends.

**Used by:** `get_tech_trends` tool

**Sources:**
- Hacker News "Who's Hiring"
- Job postings
- Stack Overflow trends
- Dev.to articles

---

## Prompt Loading

### In Code

```python
from fu7ur3pr00f.prompts import load_prompt, get_prompt_builder

# Load specific prompt
cv_prompt = load_prompt("generate_cv")

# Get builder for dynamic prompts
builder = get_prompt_builder()
builder.set_user_profile(profile)
builder.set_career_data(data)
prompt = builder.build()
```

### Lazy Loading

Prompts are loaded lazily from `prompts/md/*.md`:

```python
from fu7ur3pr00f.prompts import GENERATE_CV_PROMPT

# Loads generate_cv.md on first access
print(GENERATE_CV_PROMPT)
```

---

## Customization

### Modify Existing Prompts

Edit files in `src/fu7ur3pr00f/prompts/md/`:

```bash
# Edit CV generation prompt
nano src/fu7ur3pr00f/prompts/md/generate_cv.md
```

### Add New Prompts

1. Create `prompts/md/my_prompt.md`
2. Add to `prompts/__init__.py`:
   ```python
   _PROMPT_MAP["MY_PROMPT"] = "my_prompt"
   ```
3. Access via:
   ```python
   from fu7ur3pr00f.prompts import MY_PROMPT
   ```

### Dynamic Prompt Building

```python
from fu7ur3pr00f.prompts.builders import get_prompt_builder

builder = get_prompt_builder()
builder.set_user_profile(profile)
builder.set_career_data(data)
builder.set_target_role("Senior Engineer")
prompt = builder.build("analyze_gaps")
```

---

## Prompt Variables

Available variables for injection:

| Variable | Description |
|----------|-------------|
| `{user_profile}` | Current user profile |
| `{career_data}` | Indexed career data |
| `{market_data}` | Market intelligence |
| `{target_role}` | Target job title |
| `{skills}` | User skills |
| `{experience}` | Work experience |
| `{education}` | Education history |
| `{tool_results}` | Tool execution results |

---

## Best Practices

### Writing Prompts

1. **Be specific** — Clear instructions
2. **Use examples** — Show expected output format
3. **Set constraints** — Length, style, tone
4. **Inject data** — Use `{variables}` for dynamic content
5. **Test iteratively** — Refine based on outputs

### Prompt Engineering

1. **Chain of thought** — Ask model to reason step-by-step
2. **Few-shot learning** — Provide examples
3. **Role prompting** — "You are an expert career advisor"
4. **Output formatting** — Specify Markdown, JSON, etc.
5. **Temperature tuning** — Lower for consistency, higher for creativity

---

## Troubleshooting

### Prompt not loading

**Error:** `AttributeError: module has no attribute 'MY_PROMPT'`

**Solution:**
1. Check file exists: `prompts/md/my_prompt.md`
2. Add to `_PROMPT_MAP` in `prompts/__init__.py`
3. Restart application

### Variables not injected

**Issue:** `{variable}` appears literally in output

**Solution:**
1. Use `get_prompt_builder()` for dynamic prompts
2. Call `builder.set_<variable>()` for each variable
3. Call `builder.build()` to finalize

### Generic responses

**Issue:** LLM gives generic advice

**Solution:**
1. Check `AnalysisSynthesisMiddleware` is active
2. Use reasoning model for synthesis
3. Add more specific instructions to prompt
4. Inject more data context

---

## See Also

- [Architecture](architecture.md) — System design
- [Tools Reference](tools.md) — Tool documentation
- [CV Generation](cv_generation.md) — CV prompt details
