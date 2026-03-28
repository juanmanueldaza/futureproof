<instructions>
Identify gaps between stated career goals and actual professional activities using this step-by-step process:

**Step 1: Extract stated goals**
- List all explicit career goals from the user's profile, target roles, or search queries
- Note implicit goals from skills listed, projects started, or courses taken
- Categorize goals: role transition, skill development, income growth, location change

**Step 2: Inventory demonstrated skills and experience**
- Review experience section for each skill mentioned in goals
- Check projects, certifications, assessments, and GitHub/GitLab for evidence
- Create two lists: (a) skills mentioned AND demonstrated, (b) skills mentioned but NOT demonstrated
- **Sovereignty Check**: Mark which demonstrated skills are publicly verifiable (OSS, public repos) vs company-locked

**Step 3: Calculate alignment score with confidence metric**
- For each goal: count demonstrated skills / required skills
- Weight by importance: core skills 2x, nice-to-have 1x
- Compute weighted average as Alignment Score
- **Confidence Score**: Y/100 — if evidence is sparse, note uncertainty: "Confidence: 50/100 — only 1 of 5 claimed skills has public proof"
- Explicitly state what data is missing for 100% confidence

**Step 4: Identify active strengths**
- Name skills with clear evidence (project name, role, contribution, technology)
- If CliftonStrengths data exists, name themes that amplify these strengths
- Prioritize strengths that directly support stated goals
- **Sovereignty Score**: Rate each strength 0-100 based on portability (public > private)

**Step 5: Identify gaps (stated but not demonstrated)**
- For each gap: name what's claimed and where it's absent
- Be specific: "No Python ML projects despite listing ML in skills" not "limited ML experience"
- Include visibility/networking gaps: limited public presence, no speaking, no community contributions
- **Cross-reference with GitHub**: If a repo contradicts a claimed gap, declare it FALSE

**Step 6: Generate top 3 actions with dual metrics**
- For each action: name the specific gap it closes or strength it builds on
- Actions must be concrete (what, when, how) not vague advice
- **Dual Ranking**: Rank by both Goal Impact (how much it advances the stated goal) AND Sovereignty Score (0-100)
- **Cold Start Protocol**: If no repos are found after Step 3, pivot from "Analysis" to "Infrastructure Building" — generate a "Day 0" project blueprint naming specific technologies and README structure
</instructions>

<constraints>
  <max_words>600</max_words>
  <format>bullet_points_only</format>
  <required_sections>
    <section>Alignment Score + Confidence</section>
    <section>Active Strengths</section>
    <section>Gaps</section>
    <section>Top 3 Actions</section>
  </required_sections>
  <forbidden_patterns>
    <pattern>vague statements like "build more projects" without naming specific project types</pattern>
    <pattern>generic advice not tied to user's actual goals</pattern>
    <pattern>speculation about why gaps exist</pattern>
    <pattern>recommending proprietary certifications as primary path</pattern>
  </forbidden_patterns>
  <required_elements>
    <element>Alignment Score AND Confidence Score with specific evidence</element>
    <element>At least 3 active strengths with project/evidence names + Sovereignty Score</element>
    <element>At least 3 gaps with specific missing demonstrations</element>
    <element>If CliftonStrengths exists: name themes that amplify strengths</element>
    <element>3 concrete actions ranked by Goal Impact + Sovereignty Score</element>
    <element>Explicitly state what data is missing for 100% confidence</element>
  </required_elements>
</constraints>

<examples>
<example>
<input>
User goal: "Become a Staff Engineer specializing in AI/ML"
Career data: 5 years backend development, 2 ML courses completed, 0 ML projects in portfolio, GitHub has 8 repos (all backend/DevOps tools)
</input>

<output>
### Alignment Score: 45/100 (Confidence: 80/100)
Claims AI/ML specialization but has zero production ML projects — only coursework without applied work.
**Missing for 100% confidence**: Evidence of ML model deployment, MLOps practices, or production ML system design.

### Active Strengths (demonstrated in practice)
- **Backend engineering**: 5 years building distributed systems at scale (Company X, Project Y serving 10k+ users). **Sovereignty: 30/100** (company-locked)
- **Learning agility**: Completed 2 ML courses while working full-time — shows commitment to transition. **Sovereignty: 70/100** (portable skill)
- **DevOps expertise**: 8 GitHub repos demonstrating infrastructure automation, CI/CD pipelines. **Sovereignty: 85/100** (public proof)

### Gaps (stated but not demonstrated)
- **ML portfolio**: Claims "AI/ML specialist" but no public ML projects, Kaggle competitions, or research contributions
- **Production ML experience**: No evidence of deploying ML models to production, training pipelines, or MLOps practices
- **ML network**: No contributions to ML communities, no following of ML researchers, no conference attendance

### Top 3 Actions (ranked by Goal Impact + Sovereignty)
1. **Build and deploy one end-to-end ML project** (next 60 days) — closes portfolio gap; use your backend skills to productionize a model (e.g., RAG chatbot, image classifier). **Goal Impact: 90/100, Sovereignty: 100/100**
2. **Contribute to open-source ML library** (3 months) — LangChain, Hugging Face, or LlamaIndex; demonstrates production ML skills and builds network. **Goal Impact: 85/100, Sovereignty: 100/100**
3. **Write technical blog post explaining ML concept** (next 30 days) — establishes thought leadership; connect ML to your backend expertise (e.g., "Deploying LLMs at Scale"). **Goal Impact: 70/100, Sovereignty: 90/100**
</output>
</example>

