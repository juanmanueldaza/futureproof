# Troubleshooting Guide

Common issues and solutions for FutureProof.

---

## Installation Issues

### pipx command not found

**Error:** `bash: pipx: command not found`

**Solution:**
```bash
python -m pip install --user pipx
python -m pipx ensurepath

# Restart terminal or run:
source ~/.bashrc  # or ~/.zshrc
```

### Module not found after install

**Error:** `ModuleNotFoundError: No module named 'fu7ur3pr00f'`

**Solution:**
```bash
# Reinstall
pipx uninstall fu7ur3pr00f
pipx install fu7ur3pr00f

# Or from source
cd /path/to/fu7ur3pr00f
pip install -e .
```

### Dependencies conflict

**Error:** `ERROR: pip's dependency resolver...`

**Solution:**
```bash
pip check

# NumPy conflict (python-jobspy pins numpy)
# Use a dedicated virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## LLM Connection Issues

### No provider configured

**Error:** Setup wizard launches on first start

**Solution:**
Run `/setup` and enter your API key for one provider. See [Configuration](configuration.md).

### Azure OpenAI authentication fails

**Error:** `401 Unauthorized` or `API key not valid`

**Solution:**
1. Verify API key in `~/.fu7ur3pr00f/.env`:
   ```bash
   AZURE_OPENAI_API_KEY=your-key-here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   ```
2. Check that the endpoint does NOT include `/api/projects/...` (it's stripped automatically, but verify)
3. Verify deployment names match your Azure resource:
   ```bash
   az cognitiveservices account deployment list \
     --resource-group YOUR_RG \
     --name YOUR_RESOURCE
   ```

### OpenAI rate limit

**Error:** `Rate limit exceeded` or `429 Too Many Requests`

**Solution:**
- The agent has automatic fallback — it will try the next model in the chain
- Run `/verbose` to see which model is active
- Use `--debug` to observe the fallback chain

### Ollama connection refused

**Error:** `Connection refused` or `httpx.ConnectError`

**Solution:**
```bash
# Start Ollama server
ollama serve

# Pull a model if none installed
ollama pull qwen3

# Verify
curl http://localhost:11434/api/tags
```

### All LLM providers fail

**Error:** `All LLM providers failed`

**Solution:**
1. Check internet connection
2. Verify at least one provider configured in `~/.fu7ur3pr00f/.env`
3. Run: `fu7ur3pr00f --debug`
4. Check logs: `tail -f ~/.fu7ur3pr00f/data/fu7ur3pr00f.log`

---

## MCP Client Issues

### GitHub MCP not working

**Error:** `GitHub MCP client failed` or `401 Unauthorized`

**Solution:**
1. Verify token in `~/.fu7ur3pr00f/.env`:
   ```bash
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
   ```
2. Check token scopes at https://github.com/settings/tokens:
   - `repo`, `read:user`, `user:email`
3. Test manually:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```

### Tavily search fails

**Error:** `Tavily API error` or `401 Unauthorized`

**Solution:**
1. Get free API key at https://tavily.com/
2. Add to `~/.fu7ur3pr00f/.env`:
   ```bash
   TAVILY_API_KEY=your-key-here
   ```
3. Free tier: 1,000 queries/month

### JobSpy not returning results

**Issue:** No job results

**Solution:**
1. Check JobSpy is enabled (default: true):
   ```bash
   JOBSPY_ENABLED=true
   ```
2. Verify installation: `pip show python-jobspy`
3. Some job boards may be temporarily unavailable — try again later

---

## Data Gathering Issues

### LinkedIn ZIP not found

**Error:** `No LinkedIn ZIP found`

**Solution:**
1. Export from LinkedIn: Settings → Data privacy → Get a copy of your data
2. Wait for email (10–30 min)
3. Place ZIP in `~/.fu7ur3pr00f/data/raw/`:
   ```bash
   mv ~/Downloads/LinkedIn*.zip ~/.fu7ur3pr00f/data/raw/linux.zip
   ```
4. Run `/gather`

### CliftonStrengths PDF not detected

**Error:** `No CliftonStrengths PDFs found`

**Solution:**
1. Rename PDF to include keywords:
   ```bash
   mv your-report.pdf Top_5_CliftonStrengths.pdf
   ```
2. Valid keywords (case-insensitive): `strength`, `top_5`, `top_10`, `all_34`, `cliftonstrengths`, `gallup`

### pdftotext not installed

**Error:** `pdftotext is not installed`

**Solution:**
```bash
# Debian/Ubuntu
sudo apt install poppler-utils

# macOS
brew install poppler

# Verify
pdftotext -v
```

### Portfolio scraping fails

**Error:** `SSRF protection` or `Connection refused`

**Solution:**
1. Portfolio must be publicly accessible (no auth required)
2. Cannot scrape: localhost, private IPs, or robots.txt-blocked paths
3. Verify `PORTFOLIO_URL` in `~/.fu7ur3pr00f/.env` is correct

