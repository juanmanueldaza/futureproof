# FutureProof Product Direction

## Product Philosophy

FutureProof is a **free, local-first** career intelligence tool. All data stays on the user's machine — ChromaDB, SQLite conversations, YAML profile, generated CVs. It is not a SaaS. Not a hosted platform. A tool you install and own.

All tools, all analysis workflows, CV generation — free with no gates. The only variable cost is LLM compute, which users control: use the FutureProof proxy (default), bring your own API keys, or run local models with Ollama.

---

## Architecture Overview

The core architecture is unchanged. Multi-provider LLM support is fully implemented.

```
CLI (Typer)
  └─ Chat Client (prompt_toolkit, Rich UI, streaming)
       └─ LangGraph Agent (create_agent, 41 tools, 4 middlewares)
            ├─ Multi-Provider LLM (FutureProof proxy / BYOK / Ollama)
            ├─ ChromaDB PersistentClient (~/.futureproof/episodic/)
            ├─ SqliteSaver checkpointer (~/.futureproof/memory.db)
            ├─ Profile YAML (~/.futureproof/profile.yaml)
            ├─ MCP Clients (13: GitHub, Tavily, job boards, HN, financial, content)
            └─ Services (KnowledgeService, GathererService, AnalysisService)
```

Everything local. The only network calls are to the LLM provider (whichever the user chose) and external data APIs (GitHub, job boards, market data).

---

## Multi-Provider LLM Support

Users shouldn't be locked to Azure OpenAI. FutureProof supports multiple LLM providers, prioritized for zero-friction onboarding:

| Priority | Provider | Setup | Cost |
|----------|----------|-------|------|
| 1 (default) | **FutureProof proxy** | Zero config — free starter tokens on signup | API cost + ~10% markup |
| 2 | **BYOK cloud** — OpenAI, Anthropic, Google, Azure | User provides API keys in `.env` | User pays provider directly |
| 3 | **Ollama** (local) | Install Ollama, pull a model | Free, offline, private |

Multi-provider LLM support is implemented in `src/futureproof/llm/fallback.py` and `src/futureproof/config.py`.

---

## Monetization: FutureProof LLM Proxy

> **Status: Planned** — The proxy is not yet operational. The sections below describe the target experience.

### The Model

Following Zed Editor and Warp Terminal: free tool with hosted LLM compute as the **default** experience.

**New users will get free starter tokens** — enough for several career analysis sessions. Once published to PyPI, `pip install futureproof` will work immediately with no API key setup or provider configuration, eliminating onboarding friction entirely.

**After free tokens**: pay-as-you-go at API cost + ~10% markup, or switch to BYOK/Ollama at any time. No lock-in.

### Pricing

- **Token-based, transparent.** Users see what they consume.
- **~10% markup** over provider API cost. Covers proxy infrastructure + rate limit management.
- No subscriptions, no credit pools, no sticker shock.

### Why This Works (and Where It Doesn't)

The proxy's real value is **zero-config onboarding** — the same reason Zed and Warp offer hosted compute. Users who want control switch to BYOK or Ollama. Users who want convenience stay on the proxy.

**Honest acknowledgment**: LLM compute is a commodity with thin margins. No local-first tool successfully sells ONLY LLM compute at scale. The proxy may not be a sustainable sole revenue source. Future monetization paths (team features, premium gatherers, enterprise support) may evolve based on validated demand — but we don't spec those now.

### Infrastructure

The proxy is the **only** cloud infrastructure FutureProof operates:

| Component | Purpose | Est. Cost |
|-----------|---------|-----------|
| LiteLLM proxy container | Multi-model routing, token metering, rate limiting | ~$40-70/mo |
| Redis | Rate limit state, caching | ~$10-15/mo |
| Domain + SSL | futureproof.dev | ~$1/mo |
| **Total** | | **~$50-85/mo** |

No PostgreSQL. No Qdrant. No user database. No OAuth server. Auth is a simple API key issued at signup.

### Break-Even

At 10% markup, break-even requires ~$500-850/month in proxied LLM usage. With moderate users consuming ~$0.44/month in LLM costs, that's ~50-85 active proxy users.

---

## LLM Cost Estimates

### Model Pricing (Azure OpenAI / OpenAI, March 2026)

| Model | Input / 1M tokens | Output / 1M tokens | Role in FutureProof |
|-------|-------------------|--------------------|--------------------|
| GPT-5 Mini | $0.25 | $2.00 | Agent (tool calling) |
| GPT-4.1 | $2.00 | $8.00 | Analysis, CV generation |
| GPT-4o | $2.50 | $10.00 | Fallback |
| GPT-4.1 Mini | $0.40 | $1.60 | Fallback |
| GPT-4o Mini | $0.15 | $0.60 | Summarization |
| o4-mini | $1.10 | $4.40 | Synthesis (reasoning) |
| text-embedding-3-small | $0.02 | N/A | Vector embeddings |

