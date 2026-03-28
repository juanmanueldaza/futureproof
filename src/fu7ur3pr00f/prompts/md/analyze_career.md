<instructions>
Analyze the following professional data using this step-by-step process:

**Step 1: Extract professional identity**
- Identify current role, company, and industry from the data
- Note 2-3 standout differentiators (specific skills, credentials, or experiences)
- If CliftonStrengths data exists, identify top themes
- **Sovereignty Check**: Prioritize "Signature Achievements" that are publicly verifiable (Open Source, public repos, talks, blog posts)

**Step 2: Calculate alignment score with confidence metric**
- Compare stated goals/target roles against actual experience
- Weight: core skills 2x, nice-to-have 1x
- Score = (demonstrated skills / required skills) × 100
- **Confidence Score**: Y/100 — explicitly state what data is missing (e.g., "Confidence: 60/100 — missing recent backend repos, no public architecture docs")
- Cite specific evidence for the score

**Step 3: Identify top strengths for income leverage**
- Review all data sources: LinkedIn, portfolio, GitHub, assessments
- For each strength: name specific evidence (project, role, contribution)
- If CliftonStrengths exists: dedicate 2-3 bullets to specific themes
- **Sovereignty-Adjusted Ranking**: Rank strengths by both Income Impact AND Sovereignty Score
  - An Open Source contribution that builds public reputation ranks higher than a proprietary internal promotion
  - "No-lock-in" career capital (portable skills, public brand) > company-specific capital

**Step 4: Identify critical gaps blocking higher income**
- Name specific missing skills, certifications, portfolio pieces, or experience types
- Include visibility/networking gaps if data shows limited public presence
- **Cross-reference with GitHub**: If a repo contradicts a claimed gap (e.g., user has a LangChain project but analysis says "no AI experience"), declare that gap FALSE and identify the next real gap
- Prioritize gaps that block multiple goals simultaneously

**Step 5: Generate ranked action plan with dual metrics**
- For each action: name the specific gap it closes or strength it leverages
- Actions must be concrete (what, when, how) not vague advice
- **Dual Ranking**: Rank by both Income Impact (€/$) AND Sovereignty Score (0-100)
  - Example: "Contribute to LangChain (Income: €5k-€10k consulting premium, Sovereignty: 90/100 — builds public reputation, no lock-in)"
- Consider both employment and non-employment income paths: freelancing, consulting, products, open source, teaching
</instructions>

<constraints>
  <max_words>800</max_words>
  <format>bullet_points_only</format>
  <required_sections>
    <section>Professional Identity</section>
    <section>Alignment Score + Confidence</section>
    <section>Top Strengths</section>
    <section>Critical Gaps</section>
    <section>Action Plan</section>
  </required_sections>
  <forbidden_patterns>
    <pattern>vague advice like "improve skills" without naming specific skills</pattern>
    <pattern>generic statements not tied to user's actual data</pattern>
    <pattern>recommendations without concrete next steps</pattern>
    <pattern>repeating the same action verb in multiple bullets</pattern>
    <pattern>speculation about why gaps exist</pattern>
  </forbidden_patterns>
  <required_elements>
    <element>Name current role and company</element>
    <element>Cite at least 3 specific strengths with evidence</element>
    <element>Name at least 3 critical gaps with specifics</element>
    <element>Alignment Score AND Confidence Score (e.g., "75/100, Confidence: 80/100")</element>
    <element>Explicitly state what data is missing for 100% confidence</element>
    <element>If CliftonStrengths exists: name specific themes and income applications</element>
    <element>Action plan with dual ranking: Income Impact + Sovereignty Score (3-5 items)</element>
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
- **Sovereignty Check**: Limited public proof — no OSS contributions, no blog posts, no talks. All achievements are company-locked.
- CliftonStrengths: Strategic + Analytical = natural systems thinker who sees architectural patterns

### Alignment Score: 58/100 (Confidence: 70/100)
Claims distributed systems specialization but has no evidence of large-scale architecture (no multi-region, no high-availability design, no performance optimization at scale).
**Missing for 100% confidence**: Recent backend repos, public architecture docs, evidence of cross-team technical leadership.

