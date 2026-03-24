# Troubleshooting Guide

Common issues and solutions for FutureProof.

---

## Installation Issues

### pipx command not found

**Error:** `bash: pipx: command not found`

**Solution:**
```bash
# Install pipx
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
# Check for conflicts
pip check

# If NumPy conflict (JobSpy pins numpy==1.26.3)
# Use separate venv for other tools
python -m venv .venv-other
source .venv-other/bin/activate
pip install other-tools
```

---

## LLM Connection Issues

### Azure OpenAI authentication fails

**Error:** `401 Unauthorized` or `API key not valid`

**Solution:**
1. Verify API key in `~/.fu7ur3pr00f/.env`:
   ```bash
   AZURE_OPENAI_API_KEY=your-key-here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   ```
2. Check key hasn't expired
3. Verify deployment names match:
   ```bash
   az cognitiveservices account deployment list \
     --resource-group YOUR_RG \
     --name YOUR_RESOURCE
   ```

### OpenAI API errors

**Error:** `Rate limit exceeded` or `429 Too Many Requests`

**Solution:**
- Wait and retry (rate limits reset)
- Use `--debug` to see retry behavior
- Consider upgrading OpenAI tier

### Ollama connection refused

**Error:** `Connection refused` or `httpx.ConnectError`

**Solution:**
```bash
# Start Ollama server
ollama serve

# Pull a model if none installed
ollama pull qwen3

# Verify connection
curl http://localhost:11434/api/tags
```

### All LLM providers fail

**Error:** `All LLM providers failed`

**Solution:**
1. Check internet connection
2. Verify at least one provider configured in `.env`
3. Run with debug: `fu7ur3pr00f --debug`
4. Check logs at `~/.fu7ur3pr00f/logs/`

---

## MCP Client Issues

### GitHub MCP not working

**Error:** `GitHub MCP client failed` or `401 Unauthorized`

**Solution:**
1. Verify token in `.env`:
   ```bash
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
   ```
2. Check token scopes:
   - Go to https://github.com/settings/tokens
   - Token must have: `repo`, `read:user`, `user:email`
3. Test connection:
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" \
     https://api.github.com/user
   ```

### Tavily search fails

**Error:** `Tavily API error` or `401 Unauthorized`

**Solution:**
1. Get API key at https://tavily.com/
2. Add to `.env`:
   ```bash
   TAVILY_API_KEY=your-key-here
   ```
3. Free tier: 1,000 queries/month

### JobSpy not returning results

**Issue:** No job results

**Solution:**
1. Check JobSpy is enabled:
   ```bash
   JOBSPY_ENABLED=true
   ```
2. Verify `python-jobspy` installed:
   ```bash
   pip show python-jobspy
   ```
3. Some job boards may be temporarily unavailable

---

## Data Gathering Issues

### LinkedIn ZIP not found

**Error:** `FileNotFoundError: LinkedIn export not found`

**Solution:**
1. Export from LinkedIn:
   - Settings → Data privacy → Get a copy of your data
   - Wait for email (10-30 min)
2. Place ZIP in correct location:
   ```bash
   mv ~/Downloads/LinkedIn*.zip ~/.fu7ur3pr00f/data/raw/linkedin.zip
   ```

### CliftonStrengths PDF not detected

**Error:** `No Gallup CliftonStrengths PDFs found`

**Solution:**
1. Rename PDF to include keywords:
   ```bash
   mv your-report.pdf Top_5_CliftonStrengths.pdf
   ```
2. Valid keywords: `top_5`, `top_10`, `all_34`, `cliftonstrengths`, `gallup`

### pdftotext not installed

**Error:** `pdftotext is not installed`

**Solution:**
```bash
# Debian/Ubuntu
sudo apt install poppler-utils

# macOS
brew install poppler