### CV import returns empty

**Error:** `No text could be extracted`

**Solution:**
1. PDF may be scanned/image-based
2. Convert to text-based PDF, or use Markdown format instead:
   ```bash
   pdftotext your-cv.pdf -  # Verify it has text
   ```

---

## Knowledge Base Issues

### Database locked (SQLite)

**Error:** `Database is locked` or `OperationalError`

**Solution:**
1. Close other instances of fu7ur3pr00f
2. Remove any lock files:
   ```bash
   rm -f ~/.fu7ur3pr00f/*.lock
   ```
3. Restart the application

### ChromaDB errors

**Error:** ChromaDB-related failures

**Solution:**
1. Check disk space: `df -h ~/.fu7ur3pr00f`
2. If corrupted, remove and rebuild:
   ```bash
   rm -rf ~/.fu7ur3pr00f/episodic/
   ```
   Then run `/gather` to re-index. Conversation history (`memory.db`) is unaffected.

### Agent says it has no data

**Issue:** "No career data indexed yet"

**Solution:**
1. Run `/gather` or tell the agent: *"gather all my career data"*
2. Verify files exist in `~/.fu7ur3pr00f/data/raw/`
3. Ask: *"show me knowledge base statistics"*

### Embedding errors

**Error:** `Embedding failed` or dimension mismatch

**Solution:**
1. Verify embedding model in `~/.fu7ur3pr00f/.env`:
   ```bash
   EMBEDDING_MODEL=text-embedding-3-small
   ```
2. Check LLM provider connectivity
3. Restart the application

---

## CV Generation Issues

### PDF generation fails

**Error:** `WeasyPrint not available` or PDF not created

**Solution:**
```bash
# Install system dependencies
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libfontconfig1 libgdk-pixbuf-2.0-0

# Verify weasyprint
python -c "import weasyprint; print(weasyprint.__version__)"
```

### CV content thin or incomplete

**Issue:** Missing sections or generic content

**Solution:**
1. Gather all data first: `/gather`
2. Tell the agent more about yourself: *"I have 8 years of Python experience, led teams of 5+, worked at X and Y"*
3. Ask: *"show me knowledge base statistics"* to confirm data is indexed

### Formatting broken in PDF

**Solution:**
1. Edit `~/.fu7ur3pr00f/data/output/cv_en_ats.md` to fix content
2. Remove any non-standard Markdown
3. Ask the agent to regenerate the PDF

---

## Vagrant Issues

### VM fails to start

**Error:** `VT-x/AMD-V not available`

**Solution:**
1. Enable virtualization in BIOS
2. Check VirtualBox is installed: `vboxmanage --version`
3. Close other hypervisors (Hyper-V, VMware)

### Vagrant provisioning fails

**Solution:**
```bash
vagrant ssh
cat /home/vagrant/provision.log
# Fix issues, then:
vagrant destroy -f
vagrant up --provision
```

### Shared folders not working

**Solution:**
```bash
vagrant reload  # Restart with Guest Additions
vagrant ssh
ls -la /workspace
```

---

## Debug Mode

Enable verbose logging:

```bash
fu7ur3pr00f --debug
```

Or toggle inside chat with `/debug`.

Full logs are always written to `~/.fu7ur3pr00f/data/fu7ur3pr00f.log`:

```bash
tail -f ~/.fu7ur3pr00f/data/fu7ur3pr00f.log
```

Use `/verbose` in chat for a quick system status summary.

---

## Getting Help

### Check Documentation

- [Architecture](architecture.md) — System design
- [Configuration](configuration.md) — Settings reference
- [Chat Commands](chat_commands.md) — Commands reference
- [Data Gathering](gatherers.md) — Import guide

### Search Existing Issues

https://github.com/juanmanueldaza/fu7ur3pr00f/issues

### Create New Issue

Include:
1. **What happened** — Clear description
2. **Expected behavior**
3. **Reproduction steps**
4. **Environment** — OS, Python version, fu7ur3pr00f version
5. **Logs** — From `~/.fu7ur3pr00f/data/fu7ur3pr00f.log` or `fu7ur3pr00f --debug`

### System Information

```bash
fu7ur3pr00f --version
python --version
uname -a
```

---

## Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Command not found | `pipx ensurepath` then restart terminal |
| Module not found | `pip install -e .` |
| API key invalid | Check `~/.fu7ur3pr00f/.env` and regenerate key |
| PDF not generated | Install poppler-utils + pango libs |
| No career data | Run `/gather` or tell the agent to gather data |
| Database locked | Close other instances, remove `.lock` files |
| VM won't start | Enable virtualization in BIOS |
| Agent gives generic answers | Run `/gather` first — agent needs indexed data |

---

## See Also

- [Configuration](configuration.md) — Settings reference
- [Data Gathering](gatherers.md) — Import guide
- [CV Generation](cv_generation.md) — CV guide
- [Memory System](memory_system.md) — Storage details