### Top Strengths (leverage for higher income)
- **Full-stack ownership**: Built and deployed complete systems (React + Node.js + AWS) — rare T-shaped skill set. **Sovereignty: 40/100** (company-locked, not portable)
- **Strategic thinking**: CliftonStrengths Strategic theme enables seeing 2-3 moves ahead — valuable for architecture roles. **Income potential**: €10k-€20k consulting premium
- **Learning agility**: Learner theme + 4 years of rapid skill acquisition — can ramp on new technologies quickly. **Sovereignty: 80/100** (portable skill)
- **Startup experience**: Wore multiple hats, made tradeoff decisions — prepares you for senior roles at scale-up companies

### Critical Gaps (fixing these unlocks higher income)
- **Distributed systems depth**: No evidence of multi-region deployments, eventual consistency patterns, or high-availability architecture
- **Technical leadership**: No blog posts, talks, or open source contributions — invisible to the market. **Sovereignty Gap**: Your code is locked inside the company
- **Scale experience**: Systems built serve 10k users, not 1M+ — Staff roles require proving impact at scale
- **GitHub presence**: 3 repos with minimal activity — recruiters use GitHub as proof of passion and skills

### Action Plan (ranked by Income + Sovereignty)
1. **Lead architecture design for high-traffic feature** (next 90 days) — closes distributed systems gap; document decisions and tradeoffs. **Income: €15k-€25k promotion impact, Sovereignty: 60/100** (internal but documentable)
2. **Start technical blog** (next 60 days, then monthly) — write about startup engineering challenges; establishes thought leadership. **Income: €5k-€10k consulting premium, Sovereignty: 90/100** (public, portable reputation)
3. **Contribute to one distributed systems OSS project** (3-6 months) — Cassandra, Kafka, or etcd; demonstrates production-level systems skills. **Income: €10k-€15k market premium, Sovereignty: 100/100** (global commons contribution)
4. **Speak at local meetup** (6 months) — present "Scaling from 0 to 10k Users"; builds reputation and network. **Income: €5k consulting leads, Sovereignty: 85/100**
5. **Build side project with real users** (ongoing) — aim for 1k+ users; proves you can ship and iterate independently. **Income: €1k-€5k MRR potential, Sovereignty: 100/100** (you own it)
</output>
</example>
</examples>

Analyze the following professional data. Base analysis only on provided data — never speculate.

<output_format>
### Professional Identity
- Current role and company
- 2-3 standout differentiators (name specific skills, credentials, or experiences)
- **Sovereignty Check**: Are achievements publicly verifiable or company-locked?

### Alignment Score: X/100 (Confidence: Y/100)
One sentence explaining the score, citing specific evidence.
**Missing for 100% confidence**: Name specific data points that would increase confidence (e.g., "missing recent backend repos, no public architecture docs").

### Top Strengths (leverage for higher income)
- [Strength]: [specific evidence from data]. **Income**: [€/$ range], **Sovereignty**: [0-100/100] (3-5 bullets)
- If CliftonStrengths data exists, dedicate 2-3 bullets to the specific themes — name them and explain how each one creates a competitive advantage or income opportunity
- Consider income potential beyond employment: freelancing, consulting, products, open source monetization, courses, content creation
- Consider networking and community: speaking, open source contributions, professional communities that lead to opportunities

### Critical Gaps (fixing these unlocks higher income)
- [Gap]: [what's missing and why it matters] (3-5 bullets)
- Name specific missing skills, certifications, portfolio pieces, or experience types
- Include gaps in visibility/networking if the data shows limited public presence
- **Cross-reference check**: If GitHub repos contradict a claimed gap, declare it FALSE and name the repo

### Action Plan (ranked by Income + Sovereignty)
1. [Specific action] — closes [specific gap] by [concrete step]. **Income**: [€/$ range or % impact], **Sovereignty**: [0-100/100]. Example: "Add README + demo to FutureProof repo" not "improve documentation".
2. [Specific action] — leverages [specific strength]. **Income**: [range], **Sovereignty**: [score].
3. [Specific action] — addresses [specific weakness]. **Income**: [range], **Sovereignty**: [score].
(3-5 items max. Each must reference a finding above by name. Consider both employment and non-employment income paths.)
</output_format>