<example>
<input>
User goal: "Transition from frontend to full-stack developer"
Career data: 3 years React/Vue development, 1 Node.js microservice project, no database experience, GitHub shows 12 frontend projects
</input>

<output>
### Alignment Score: 62/100 (Confidence: 90/100)
Strong frontend foundation with initial backend exposure, but lacks database and API design experience critical for full-stack roles.
**Missing for 100% confidence**: Evidence of database schema design, complex SQL queries, or backend deployment.

### Active Strengths (demonstrated in practice)
- **Frontend expertise**: 3 years building complex SPAs with React and Vue (12 GitHub projects demonstrating component architecture, state management). **Sovereignty: 90/100** (public portfolio)
- **Backend initiative**: Built one Node.js microservice independently — shows proactive learning. **Sovereignty: 80/100** (public repo)
- **Modern stack knowledge**: Experience with Pinia, Vue 3, TypeScript — current and marketable. **Sovereignty: 85/100**

### Gaps (stated but not demonstrated)
- **Database experience**: No SQL or NoSQL database projects despite full-stack claims — no schema design, queries, or optimization
- **API design**: Limited evidence of RESTful or GraphQL API architecture beyond the one microservice
- **Backend deployment**: No evidence of deploying backend services (Docker, Kubernetes, cloud platforms)

### Top 3 Actions (ranked by Goal Impact + Sovereignty)
1. **Build full-stack project with PostgreSQL backend** (next 60 days) — closes database gap; design schema, write queries, implement ORM. **Goal Impact: 95/100, Sovereignty: 100/100**
2. **Design and document REST API for existing frontend project** (next 30 days) — demonstrates API skills; use OpenAPI/Swagger for documentation. **Goal Impact: 85/100, Sovereignty: 90/100**
3. **Complete backend-focused course** (next 45 days) — "Node.js Design Patterns" or "Database Systems"; formalizes backend knowledge with credential. **Goal Impact: 70/100, Sovereignty: 60/100** (certification less valuable than public project)
</output>
</example>

<example>
<input>
User goal: "Become a Staff Engineer"
Career data: 5 years backend, GitHub shows 0 repos after tool discovery
</input>

<output>
### Alignment Score: 35/100 (Confidence: 40/100)
Claims Staff-level trajectory but has zero public proof of skill — no repos, no architecture docs, no technical leadership evidence.
**Missing for 100% confidence**: All data — no GitHub presence, no portfolio, no public technical artifacts.

### Active Strengths (demonstrated in practice)
- **Backend engineering**: 5 years experience (company-locked, no public proof). **Sovereignty: 10/100**
- **Learning agility**: Expressed interest in growth (self-reported). **Sovereignty: 50/100**

### Gaps (stated but not demonstrated)
- **Public portfolio**: Zero GitHub/GitLab presence — recruiters cannot verify skills
- **Technical leadership**: No blog posts, talks, or open source contributions
- **Architecture proof**: No system design documentation, no tradeoff analysis

### Top 3 Actions (Cold Start Protocol — Day 0 Blueprint)
1. **Create GitHub account and initialize first repo** (today) — name it "production-grade-[your-stack]-starter"; add README with: project description, tech stack, architecture diagram placeholder, "Getting Started" section. **Goal Impact: 100/100, Sovereignty: 100/100**
2. **Build SaaS boilerplate** (next 45 days) — Tech: Next.js 14, PostgreSQL (Supabase), Stripe, Tailwind. Features: auth, subscription tiers, dashboard. Deploy to Vercel + Supabase (free tiers). **Goal Impact: 95/100, Sovereignty: 100/100**
3. **Document one architecture decision from work** (next 30 days, anonymized) — Write "Why We Chose X Over Y" post; publish on Dev.to or Hashnode. **Goal Impact: 80/100, Sovereignty: 90/100**
</output>
</example>
</examples>

<input>
<career_data>
{career_data}
</career_data>
</input>

<output_format>
### Alignment Score: X/100 (Confidence: Y/100)
One sentence with specific evidence.
**Missing for 100% confidence**: Name specific data points.

### Active Strengths (demonstrated in practice)
- [Skill/tech]: [evidence — project name, role, contribution]. **Sovereignty**: [0-100/100] (3-5 bullets)
- If CliftonStrengths data exists, name the themes that amplify these strengths

### Gaps (stated but not demonstrated)
- [Gap]: [claimed in X but absent from Y] (3-5 bullets)
- Be specific: "No Python ML projects despite listing ML in skills" not "limited ML experience"
- Include visibility/networking gaps: limited public presence, no speaking, no community contributions
- **Cross-reference check**: If GitHub repos contradict a claimed gap, declare it FALSE and name the repo

### Top 3 Actions (ranked by Goal Impact + Sovereignty)
1. [Action] — closes gap in [specific skill/area]. **Goal Impact**: [0-100], **Sovereignty**: [0-100]. Concrete step, not vague advice.
2. [Action] — builds on [specific existing strength/project]. **Goal Impact**: [0-100], **Sovereignty**: [0-100].
3. [Action] — addresses [specific missing portfolio piece or credential]. **Goal Impact**: [0-100], **Sovereignty**: [0-100].
</output_format>
