"""Project-wide constants.

All magic numbers, API base URLs, error message templates, status strings,
file paths, and UI colors live here. Import from this module rather than
scattering literals throughout the codebase.
"""

# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------
TOOL_RESULT_MAX_CHARS = 3000
TOOL_RESULT_PREVIEW_CHARS = 500
MAX_TOOL_ROUNDS = 10
MAX_TOTAL_TOOL_CALLS = 25

# ---------------------------------------------------------------------------
# LLM / context limits
# ---------------------------------------------------------------------------
ANALYSIS_MARKER = (
    "[Detailed analysis was displayed directly to the user. "
    "Do not repeat or summarize it. Instead: reference salary data, "
    "ask about current compensation if unknown, and suggest "
    "1-2 concrete next steps.]"
)
CAREER_CONTEXT_MAX_CHARS = 4000

# ---------------------------------------------------------------------------
# Chunking / tokenisation
# ---------------------------------------------------------------------------
CHUNK_MAX_TOKENS = 500
CHUNK_MIN_TOKENS = 50
TOKENS_PER_WORD = 1.3

# ---------------------------------------------------------------------------
# Knowledge base / vector store
# ---------------------------------------------------------------------------
INDEX_BATCH_SIZE = 100
SEARCH_FETCH_MULTIPLIER = 3
MAX_EMBEDDING_CACHE_SIZE = 1000

# ---------------------------------------------------------------------------
# Timeouts (seconds)
# ---------------------------------------------------------------------------
HTTP_TIMEOUT = 20

# ---------------------------------------------------------------------------
# CliftonStrengths tiers
# ---------------------------------------------------------------------------
CLIFTON_TOP_5_MAX_RANK = 5
CLIFTON_TOP_10_MAX_RANK = 10
CLIFTON_ALL_34_MAX_RANK = 34

# ---------------------------------------------------------------------------
# MCP / external API base URLs
# ---------------------------------------------------------------------------
GITHUB_API_BASE = "https://api.github.com"
HN_API_BASE = "https://hn.algolia.com/api/v1"
HN_BASE_URL = "https://news.ycombinator.com"
DEVTO_API_BASE = "https://dev.to/api/articles"
STACKOVERFLOW_API_BASE = "https://api.stackexchange.com/2.3"
FOREX_API_BASE = "https://open.er-api.com/v6/latest"
PPP_API_BASE = "https://api.worldbank.org/v2/country"
TAVILY_API_BASE = "https://api.tavily.com/search"
REMOTEOK_API_BASE = "https://remoteok.com/api"
HIMALAYAS_API_BASE = "https://himalayas.app/jobs/api"
REMOTIVE_API_BASE = "https://remotive.com/api/remote-jobs"
JOBICY_API_BASE = "https://jobicy.com/api/v2/remote-jobs"
JOBICY_RSS_URL = "https://jobicy.com/feed/newjobs"
WEREMOTE_BASE = "https://weworkremotely.com"
WEREMOTE_FEEDS = {
    "programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "devops": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "management": "https://weworkremotely.com/categories/remote-management-jobs.rss",
    "all": "https://weworkremotely.com/remote-jobs.rss",
}

# ---------------------------------------------------------------------------
# Error message templates
# ---------------------------------------------------------------------------
ERROR_TOOL_NOT_FOUND = "Tool {name!r} not available to {agent} specialist."
ERROR_TOOL_EXECUTION = "Error running {tool}: {error}"
ERROR_KNOWLEDGE_NOT_FOUND = "No relevant career knowledge found for this query."
ERROR_KNOWLEDGE_EMPTY = "Knowledge base is empty — index career data first."
ERROR_PROFILE_NOT_CONFIGURED = (
    "No profile configured. Run /setup or /profile to add your information."
)
ERROR_PDFTOTEXT_MISSING = (
    "pdftotext is not installed. "
    "Install it with: apt install poppler-utils  /  brew install poppler"
)

# ---------------------------------------------------------------------------
# Status strings
# ---------------------------------------------------------------------------
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_WORKING = "working"
STATUS_COMPLETE = "complete"

# ---------------------------------------------------------------------------
# Default data directory and paths
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR = "~/.fu7ur3pr00f"
DEFAULT_ENV_PATH = "~/.fu7ur3pr00f/.env"

# ---------------------------------------------------------------------------
# UI colours (Rich markup / prompt-toolkit)
# ---------------------------------------------------------------------------
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#ffd700"
COLOR_ERROR = "#ff6b6b"
COLOR_INFO = "#415a77"
COLOR_ACCENT = "#e0d8c0"
