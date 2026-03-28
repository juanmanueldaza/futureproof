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

**Step 3: Calculate alignment score**
- For each goal: count demonstrated skills / required skills
- Weight by importance: core skills 2x, nice-to-have 1x
- Compute weighted average as Alignment Score
- If evidence is sparse, note uncertainty: "Based on limited data, approximately X/100"

**Step 4: Identify active strengths**
- Name skills with clear evidence (project name, role, contribution, technology)
- If CliftonStrengths data exists, name themes that amplify these strengths
- Prioritize strengths that directly support stated goals

**Step 5: Identify gaps (stated but not demonstrated)**
- For each gap: name what's claimed and where it's absent
- Be specific: "No Python ML projects despite listing ML in skills" not "limited ML experience"
- Include visibility/networking gaps: limited public presence, no speaking, no community contributions

**Step 6: Generate top 3 actions**
- For each action: name the specific gap it closes or strength it builds on
- Actions must be concrete (what, when, how) not vague advice
- Rank by impact on the primary stated goal
</instructions>

<constraints>
  <max_words>600</max_words>
  <format>bullet_points_only</format>
  <required_sections>
    <section>Alignment Score</section>
    <section>Active Strengths</section>
    <section>Gaps</section>
    <section>Top 3 Actions</section>
  </required_sections>
  <forbidden_patterns>
    <pattern>vague statements like "build more projects" without naming specific project types</pattern>
    <pattern>generic advice not tied to user's actual goals</pattern>
    <pattern>speculation about why gaps exist</pattern>
  </forbidden_patterns>
  <required_elements>
    <element>Alignment Score with specific evidence</element>
    <element>At least 3 active strengths with project/evidence names</element>
    <element>At least 3 gaps with specific missing demonstrations</element>
    <element>If CliftonStrengths exists: name themes that amplify strengths</element>
    <element>3 concrete actions ranked by impact</element>
  </required_elements>
</constraints>

<examples>
<example>
<input>
User goal: "Become a Staff Engineer specializing in AI/ML"
Career data: 5 years backend development, 2 ML courses completed, 0 ML projects in portfolio, GitHub has 8 repos (all backend/DevOps tools)
</input>

<output>
### Alignment Score: 45/100
Claims AI/ML specialization but has zero production ML projects — only coursework without applied work.

### Active Strengths (demonstrated in practice)
- **Backend engineering**: 5 years building distributed systems at scale (Company X, Project Y serving 10k+ users)
- **Learning agility**: Completed 2 ML courses while working full-time — shows commitment to transition
- **DevOps expertise**: 8 GitHub repos demonstrating infrastructure automation, CI/CD pipelines

### Gaps (stated but not demonstrated)
- **ML portfolio**: Claims "AI/ML specialist" but no public ML projects, Kaggle competitions, or research contributions
- **Production ML experience**: No evidence of deploying ML models to production, training pipelines, or MLOps practices
- **ML network**: No contributions to ML communities, no following of ML researchers, no conference attendance

### Top 3 Actions (ranked by impact)
1. **Build and deploy one end-to-end ML project** (next 60 days) — closes portfolio gap; use your backend skills to productionize a model (e.g., RAG chatbot, image classifier)
2. **Contribute to open-source ML library** (3 months) — LangChain, Hugging Face, or LlamaIndex; demonstrates production ML skills and builds network
3. **Write technical blog post explaining ML concept** (next 30 days) — establishes thought leadership; connect ML to your backend expertise (e.g., "Deploying LLMs at Scale")
</output>
</example>

<example>
<input>
User goal: "Transition from frontend to full-stack developer"
Career data: 3 years React/Vue development, 1 Node.js microservice project, no database experience, GitHub shows 12 frontend projects
</input>

<output>
### Alignment Score: 62/100
Strong frontend foundation with initial backend exposure, but lacks database and API design experience critical for full-stack roles.

### Active Strengths (demonstrated in practice)
- **Frontend expertise**: 3 years building complex SPAs with React and Vue (12 GitHub projects demonstrating component architecture, state management)
- **Backend initiative**: Built one Node.js microservice independently — shows proactive learning
- **Modern stack knowledge**: Experience with Pinia, Vue 3, TypeScript — current and marketable

### Gaps (stated but not demonstrated)
- **Database experience**: No SQL or NoSQL database projects despite full-stack claims — no schema design, queries, or optimization
- **API design**: Limited evidence of RESTful or GraphQL API architecture beyond the one microservice
- **Backend deployment**: No evidence of deploying backend services (Docker, Kubernetes, cloud platforms)

### Top 3 Actions (ranked by impact)
1. **Build full-stack project with PostgreSQL backend** (next 60 days) — closes database gap; design schema, write queries, implement ORM
2. **Design and document REST API for existing frontend project** (next 30 days) — demonstrates API skills; use OpenAPI/Swagger for documentation
3. **Complete backend-focused course** (next 45 days) — "Node.js Design Patterns" or "Database Systems"; formalizes backend knowledge with credential
</output>
</example>
</examples>

<input>
<career_data>
{career_data}
</career_data>
</input>

<output_format>
### Alignment Score: X/100
One sentence with specific evidence (e.g., "68/100 — claims Agentic AI specialist but no public agentic AI projects in repos").

### Active Strengths (demonstrated in practice)
- [Skill/tech]: [evidence — project name, role, contribution] (3-5 bullets)
- If CliftonStrengths data exists, name the themes that amplify these strengths

### Gaps (stated but not demonstrated)
- [Gap]: [claimed in X but absent from Y] (3-5 bullets)
- Be specific: "No Python ML projects despite listing ML in skills" not "limited ML experience"
- Include visibility/networking gaps: limited public presence, no speaking, no community contributions

### Top 3 Actions (ranked by impact)
1. [Action] — closes gap in [specific skill/area]. Concrete step, not vague advice.
2. [Action] — builds on [specific existing strength/project].
3. [Action] — addresses [specific missing portfolio piece or credential].
</output_format>
