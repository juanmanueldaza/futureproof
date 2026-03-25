# Chat Commands Reference

FutureProof has two interaction modes:

1. **Natural language** — just type. The agent understands requests like "analyze my skill gaps for Staff Engineer" or "search for remote Python jobs" or "generate my CV targeting senior roles". This is how most features are accessed.
2. **Slash commands** — a small set of utility commands for navigation, setup, and data management.

---

## Natural Language Interaction

Most features are accessed by typing naturally. Examples:

```
> analyze my skill gaps for a Staff Engineer role
> search for remote Python jobs paying above $150k
> generate an ATS-optimized CV for senior backend roles
> what are the trending technologies in my field?
> remember that I prefer remote work
> what job applications have I saved?
> convert 180000 USD to ARS with PPP comparison
> what salary can I expect for a senior ML engineer in Berlin?
```

The agent uses its 41 tools behind the scenes — RAG search over your indexed career data, job board queries, market analysis, CV generation, and more.

---

## Slash Commands

Type `/` followed by the command. Commands are case-insensitive.

---

### `/help` or `/h` — Show help

Display the help panel with all available commands.

```bash
/help
/h
```

---

### `/setup` — Configure LLM and API keys

Run the interactive setup wizard. Prompts for LLM provider and API keys, writes `~/.fu7ur3pr00f/.env` with secure permissions (`0600`).

```bash
/setup
```

**Triggered automatically** on first run if no provider is configured.

---

### `/gather` — Import career data

Scan `~/.fu7ur3pr00f/data/raw/` for data files and index them to ChromaDB.

```bash
/gather
```

**Sources scanned:**
- `*.zip` → LinkedIn export
- `*.pdf` containing "strength" → CliftonStrengths
- `*.md`, `*.pdf`, `*.txt` → CV/resume
- `PORTFOLIO_URL` in `.env` → portfolio website

**See:** [Data Gathering Guide](gatherers.md)

> **Note:** For granular per-source control (LinkedIn only, GitHub only, etc.), tell the agent in natural language: *"gather only my LinkedIn data"* or *"gather my GitHub profile"*.

---

### `/profile` — View your profile

Display a summary of your stored career profile (name, role, skills, targets).

```bash
/profile
```

---

### `/goals` — View your career goals

Display your stored career goals.

```bash
/goals
```

---

### `/thread [name]` — Show or switch conversation thread

Without an argument, shows the current thread ID. With an argument, switches to that thread (creating it if it doesn't exist).

```bash
/thread           # Show current thread
/thread work      # Switch to "work" thread
/thread interview # Switch to "interview" thread
```

Threads let you maintain separate conversations (e.g., one for job search, one for CV work).

---

### `/threads` — List all conversation threads

Show all threads that have stored conversation history.

```bash
/threads
```

Active thread is marked.

---

### `/memory` — Show memory and profile stats

Display a summary: data directory, number of threads, profile status, and goal count.

```bash
/memory
```

> **Note:** `/memory` does not have subcommands for search or clear. Use natural language to interact with the knowledge base: *"search my knowledge base for Python projects"* or *"clear my career knowledge base"*.

---

### `/multi` — Multi-agent system

Access the multi-agent system (Orchestrator + Specialist Agents).

```bash
/multi             # Show usage and agent list
/multi agents      # List all specialist agents
/multi test        # Test multi-agent connectivity
```

**Specialist agents:**
- `Coach` — Career growth, leadership, promotions
- `Learning` — Skill development, expertise building
- `Jobs` — Job search, market fit, salary insights
- `Code` — GitHub, GitLab, open source strategy
- `Founder` — Startups, entrepreneurship, launch planning

> The multi-agent system is an alternative to the default single-agent mode. Queries via `/multi` are routed by an orchestrator to the appropriate specialist.

---

### `/debug` — Toggle debug mode

Toggle verbose logging to the terminal. When ON, shows LLM calls, tool execution, agent routing, and ChromaDB operations.

```bash
/debug
```

Full debug logs are always written to `~/.fu7ur3pr00f/data/fu7ur3pr00f.log` regardless of this setting.

---

### `/verbose` — Show system information

Display current system state: data directory, LLM provider, active model, portfolio URL, MCP status, log level.

```bash
/verbose
```

---

### `/clear` — Clear conversation history

Delete all stored messages for the current thread. Does not affect the knowledge base or profile.

```bash
/clear
```

---

### `/reset` — Factory reset

Delete all generated data (conversation history, profile, episodic memory, CV output, market cache). Preserves raw data files (`data/raw/`).

```bash
/reset
```

**Requires confirmation** (`y`/`yes`). After reset, the application exits — restart to start fresh.

**Deleted:**
- `~/.fu7ur3pr00f/memory.db` — conversation history
- `~/.fu7ur3pr00f/profile.yaml` — user profile
- `~/.fu7ur3pr00f/episodic/` — knowledge base and episodic memory
- `~/.fu7ur3pr00f/data/fu7ur3pr00f.log` — log file
- `~/.fu7ur3pr00f/data/output/` — generated CVs
- `~/.fu7ur3pr00f/data/processed/` — processed data
- `~/.fu7ur3pr00f/data/cache/` — market data cache

**Preserved:** `~/.fu7ur3pr00f/data/raw/` (LinkedIn ZIPs, PDFs, CV files)

---

### `/quit` or `/q` or `/exit` — Exit

Exit the chat application. Conversation is saved automatically.

```bash
/quit
/q
/exit
```

`Ctrl+D` (EOF) also exits cleanly.

---

## Command Aliases

| Alias | Full Command |
|-------|--------------|
| `/h` | `/help` |
| `/q` | `/quit` |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current input (keeps app running) |
| `Ctrl+D` | Exit application (same as `/quit`) |
| `↑` / `↓` | Navigate command history |

Command history is persisted to `~/.fu7ur3pr00f/data/chat_history`.

---

## Workflows

### First-time setup

```
/setup          → configure LLM provider
/gather         → import career data from ~/.fu7ur3pr00f/data/raw/
analyze my career profile and skill gaps
```

### Job search

```
search for remote senior Python backend jobs
what is the market salary for a Staff Engineer in the US?
generate my CV targeting senior backend roles
```

### Career planning

```
/profile                           → review current profile
analyze my skill gaps for ML Engineer
what steps should I take to become a Staff Engineer?
/memory                            → check data availability
```

### Thread management

```
/threads                           → see existing conversations
/thread jobsearch                  → switch to job search thread
search for remote Python jobs
/thread cvwork                     → switch to CV thread
generate my CV targeting fintech companies
```

---

## Troubleshooting

### Command not recognized

**Issue:** `Unknown command`

**Solution:**
- Use `/help` to see all available slash commands
- Most features work via natural language — no slash command required

### HITL confirmation prompt

Some agent operations pause for human approval (`[Y/n]:`):
- Full data gathering
- CV generation
- Clearing the knowledge base

Press `Enter` or type `y` to approve, `n` to cancel.

### Command takes too long

Check internet and API key validity. Run `/debug` to see detailed logs. View logs at `~/.fu7ur3pr00f/data/fu7ur3pr00f.log`.

---

## See Also

- [Configuration](configuration.md) — Provider and key setup
- [Data Gathering](gatherers.md) — What `/gather` imports
- [CV Generation](cv_generation.md) — How CV generation works
- [Troubleshooting](troubleshooting.md) — Common issues
