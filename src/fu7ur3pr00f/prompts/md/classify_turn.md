You are analyzing a user's query in the context of an ongoing career conversation.

Determine the **type** of turn:
1. **factual** — Simple factual question about current status (e.g., "what is my job title?", "how many skills do I have?")
2. **follow_up** — References or deepens something from prior turns (e.g., "tell me more about that", "go deeper on the learning path")
3. **steer** — Redirects focus mid-session (e.g., "focus more on remote roles", "skip the founder aspect")
4. **workflow_step** — References an active multi-step goal (e.g., "next step in my plan" when a goal is being tracked)
5. **new_query** — Fresh topic or ambiguous

**Conversation history** (last 3 turns):
{conversation_summary}

**Current query**: {query}

**Active goals** (if any): {active_goals}

Respond with ONLY the type keyword: factual | follow_up | steer | workflow_step | new_query

Reasoning (one line): ...
