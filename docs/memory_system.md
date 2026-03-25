# Memory System

How FutureProof stores and retrieves data across two separate backends.

---

## Overview

FutureProof uses two distinct storage backends:

| Backend | File | Purpose |
|---------|------|---------|
| **SQLite** (`SqliteSaver`) | `~/.fu7ur3pr00f/memory.db` | Conversation checkpoints — per-thread message history, agent state, time-travel |
| **ChromaDB** | `~/.fu7ur3pr00f/episodic/` | Career knowledge base (RAG) and episodic memory (decisions, applications) |

These are completely separate. `/clear` clears SQLite conversation history. The knowledge base (ChromaDB) is cleared by telling the agent to clear it, which triggers a HITL confirmation.

---

## Conversation Checkpointing (SQLite)

Implemented via LangGraph's `SqliteSaver`:

- Stored at `~/.fu7ur3pr00f/memory.db`
- Persists message history across sessions (restart the app, conversation resumes)
- One row set per thread — use `/thread <name>` to isolate conversations
- Supports LangGraph time-travel and state inspection

### Thread Management

```bash
/thread            # Show current thread ID
/thread jobsearch  # Switch to a named thread
/threads           # List all threads with history
/clear             # Delete history for the current thread
```

---

## Career Knowledge Base (ChromaDB RAG)

When you run `/gather`, data is:

1. Parsed into sections (LinkedIn CSV, PDF text, HTML scrape, etc.)
2. Chunked into 50–500 token pieces with 50-token overlap
3. Embedded (vector representation)
4. Stored in ChromaDB at `~/.fu7ur3pr00f/episodic/`

The agent searches this knowledge base automatically before answering career questions.

### Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedding Model│  ← Converts query to vector
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChromaDB      │  ← Vector similarity search (cosine)
│  (episodic/)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Top-K Results  │  ← Most relevant chunks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM +         │  ← Generates response with context
│  Retrieved      │
│   Context       │
└─────────────────┘
```

### Indexed Sources

| Source | Sections |
|--------|----------|
| LinkedIn | Profile, Experience, Education, Skills, Certifications, Languages, Projects, Recommendations |
| GitHub | Repos, Contributions, Languages |
| GitLab | Projects, Merge Requests |
| CliftonStrengths | Top 5/10/34 strengths, insights, action items |
| CV/Resume | All detected sections |
| Portfolio | About, Projects, Blog posts |

### Chunking Strategy

- **Min tokens:** 50
- **Max tokens:** 500
- **Overlap:** 50 tokens
- **Boundary:** Paragraph/section breaks

---

## Episodic Memory

The agent can store and recall discrete memories: career decisions, job applications, and other events.

Tell the agent in natural language:

```
> remember that I accepted an offer at Company X for $180k
> remember I applied to Google for Senior SWE on March 15
> what job applications have I saved?
> recall decisions I've made in the last year
```

Episodic memories are stored in the same ChromaDB instance (`episodic/`) alongside career knowledge.

---

## Data Directory Structure

```
~/.fu7ur3pr00f/
├── .env                     # Configuration and secrets (0600)
├── memory.db                # SQLite — conversation checkpoints
├── profile.yaml             # User profile (name, role, skills, goals)
├── episodic/                # ChromaDB — career knowledge + episodic memory
│   ├── chroma.sqlite3       # ChromaDB metadata
│   └── *.bin                # Vector index files
└── data/
    ├── raw/                 # Place source data files here
    │   ├── linkedin.zip
    │   ├── *.pdf
    │   └── resume.md
    ├── processed/           # Intermediate processed data
    ├── output/              # Generated CVs
    │   ├── cv_en_ats.md
    │   └── cv_en_ats.pdf
    ├── cache/               # Market data cache
    └── fu7ur3pr00f.log      # Application log
```

---

## Embeddings

### Configuration

```bash
# In ~/.fu7ur3pr00f/.env
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI (default)
```

### Supported Models

| Provider | Model |
|----------|-------|
| OpenAI | `text-embedding-3-small`, `text-embedding-3-large` |
| Azure | `text-embedding-3-small` (via `AZURE_EMBEDDING_DEPLOYMENT`) |
| Ollama | `nomic-embed-text`, `mxbai-embed-large` |

### Vector Dimensions

| Model | Dimensions |
|-------|------------|
| text-embedding-3-small | 1536 |
| text-embedding-3-large | 3072 |
| nomic-embed-text | 768 |

---

## Knowledge Base Commands

Interact with the knowledge base via natural language or the agent tools directly:

```
> search my knowledge base for Python projects
> show me statistics about my indexed career data
> clear all career knowledge and start fresh
> what AWS experience do I have?
```

The `/memory` slash command only shows a brief overview (data directory, thread count, profile status). It does not support subcommands for search or clear.

---

## Troubleshooting

### No results from knowledge base

**Issue:** Agent says it has no data

**Solution:**
1. Run `/gather` to index data
2. Ask agent: *"show me knowledge base statistics"*
3. Verify files exist in `~/.fu7ur3pr00f/data/raw/`

### Database locked (SQLite)

**Error:** `Database is locked` or `OperationalError`

**Solution:**
```bash
# Close other instances of fu7ur3pr00f
# Remove lock files if present
rm -f ~/.fu7ur3pr00f/*.lock
```

### ChromaDB store reset

To fully wipe and rebuild the knowledge base:

```bash
rm -rf ~/.fu7ur3pr00f/episodic/
```

Then run `/gather` to re-index. The SQLite conversation history (`memory.db`) is unaffected.

### Embedding errors

**Error:** `Embedding failed`

**Solution:**
1. Verify embedding model is set in `.env`
2. Check LLM provider connectivity
3. Restart the application to reload embeddings

---

## Performance Tuning

### Chunk Size

```bash
# In ~/.fu7ur3pr00f/.env
KNOWLEDGE_CHUNK_MAX_TOKENS=500
KNOWLEDGE_CHUNK_MIN_TOKENS=50
```

- Smaller chunks: more precise retrieval, more items to search
- Larger chunks: more context per result, may include noise

### Auto-Indexing

```bash
# Auto-index after every gather (default: true)
KNOWLEDGE_AUTO_INDEX=true
```

---

## Data Privacy

- All data stored **locally** under `~/.fu7ur3pr00f/`
- No cloud sync
- Only the top 5–10 most relevant chunks are sent to the LLM per query
- API keys stored with `0600` permissions

### Backup

```bash
# Backup everything
cp -r ~/.fu7ur3pr00f/ ~/backup/fu7ur3pr00f-backup/

# Backup only the knowledge base
cp -r ~/.fu7ur3pr00f/episodic/ ~/backup/episodic-backup/
```

---

## Technical Details

### Similarity Search

Uses **cosine similarity** for vector comparison. ChromaDB's HNSW index provides O(log n) approximate nearest-neighbor search.

### SQLite Checkpointer

The `SqliteSaver` from `langgraph-checkpoint-sqlite` stores checkpoints in `memory.db` with `check_same_thread=False` for multi-threaded safety.

---

## See Also

- [Configuration](configuration.md) — Embedding model settings
- [Architecture](architecture.md) — System design
- [Data Gathering](gatherers.md) — How data is imported
- [Troubleshooting](troubleshooting.md) — Common issues
