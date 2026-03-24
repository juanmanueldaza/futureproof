# Memory System

How FutureProof stores and retrieves your career data using ChromaDB.

---

## Overview

FutureProof uses ChromaDB for two types of memory:

| Type | Purpose | Content |
|------|---------|---------|
| **Knowledge Base** | RAG search | Career data, skills, experience |
| **Episodic Memory** | Conversation history | Decisions, applications, chat context |

---

## Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedding Model│  ← Converts query to vector
│  (text-embedding)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChromaDB      │  ← Vector similarity search
│  - Knowledge    │
│  - Episodic     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Top-K Results  │  ← Most relevant chunks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     LLM +       │  ← Generates response with context
│   Retrieved     │
│    Context      │
└─────────────────┘
```

---

## Data Directory

```
~/.fu7ur3pr00f/
├── chroma/                  # ChromaDB database
│   ├── chroma.sqlite3       # Metadata store
│   └── *.bin                # Vector index files
└── data/
    └── raw/                 # Source data files
```

---

## Knowledge Base

### What Gets Indexed

When you run `/gather`, data is:
1. Parsed into sections
2. Chunked (50-500 tokens)
3. Embedded (vector representation)
4. Stored in ChromaDB

### Indexed Sources

| Source | Sections |
|--------|----------|
| LinkedIn | Profile, Experience, Education, Skills, etc. |
| GitHub | Repos, Contributions, Languages |
| GitLab | Projects, Merge Requests |
| CliftonStrengths | Top 5/10/34 strengths, insights |
| CV/Resume | All detected sections |
| Portfolio | About, Projects, Blog posts |

### Chunking Strategy

Text is split into chunks for efficient retrieval:

- **Min tokens:** 50
- **Max tokens:** 500
- **Overlap:** 50 tokens
- **Boundary:** Paragraph/section breaks

### Search

```bash
/memory search Python        # Semantic search
/knowledge search AWS        # Same as above
```

Search finds chunks by **meaning**, not just keywords.

**Example:**
- Query: "backend development"
- Matches: "API development", "server-side programming", "database design"

---

## Episodic Memory

### What Gets Stored

| Event | Stored Data |
|-------|-------------|
| Career decisions | Decision, reasoning, date |
| Job applications | Company, role, status, date |
| Chat context | Important conversation turns |

### Commands

```bash
# Remember a decision
/memory remember decision "Accepted offer at Company X"

# Remember job application
/memory remember application "Senior Dev at Google - Applied 2024-01-15"

# Recall memories
/memory recall "job applications"
/memory recall "decisions"

# Get stats
/memory stats
```

---

## Embeddings

### Model Configuration

```bash
# In ~/.fu7ur3pr00f/.env
EMBEDDING_MODEL=text-embedding-3-small  # OpenAI (default)
```

### Supported Models

| Provider | Model |
|----------|-------|
| OpenAI | `text-embedding-3-small`, `text-embedding-3-large` |
| Azure | `text-embedding-3-small` |
| Ollama | `nomic-embed-text`, `mxbai-embed-large` |

### Vector Dimensions

| Model | Dimensions |
|-------|------------|
| text-embedding-3-small | 1536 |
| text-embedding-3-large | 3072 |
| nomic-embed-text | 768 |

---

## Commands Reference

### Search Knowledge

```bash
/memory search <query>     # Search knowledge base
/knowledge search <query>  # Alias
```

**Examples:**
```bash
/memory search Python Django
/memory search "machine learning"
/memory search AWS certification
```

### Knowledge Stats

```bash
/memory stats              # Show knowledge base stats
/knowledge stats           # Alias
```

**Output:**
```
Knowledge Base Statistics:
- Total documents: 156
- Total chunks: 423
- Collections: 1
- Embedding model: text-embedding-3-small
```

### Clear Knowledge

```bash
/memory clear              # Clear all knowledge
/knowledge clear           # Alias
```

**Requires confirmation** before deleting all data.

### Remember Events

```bash
/memory remember decision "Description of decision"
/memory remember application "Company - Role - Status"
```

### Recall Memories

```bash
/memory recall <query>     # Search episodic memories
```

---

## Advanced Usage

### Manual Indexing

```bash
/index file resume.md      # Index specific file
/index directory ./docs    # Index directory
```

### Export/Import

```bash
/export knowledge          # Export knowledge base
/import knowledge backup/  # Import previously exported
```

---

## Troubleshooting

### Search returns no results

**Issue:** Query doesn't match any chunks

**Solution:**
1. Try different keywords
2. Check if data is indexed: `/memory stats`
3. Re-run `/gather` if needed

### Database locked

**Error:** `Database is locked`

**Solution:**
```bash
# Close other instances
# Remove lock files
rm ~/.fu7ur3pr00f/chroma/*.lock

# Restart application
```

### Indexing fails

**Error:** `Failed to index to ChromaDB`

**Solution:**
1. Check disk space:
   ```bash
   df -h ~/.fu7ur3pr00f
   ```
2. Clear and rebuild:
   ```bash
   /knowledge clear
   /gather
   ```

### Embedding errors

**Error:** `Embedding failed`

**Solution:**
1. Verify embedding model configured
2. Check LLM provider connectivity
3. Restart to reload embeddings

---

## Performance Tuning

### Chunk Size

Adjust in `.env`:

```bash
KNOWLEDGE_CHUNK_MAX_TOKENS=500
KNOWLEDGE_CHUNK_MIN_TOKENS=50
```

**Smaller chunks:**
- More precise retrieval
- More chunks to search

**Larger chunks:**
- More context per chunk
- May include irrelevant content

### Search Results

Default returns top 5 chunks. Adjust:

```python
# In code or via settings
top_k = 10  # Return more results
```

---

## Data Privacy

### Where Data is Stored

- **Local:** `~/.fu7ur3pr00f/chroma/`
- **No cloud sync** unless you configure it
- **Full control** over your data

### What Gets Sent to LLM

- Only **relevant chunks** (top 5-10)
- **Anonymized** if configured
- **Not stored** by LLM provider

### Backup Your Data

```bash
# Backup ChromaDB
cp -r ~/.fu7ur3pr00f/chroma/ ~/backup/chroma-backup/

# Backup source data
cp -r ~/.fu7ur3pr00f/data/ ~/backup/data-backup/
```

---

## Technical Details

### ChromaDB Configuration

```python
# Collection settings
collection_name = "career_knowledge"
metadata = {"hnsw:space": "cosine"}  # Cosine similarity
```

### Similarity Search

Uses **cosine similarity** for vector comparison:
- Range: -1 to 1
- Higher = more similar
- Threshold: ~0.7 for good matches

### Index Type

Uses **HNSW** (Hierarchical Navigable Small World):
- Fast approximate nearest neighbors
- O(log n) search time
- Configurable accuracy

---

## See Also

- [Configuration](configuration.md) — Embedding model settings
- [Architecture](architecture.md) — System design
- [Data Gathering](gatherers.md) — How data is imported
- [Troubleshooting](troubleshooting.md) — Common issues