### Per-Session Costs

| Session Type | Est. Cost | Primary Models |
|-------------|-----------|----------------|
| Quick question (2-3 turns) | $0.01 | GPT-5 Mini |
| Career analysis (full workflow) | $0.16-0.20 | GPT-5 Mini + GPT-4.1 + o4-mini |
| CV generation (with HITL) | $0.10-0.20 | GPT-5 Mini + GPT-4.1 |
| Data gathering + indexing | $0.02 | GPT-5 Mini |

### Monthly Cost by User Archetype

| Archetype | Sessions/Mo | Analyses | CVs | Est. LLM Cost |
|-----------|------------|----------|-----|---------------|
| Light (quick questions) | 5 | 0 | 0 | $0.05 |
| Moderate (regular) | 15 | 1 | 0.5 | $0.44 |
| Power (career mover) | 30 | 3 | 2 | $1.03 |
| Heavy (daily + analyses) | 60 | 5 | 3 | $4.50 |

Career analysis is episodic, not continuous. Unlike coding assistants (Cursor users write code all day), career analysis happens in bursts. Even heavy users consume <$5/month in LLM costs.

### o4-mini Reasoning Token Warning

o4-mini generates internal "reasoning tokens" billed as output but invisible in API responses. A 500-token visible response may consume 2,000+ total output tokens. Monitor actual consumption post-launch; fall back to GPT-4.1 for synthesis if costs exceed projections.

---

## License Strategy

**Current license**: GPL-2.0 (confirmed in `pyproject.toml` and `LICENSE`).

**Why GPL-2.0 works for local-first + proxy**:
- CLI is GPL-2.0: forks must stay GPL. Protects the open-source core.
- The proxy is a separate service (LiteLLM config + metering), not a derivative work of the GPL code.
- The "SaaS loophole" (GPL-2.0 doesn't require source disclosure for server-side use) is irrelevant here — FutureProof IS the local tool. A competitor hosting it as SaaS would defeat the "your data stays local" value prop, which is natural market protection.
- All current dependencies are GPL-2.0 compatible (LangChain: MIT, ChromaDB: Apache-2.0, LiteLLM: MIT, Typer: MIT).

**When to reconsider**: If substantial server-side code is added beyond the LiteLLM proxy config, consider AGPL-3.0 for those components (the Grafana pattern: GPL for core, AGPL for server). Not needed now.

---

## What Was Deleted and Why

This document replaces 4 previous plan documents that described a CLI-to-SaaS transition architecture. That direction has been abandoned in favor of local-first + LLM proxy.

| Deleted Document | What It Contained | Why Deleted |
|------------------|-------------------|-------------|
| `architecture-research.md` | SaaS infra research: multi-tenant RAG (Qdrant/Pinecone), CLI auth flows (OAuth Device Code), Stripe billing, LinkedIn event-driven architecture | SaaS infrastructure is not being built. Relevant BYOK/proxy research folded into this document. |
| `product-architecture.md` | CLI-to-SaaS architecture: StorageBackend protocol, CloudBackend, FastAPI server, Qdrant, PostgreSQL, S3, Redis, OAuth, Stripe, phased migration plan | Entirely obsolete. The "target architecture" was a hosted platform — we're not building that. |
| `design-doc.md` | Formal design doc for the SaaS transition | 80% duplicate of product-architecture.md. Unique sections (Alternatives Considered, Cross-Cutting Concerns) salvaged below. |
| `cost-research.md` | LLM cost estimates + SaaS infrastructure costs (Railway, Render, Qdrant Cloud, PostgreSQL, Redis, Stripe fees) | LLM cost data moved to this document. SaaS infrastructure costs irrelevant. |

---

## Alternatives Considered

### SaaS transition with hosted infrastructure
CloudBackend, FastAPI server, PostgreSQL, Qdrant, Redis, OAuth, Stripe billing. **Rejected**: unnecessary complexity (~$120-300/month infrastructure), contradicts local-first philosophy, introduces multi-tenant isolation concerns that don't exist when data is local.

### BYOK-first with proxy as optional add-on
Default to requiring users to configure their own API keys. **Rejected**: creates onboarding friction. Most users will bounce at "configure Azure OpenAI API key." Proxy-first with free starter tokens means `pip install futureproof` → works immediately (the Zed/Warp pattern).

### Credit pool / subscription billing
$15/month for a credit pool of LLM usage. **Rejected**: pass-through + markup is simpler, more honest, and avoids the sticker shock that caused Cursor's backlash. Users see exactly what they consume.

### Multi-agent architecture
Split 41 tools across specialized agents with a router. **Rejected**: the single-agent with middleware stack already works. Multi-agent adds latency and handoff complexity for no proven benefit.
