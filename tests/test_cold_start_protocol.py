"""Tests for Cold Start Protocol.

Day 0 blueprint generation when no GitHub/repos exist.
"""

from fu7ur3pr00f.prompts.loader import load_prompt


class TestColdStartProtocol:
    """Tests for Cold Start Protocol in specialist_code.md prompt."""

    def test_cold_start_protocol_exists_in_code_specialist(self):
        """Verify Cold Start Protocol is defined in code specialist prompt."""
        content = load_prompt("specialist_code")
        assert "Cold Start Protocol" in content
        assert "Day 0" in content or "Day-0" in content
        assert "no GitHub" in content.lower() or "no repos" in content.lower()

    def test_cold_start_provides_specific_tech_stack(self):
        """Cold Start Protocol must name specific technologies, not generic advice."""
        content = load_prompt("specialist_code")
        # Should mention specific tech for Day 0 blueprint
        assert any(
            tech in content
            for tech in [
                "Next.js",
                "PostgreSQL",
                "React",
                "Node.js",
                "TypeScript",
                "Tailwind",
                "Vercel",
                "Supabase",
            ]
        )

    def test_cold_start_provides_readme_structure(self):
        """Cold Start Protocol must include README structure guidance."""
        content = load_prompt("specialist_code")
        assert "README" in content
        # Should mention structure elements
        assert any(
            element in content.lower()
            for element in [
                "description",
                "architecture",
                "diagram",
                "structure",
                "blueprint",
            ]
        )

    def test_cold_start_provides_deployment_target(self):
        """Cold Start Protocol must name specific deployment targets."""
        content = load_prompt("specialist_code")
        # Should mention deployment platforms
        assert any(
            platform in content
            for platform in [
                "Vercel",
                "Netlify",
                "Railway",
                "Render",
                "Hugging Face",
                "AWS",
            ]
        )

    def test_cold_start_in_analyze_gaps(self):
        """Cold Start Protocol should also be referenced in analyze_gaps prompt."""
        content = load_prompt("analyze_gaps")
        assert (
            "Cold Start" in content
            or "Day 0" in content
            or "blueprint" in content.lower()
        )

    def test_cold_start_provides_timeline(self):
        """Cold Start Protocol must include concrete timelines."""
        content = load_prompt("specialist_code")
        # Should mention specific timelines (days/weeks)
        assert any(
            timeline in content
            for timeline in ["30 days", "45 days", "60 days", "next ", "weeks", "month"]
        )


class TestColdStartOutputFormat:
    """Tests validating Cold Start Protocol output format."""

    def test_code_specialist_has_cold_start_output_format(self):
        """Verify code specialist output format includes Cold Start section."""
        content = load_prompt("specialist_code")
        assert "output_format" in content.lower() or "Output Format" in content
        # Should have section for Cold Start in output
        assert "Cold Start" in content or "Portfolio Audit" in content

    def test_cold_start_has_sovereignty_score(self):
        """Cold Start Protocol outputs should include Sovereignty Score."""
        content = load_prompt("specialist_code")
        assert "Sovereignty Score" in content or "Sovereignty:" in content

    def test_cold_start_has_income_impact(self):
        """Cold Start Protocol outputs should include Income Impact metric."""
        content = load_prompt("specialist_code")
        assert "Income Impact" in content or "Income:" in content


class TestColdStartBehavioralRules:
    """Tests for Cold Start behavioral rules in prompts."""

    def test_code_specialist_has_cold_start_rule(self):
        """Verify behavioral rule for Cold Start exists."""
        content = load_prompt("specialist_code")
        assert "Cold Start" in content
        # Should have a rule about activating Cold Start when no repos found
        assert any(
            rule in content.lower()
            for rule in [
                "if no github",
                "if no repos",
                "if user has no github",
                "no github presence",
                "starting from zero",
            ]
        )

    def test_cold_start_not_generic_advice(self):
        """Cold Start Protocol must NOT provide generic advice."""
        content = load_prompt("specialist_code")
        # Should explicitly forbid generic advice
        assert "generic" in content.lower() or "specific" in content.lower()
        # Should emphasize concrete blueprints
        assert "blueprint" in content.lower() or "concrete" in content.lower()


