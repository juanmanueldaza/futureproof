<instructions>
Analyze the following professional data using this step-by-step process:

**Step 1: Extract professional identity**
- Identify current role, company, and industry from the data
- Note 2-3 standout differentiators (specific skills, credentials, or experiences)
- If CliftonStrengths data exists, identify top themes

**Step 2: Calculate alignment score (0-100)**
- Compare stated goals/target roles against actual experience
- Weight: core skills 2x, nice-to-have 1x
- Score = (demonstrated skills / required skills) × 100
- Cite specific evidence for the score

**Step 3: Identify top strengths for income leverage**
- Review all data sources: LinkedIn, portfolio, GitHub, assessments
- For each strength: name specific evidence (project, role, contribution)
- If CliftonStrengths exists: dedicate 2-3 bullets to specific themes
- Consider income paths beyond employment: freelancing, consulting, products, open source, teaching

**Step 4: Identify critical gaps blocking higher income**
- Name specific missing skills, certifications, portfolio pieces, or experience types
- Include visibility/networking gaps if data shows limited public presence
- Prioritize gaps that block multiple goals simultaneously

**Step 5: Generate ranked action plan**
- For each action: name the specific gap it closes or strength it leverages
- Actions must be concrete (what, when, how) not vague advice
- Rank by income impact (highest first)
- Consider both employment and non-employment income paths
</instructions>

<constraints>
  <max_words>800</max_words>
  <format>bullet_points_only</format>
  <required_sections>
    <section>Professional Identity</section>
    <section>Alignment Score</section>
    <section>Top Strengths</section>
    <section>Critical Gaps</section>
    <section>Action Plan</section>
  </required_sections>
  <forbidden_patterns>
    <pattern>vague advice like "improve skills" without naming specific skills</pattern>
    <pattern>generic statements not tied to user's actual data</pattern>
    <pattern>recommendations without concrete next steps</pattern>
    <pattern>repeating the same action verb in multiple bullets</pattern>
  </forbidden_patterns>
  <required_elements>
    <element>Name current role and company</element>
    <element>Cite at least 3 specific strengths with evidence</element>
    <element>Name at least 3 critical gaps with specifics</element>
    <element>If CliftonStrengths exists: name specific themes and income applications</element>
    <element>Action plan ranked by income impact (3-5 items)</element>
  </required_elements>
</constraints>

<examples>
<example>
<input>
User: Senior Software Engineer at startup, 4 years experience
Skills: Python, React, Node.js, AWS
Goal: "Become a Staff Engineer specializing in distributed systems"
GitHub: 3 repos, 2 with READMEs, no recent activity
CliftonStrengths: Strategic, Analytical, Learner
</input>

<output>
### Professional Identity
- Senior Software Engineer at early-stage startup, 4 years full-stack experience
- Standout: Built AWS infrastructure serving 10k+ users, full-stack ownership from frontend to deployment
- CliftonStrengths: Strategic + Analytical = natural systems thinker who sees architectural patterns

### Alignment Score: 58/100
Claims distributed systems specialization but has no evidence of large-scale architecture (no multi-region, no high-availability design, no performance optimization at scale).

### Top Strengths (leverage for higher income)
- **Full-stack ownership**: Built and deployed complete systems (React + Node.js + AWS) — rare T-shaped skill set
- **Strategic thinking**: CliftonStrengths Strategic theme enables seeing 2-3 moves ahead — valuable for architecture roles
- **Learning agility**: Learner theme + 4 years of rapid skill acquisition — can ramp on new technologies quickly
- **Startup experience**: Wore multiple hats, made tradeoff decisions — prepares you for senior roles at scale-up companies

### Critical Gaps (fixing these unlocks higher income)
- **Distributed systems depth**: No evidence of multi-region deployments, eventual consistency patterns, or high-availability architecture
- **Technical leadership**: No blog posts, talks, or open source contributions — invisible to the market
- **Scale experience**: Systems built serve 10k users, not 1M+ — Staff roles require proving impact at scale
- **GitHub presence**: 3 repos with minimal activity — recruiters use GitHub as proof of passion and skills

### Action Plan (ranked by income impact)
1. **Lead architecture design for high-traffic feature** (next 90 days) — closes distributed systems gap; document decisions and tradeoffs
2. **Start technical blog** (next 60 days, then monthly) — write about startup engineering challenges; establishes thought leadership
3. **Contribute to one distributed systems OSS project** (3-6 months) — Cassandra, Kafka, or etcd; demonstrates production-level systems skills
4. **Speak at local meetup** (6 months) — present "Scaling from 0 to 10k Users"; builds reputation and network
5. **Build side project with real users** (ongoing) — aim for 1k+ users; proves you can ship and iterate independently
</output>
</example>
</examples>

Analyze the following professional data. Base analysis only on provided data — never speculate.

<output_format>
### Professional Identity
- Current role and company
- 2-3 standout differentiators (name specific skills, credentials, or experiences)

### Alignment Score: X/100
One sentence explaining the score, citing specific evidence (e.g., "75/100 — headline says AI Engineer but only 1 of 8 repos uses ML").

### Top Strengths (leverage for higher income)
- [Strength]: [specific evidence from data] (3-5 bullets)
- If CliftonStrengths data exists, dedicate 2-3 bullets to the specific themes — name them and explain how each one creates a competitive advantage or income opportunity (e.g., "Ideation + Strategic = natural consultant who sees patterns others miss")
- Consider income potential beyond employment: freelancing, consulting, products, open source monetization, courses, content creation
- Consider networking and community: speaking, open source contributions, professional communities that lead to opportunities

### Critical Gaps (fixing these unlocks higher income)
- [Gap]: [what's missing and why it matters] (3-5 bullets)
- Name specific missing skills, certifications, portfolio pieces, or experience types
- Include gaps in visibility/networking if the data shows limited public presence

### Action Plan (ranked by income impact)
1. [Specific action] — closes [specific gap] by [concrete step]. Example: "Add README + demo to FutureProof repo" not "improve documentation".
2. [Specific action] — leverages [specific strength].
3. [Specific action] — addresses [specific weakness].
(3-5 items max. Each must reference a finding above by name. Consider both employment and non-employment income paths.)
</output_format>
