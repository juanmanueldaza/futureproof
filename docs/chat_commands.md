# Chat Commands Reference

All commands available in the FutureProof chat client.

## Usage

Type `/` followed by command name. Most commands accept arguments.

```bash
/command [arguments]
```

---

## Core Commands

### `/help` — Show help

Show all available commands or help for specific command.

```bash
/help                    # Show all commands
/help gather             # Help for specific command
```

---

### `/gather` — Import career data

Gather data from various sources and index to ChromaDB.

```bash
/gather                  # Gather all sources
/gather linkedin         # LinkedIn export only
/gather github           # GitHub profile only
/gather portfolio        # Portfolio website only
/gather cliftonstrengths # CliftonStrengths PDF only
/gather cv               # CV/resume file only
```

**Sources:**
- LinkedIn ZIP export
- GitHub (via MCP)
- Portfolio website
- CliftonStrengths PDF
- CV/resume files

**See:** [Data Gathering Guide](gatherers.md)

---

### `/analyze` — Career analysis

Analyze your career data and provide insights.

```bash
/analyze                 # General career analysis
/analyze skills          # Skill gap analysis
/analyze market          # Market fit analysis
/analyze for Staff Engineer  # Analysis for specific role
```

**Outputs:**
- Skill gaps
- Market fit assessment
- Career trajectory recommendations
- Salary insights

---

### `/search` — Job search

Search job boards and hiring threads.

```bash
/search                  # Search all job boards
/search python remote    # Search with keywords
/search --board linkedin # Search specific board
```

**Boards searched:**
- LinkedIn
- Indeed
- Glassdoor
- RemoteOK
- Himalayas
- Hacker News "Who's Hiring"
- And more...

---

### `/generate` — Generate CV

Create ATS-optimized CV in Markdown and PDF.

```bash
/generate cv             # Generate CV
/generate cv draft       # Generate draft for review
/generate cv for Senior Developer  # Targeted CV
```

**Outputs:**
- `data/output/cv_en_ats.md` (Markdown)
- `data/output/cv_en_ats.pdf` (PDF)

**See:** [CV Generation Guide](cv_generation.md)

---

### `/memory` — Knowledge base

Query and manage your career knowledge base.

```bash
/memory search Python    # Search knowledge base
/memory stats            # Show knowledge base stats
/memory clear            # Clear all knowledge (requires confirmation)
```

**See:** [Memory System](memory_system.md)

---

## Profile Commands

### `/get` — View profile

View your current profile and settings.

```bash
/get profile             # Full profile
/get goals               # Career goals
/get config              # Current configuration
```

---

### `/update` — Update profile

Update your profile information.

```bash
/update name John Doe              # Update name
/update current_role Senior Dev    # Update current role
/update skills Python, AWS, Docker # Update skills
/update salary 150000 USD          # Update salary
```

---

### `/set` — Set preferences

Set career preferences and targets.

```bash
/set target_role Staff Engineer    # Set target role
/set goal Lead engineering team    # Set career goal
/set location Remote               # Set location preference
```

---

### `/clear` — Clear profile data

Clear specific profile data (requires confirmation).

```bash
/clear profile           # Clear entire profile
/clear goals             # Clear career goals
```

---

## Settings Commands

### `/config` — Configuration

View and modify application settings.

```bash
/config                  # Show current config
/config set MODEL gpt-4  # Update setting
```

---

### `/model` — Switch LLM model

Switch the LLM model being used.

```bash
/model                   # Show current model
/model gpt-4             # Switch to GPT-4
/model claude-3          # Switch to Claude 3
/model list              # List available models
```

---

### `/setup` — Initial setup

Run the setup wizard for first-time configuration.

```bash
/setup
```

**Configures:**
- LLM provider
- API keys
- Data directories
- MCP clients

---

## Knowledge Commands

### `/index` — Index data

Manually index data to the knowledge base.

```bash
/index file resume.md    # Index specific file
/index directory ./docs  # Index directory
```

---

### `/knowledge` — Knowledge management

Alias for `/memory` commands.

```bash
/knowledge search Python
/knowledge stats
/knowledge clear
```

---

## Utility Commands

### `/export` — Export data

Export your data in various formats.

```bash
/export cv               # Export CV (same as /generate)
/export profile          # Export profile as JSON
/export knowledge        # Export knowledge base
```

---

### `/import` — Import data

Import data from external sources.

```bash
/import cv resume.pdf    # Import CV file
/import linkedin export.zip  # Import LinkedIn export
```

---

### `/debug` — Debug mode

Toggle debug logging.

```bash
/debug                   # Toggle debug mode
/debug on                # Enable debug
/debug off               # Disable debug
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current operation |
| `Ctrl+D` | Exit application |
| `↑/↓` | Command history |
| `Tab` | Autocomplete |
| `Ctrl+R` | Search history |

---

## Exit Commands

### `/quit` — Exit application

```bash
/quit
/exit
Ctrl+D
```

---

## Command Aliases

| Alias | Full Command |
|-------|--------------|
| `/h` | `/help` |
| `/g` | `/gather` |
| `/a` | `/analyze` |
| `/s` | `/search` |
| `/gen` | `/generate` |
| `/m` | `/memory` |
| `/q` | `/quit` |

---

## Examples

### First-time setup

```bash
/setup                     # Configure LLM and settings
/gather                    # Import all career data
/analyze                   # Get initial analysis
```

### Job search workflow

```bash
/search python remote      # Find remote Python jobs
/analyze market            # Check market fit
/generate cv               # Generate targeted CV
```

### Career planning

```bash
/get profile               # Review current profile
/set target_role Staff Engineer  # Set goal
/analyze skills            # Identify gaps
/gather                    # Update data
/analyze                   # Get recommendations
```

### Knowledge management

```bash
/knowledge stats           # Check indexed data
/knowledge search AWS      # Find AWS-related info
/knowledge search "system design"  # Multi-word search
```

---

## Tips

1. **Use Tab for autocomplete** — Type `/` and press Tab to see commands
2. **Command history** — Use ↑/↓ to navigate previous commands
3. **Partial matching** — `/mem` works for `/memory`
4. **Quotes for multi-word** — `/search "machine learning"`
5. **Combine commands** — Chain related commands in sequence

---

## Troubleshooting

### Command not found

**Issue:** Unknown command

**Solution:**
- Check spelling
- Use `/help` to see available commands
- Ensure you're using `/` prefix

### Command requires confirmation

Some commands require `Y/n` confirmation:
- `/knowledge clear`
- `/clear profile`
- CV generation (HITL)

### Command timeout

**Issue:** Command takes too long

**Solution:**
- Check internet connection
- Verify API keys are valid
- Run with `--debug` for details

---

## See Also

- [Configuration](configuration.md) — Settings reference
- [Troubleshooting](troubleshooting.md) — Common issues
- [Architecture](architecture.md) — System design