class TestAnalyzeGapsColdStart:
    """Tests for Cold Start Protocol in analyze_gaps.md."""

    def test_analyze_gaps_has_cold_start_step(self):
        """Verify analyze_gaps includes Cold Start Protocol step."""
        content = load_prompt("analyze_gaps")
        assert "Cold Start" in content

    def test_analyze_gaps_cold_start_provides_blueprint(self):
        """Cold Start in analyze_gaps must provide Day 0 blueprint."""
        content = load_prompt("analyze_gaps")
        # Should mention blueprint or specific project recommendations
        assert any(
            term in content.lower()
            for term in ["blueprint", "day 0", "first project", "create github"]
        )

    def test_analyze_gaps_cold_start_has_dual_metrics(self):
        """Cold Start actions should have Goal Impact + Sovereignty scores."""
        content = load_prompt("analyze_gaps")
        assert "Goal Impact" in content
        assert "Sovereignty" in content


class TestSubstanceOverSyntax:
    """Tests for Substance-over-Syntax rule in generate_cv.md."""

    def test_substance_over_syntax_rule_exists(self):
        """Verify Substance-over-Syntax rule is defined in generate_cv prompt."""
        content = load_prompt("generate_cv")
        assert "Substance-over-Syntax" in content or "Substance over Syntax" in content

    def test_substance_over_syntax_requires_evidence(self):
        """Substance-over-Syntax must require evidence for claims."""
        content = load_prompt("generate_cv")
        assert "Signature Achievement" in content
        assert "backed by" in content.lower() or "evidence" in content.lower()

    def test_weak_vs_strong_examples_provided(self):
        """Prompt should provide examples of weak vs strong openers."""
        content = load_prompt("generate_cv")
        assert "Weak:" in content
        assert "Strong:" in content

    def test_banned_openers_mentioned(self):
        """Prompt should mention banned weak openers."""
        content = load_prompt("generate_cv")
        assert any(
            phrase in content
            for phrase in [
                "years of experience",
                "Results-driven",
                "Passionate about",
                "proven track record",
            ]
        )

    def test_xyz_formula_required(self):
        """CV bullets must follow XYZ formula."""
        content = load_prompt("generate_cv")
        assert "XYZ" in content
        assert "Accomplished" in content
        assert "measured by" in content

    def test_action_verb_rules_defined(self):
        """Prompt should define action verb rules."""
        content = load_prompt("generate_cv")
        assert "Action Verb" in content
        # Should list strong verbs
        assert any(
            verb in content
            for verb in ["Architected", "Shipped", "Drove", "Migrated", "Pioneered"]
        )


class TestDataFidelity:
    """Tests for data fidelity rules - preventing hallucination."""

    def test_synthesis_requires_github_data_for_repo_claims(self):
        """Synthesis prompt must forbid mentioning repo names without tool data."""
        content = load_prompt("synthesis")
        content_lower = content.lower()
        assert "data fidelity" in content_lower
        assert (
            "cannot mention specific repo names" in content_lower
            or "unless they appear" in content_lower
        )
        assert "do not invent" in content_lower or "never invent" in content_lower

    def test_blackboard_synthesis_has_data_fidelity_rule(self):
        """Blackboard synthesis must have data fidelity rule for GitHub."""
        content = load_prompt("blackboard_synthesis_system")
        content_lower = content.lower()
        assert "data fidelity" in content_lower
        assert "never invent" in content_lower or "do not invent" in content_lower

    def test_specialist_guidance_requires_github_fetch(self):
        """Specialist guidance must require GitHub fetch before repo claims."""
        content = load_prompt("specialist_guidance")
        content_lower = content.lower()
        assert (
            "github data fetch" in content_lower
            or "get_github_profile" in content_lower
        )
        assert (
            "cannot make claims about specific repos" in content_lower
            or "critical" in content_lower
        )
        assert "do not invent" in content_lower or "never invent" in content_lower
