"""Example: Using the Blackboard Pattern for Multi-Specialist Analysis.

This example demonstrates how to use the blackboard pattern to execute
a comprehensive 5-year career prediction with integrated analysis from
all 5 specialists (Coach, Learning, Code, Jobs, Founder).
"""

from fu7ur3pr00f.agents.specialists.orchestrator import get_orchestrator


def example_blackboard_execution():
    """Example: Execute a comprehensive career analysis using blackboard pattern."""

    # Get the orchestrator and create executor
    orchestrator = get_orchestrator()

    # User's query and profile
    query = (
        "I'm a Senior Engineer with 5 years of experience. "
        "What should my 5-year plan be?"
    )
    user_profile = {
        "role": "Senior Engineer",
        "company": "Tech Startup",
        "years_experience": 5,
        "skills": ["Python", "Go", "Kubernetes"],
        "strengths": ["Learner", "Problem Solver"],
        "goals": ["Advance to Staff role"],
    }

    # Create blackboard executor with iterative strategy
    executor = orchestrator.get_executor(strategy="linear_iterative", max_iterations=3)

    print("=" * 70)
    print("BLACKBOARD PATTERN: Multi-Specialist Career Analysis")
    print("=" * 70)
    print(f"Query: {query}")
    print(
        f"Profile: {user_profile['role']} with {user_profile['years_experience']} years"
    )
    print("=" * 70)
    print()

    # Counters for progress
    specialist_count = {"count": 0}
    finding_count = {"count": 0}

    def on_start(specialist_name: str):
        """Callback when a specialist starts."""
        specialist_count["count"] += 1
        print(
            f"[{specialist_count['count']:2d}] {specialist_name.upper():10s} "
            f"analyzing..."
        )

    def on_complete(specialist_name: str, finding: dict):
        """Callback when a specialist finishes."""
        finding_count["count"] += 1
        confidence = finding.get("confidence", 0.70)
        keys = ", ".join([k for k in finding.keys() if k != "confidence"])
        print(f"      → {len(keys)} findings (confidence: {confidence:.0%})")

    # Execute the blackboard
    print("Executing multi-specialist analysis...\n")
    blackboard = executor.execute(
        query=query,
        user_profile=user_profile,
        on_specialist_start=on_start,
        on_specialist_complete=on_complete,
    )

    # Display results
    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Specialists contributed: {len(blackboard['findings'])}")
    print(f"Total findings: {finding_count['count']}")
    print(f"Iterations completed: {blackboard['iteration'] + 1}")
    print()

    # Display integrated advice
    synthesis = blackboard.get("synthesis", {})
    integrated = synthesis.get("integrated_advice", {})

    if integrated:
        print("INTEGRATED ADVICE")
        print("-" * 70)
        print(f"Target Role:       {integrated.get('target_role', 'N/A')}")
        print(f"Timeline:          {integrated.get('timeline', 'N/A')}")
        print(f"Key Gaps:          {', '.join(integrated.get('key_gaps', []))}")
        print(f"Learning Plan:     {', '.join(integrated.get('learning_plan', []))}")
        print(f"Job Opportunities: {', '.join(integrated.get('opportunities', []))}")
        print()

    # Display change log (shows iterative refinement)
    if blackboard["change_log"]:
        print("SPECIALIST CONTRIBUTIONS (Audit Trail)")
        print("-" * 70)
        for entry in blackboard["change_log"]:
            iteration = entry.get("iteration", 0)
            specialist = entry.get("specialist", "unknown")
            confidence = entry.get("confidence", 0)
            keys_modified = entry.get("keys_modified", [])
            print(
                f"Iteration {iteration}: {specialist:10s} "
                f"({confidence:.0%} confidence, {len(keys_modified)} keys)"
            )
        print()

    # Display all findings by specialist
    print("SPECIALIST FINDINGS")
    print("-" * 70)
    for specialist, finding in blackboard.get("findings", {}).items():
        print(f"\n{specialist.upper()}:")
        for key, value in finding.items():
            if key not in ("confidence", "iteration_contributed"):
                print(f"  {key:20s}: {value}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    example_blackboard_execution()
