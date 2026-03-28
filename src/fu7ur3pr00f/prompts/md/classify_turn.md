You are analyzing a user's query in the context of an ongoing career conversation.

Determine the **type** of turn:
1. **factual** — Simple standalone factual question with no dependency on prior turns (e.g., "what is my job title?", "how many skills do I have?")
2. **follow_up** — Continues, affirms, or deepens the prior exchange. This includes: short affirmations ("yes", "ok", "sure", "proceed", "go ahead"), requests for more detail ("tell me more", "go deeper"), and any query that only makes sense in the context of what the agent just said or asked.
3. **steer** — Redirects focus mid-session (e.g., "focus more on remote roles", "skip the founder aspect")
4. **workflow_step** — References an active multi-step goal (e.g., "next step in my plan" when a goal is being tracked)
5. **new_query** — Fresh topic unrelated to the previous exchange

**Key rule**: If the agent's last message ended with a question, and the user's current message is a short affirmation or direct answer to that question, classify as **follow_up** — NOT factual.

**Conversation history** (last 3 turns):
{conversation_summary}

**Current query**: {query}

**Active goals** (if any): {active_goals}

Respond with ONLY the type keyword: factual | follow_up | steer | workflow_step | new_query

Reasoning (one line): ...