# Verify installation
pdftotext -v
```

### Portfolio scraping fails

**Error:** `SSRF protection` or `Connection refused`

**Solution:**
1. Portfolio must be publicly accessible
2. Cannot scrape:
   - `localhost` or `127.0.0.1`
   - Private IPs (`192.168.x.x`, `10.x.x.x`)
   - Sites requiring authentication
3. Check `robots.txt` allows scraping

### CV import returns empty

**Error:** `NoDataError: No text could be extracted`

**Solution:**
1. PDF may be scanned/image-based
2. Convert to text-based PDF or use Markdown
3. Verify file has content:
   ```bash
   pdftotext your-cv.pdf -
   ```

---

## ChromaDB Issues

### Database locked

**Error:** `Database is locked` or `OperationalError`

**Solution:**
1. Close other instances of fu7ur3pr00f
2. Remove lock file:
   ```bash
   rm ~/.fu7ur3pr00f/chroma/*.lock
   ```
3. Restart the application

### Indexing fails

**Error:** `Failed to index to ChromaDB`

**Solution:**
1. Check disk space:
   ```bash
   df -h ~/.fu7ur3pr00f
   ```
2. Clear and rebuild:
   ```bash
   fu7ur3pr00f
   /knowledge clear
   /gather
   ```

### Embedding errors

**Error:** `Embedding failed` or dimension mismatch

**Solution:**
1. Verify embedding model configured:
   ```bash
   EMBEDDING_MODEL=text-embedding-3-small
   ```
2. Check model is available in your LLM provider
3. Restart to reload embeddings

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

### CV content incomplete

**Issue:** Missing sections or data

**Solution:**
1. Gather all data first:
   ```bash
   /gather
   ```
2. Check knowledge base:
   ```bash
   /knowledge stats
   ```
3. Update profile with missing info

### Formatting broken in PDF

**Issue:** Weird layout or spacing

**Solution:**
1. Edit Markdown file to fix content
2. Remove custom formatting
3. Ensure proper Markdown syntax
4. Regenerate PDF

---

## Vagrant Issues

### VM fails to start

**Error:** `VT-x/AMD-V not available` or similar

**Solution:**
1. Enable virtualization in BIOS
2. Check VirtualBox installed:
   ```bash
   vboxmanage --version
   ```
3. Close other VMs or hypervisors

### Vagrant provisioning fails

**Error:** `Provisioning failed`

**Solution:**
1. Check logs:
   ```bash
   vagrant ssh
   cat /home/vagrant/provision.log
   ```
2. Destroy and recreate:
   ```bash
   vagrant destroy -f
   vagrant up --provision
   ```

### Shared folders not working

**Issue:** `/workspace` empty or not accessible

**Solution:**
1. Install VirtualBox Guest Additions
2. Restart VM:
   ```bash
   vagrant reload
   ```
3. Check permissions:
   ```bash
   vagrant ssh
   ls -la /workspace
   ```

---

## Debug Mode

Enable verbose logging:

```bash
fu7ur3pr00f --debug
```

This shows:
- LLM API calls and responses
- Tool execution details
- MCP client connections
- ChromaDB operations
- Full error tracebacks

### Log Files

```
~/.fu7ur3pr00f/logs/
├── fu7ur3pr00f.log      # Main application log
└── chroma.log           # ChromaDB logs
```

View recent logs:
```bash
tail -f ~/.fu7ur3pr00f/logs/fu7ur3pr00f.log
```

---

## Getting Help

### Check Documentation

- [Architecture](architecture.md) — System design
- [Configuration](configuration.md) — Settings reference
- [Tools](tools.md) — Tool documentation
- [Scripts](scripts.md) — Utility scripts

### Search Existing Issues

https://github.com/juanmanueldaza/fu7ur3pr00f/issues

### Create New Issue

Include:
1. **What happened** — Clear description
2. **Expected behavior** — What you expected
3. **Reproduction steps** — How to reproduce
4. **Environment** — OS, Python version, fu7ur3pr00f version
5. **Logs** — Debug output from `fu7ur3pr00f --debug`

### System Information

Run this and include in bug report:
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
| API key invalid | Check `.env` and regenerate if needed |
| PDF not generated | Install poppler-utils and pango libs |
| Data not found | Run `/gather` first |
| Database locked | Close other instances, remove `.lock` files |
| VM won't start | Enable virtualization in BIOS |

---

## See Also

- [Configuration](configuration.md) — Settings reference
- [Data Gathering](gatherers.md) — Import guide
- [CV Generation](cv_generation.md) — CV guide
