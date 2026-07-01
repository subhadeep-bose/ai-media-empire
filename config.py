from pathlib import Path
import os

REPO_ROOT = Path(__file__).parent

# LLM
GROQ_MODEL = "llama-3.1-8b-instant"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
GROQ_MAX_TOKENS_INTEL = 2500
GROQ_MAX_TOKENS_CONTENT = 1000
GROQ_RATE_LIMIT_RETRIES = 4
GROQ_RATE_LIMIT_WAIT_BASE = 15

# Scrapers
SCRAPER_TIMEOUT = 10
RATE_LIMIT_SECS = 2
ITEMS_PER_SOURCE = 5
SUMMARY_MAX_CHARS = 150

# Squad 2 generators write one of these exact strings when a niche has no
# real content today; Squad 3 reads the same list to decide what to skip.
SKIP_MARKERS = (
    "NO SPORTS CONTENT TODAY",
    "NO GAMING CONTENT TODAY",
    "NO BENGALI BOOK CONTENT TODAY",
    "NO MOVIES CONTENT TODAY",
    "NO AI/TECH CONTENT TODAY",
    "[ERROR]",
)

# Squad 3 moderation pass — case-insensitive substring denylist checked
# against each script before TTS/video assembly. Intentionally small and
# blunt (a safety net for an obvious LLM slip, not a full moderation
# system); flagged niches are skipped the same way SKIP_MARKERS niches are.
MODERATION_DENYLIST = (
    "kill yourself",
    "suicide instructions",
    "child sexual",
    "how to make a bomb",
    "credit card number",
)

# Paths
SEEN_ITEMS_PATH = REPO_ROOT / "seen_items.json"
DIGEST_PATH = REPO_ROOT / "master_intel_digest.md"
OUTPUT_DIR = REPO_ROOT / "squad2_output"
LOG_DIR = REPO_ROOT / "logs"
LLM_USAGE_PATH = REPO_ROOT / "llm_usage_history.json"

# Squad 3 — video assembly
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
STOCK_CLIPS_PER_REEL = 3

# Squad 5 — infra resilience
SQUAD_RETRY_ATTEMPTS = 2          # extra attempts after the first failure
SQUAD_RETRY_WAIT_BASE_SECS = 30   # backoff = base * attempt_number
SQUAD_TIMEOUT_SECS = 600

# Squad 6 — analytics feedback loop
ANALYTICS_HISTORY_PATH = REPO_ROOT / "analytics_history.json"
NICHE_BOOST_PATH = REPO_ROOT / "niche_boosts.json"
ANALYTICS_SKIP_STREAK_THRESHOLD = 3   # consecutive skips before boosting scrape volume
NICHE_BOOST_MULTIPLIER = 2            # scrape this many times ITEMS_PER_SOURCE when boosted

# Named agent personas — single source of truth for report-card branding.
# Each squad/output-type is fronted by a named "agent" (Indian cricketers)
# that produces a per-run HTML report card (see reports/report_card.py).
REPORTS_DIR = REPO_ROOT / "reports"

# Notifications — daily roundup GitHub Issue + approval email
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
ROUNDUP_ISSUE_LABEL = "daily-roundup"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

AGENT_PROFILES = {
    "chief_of_staff":    {"name": "MS Dhoni",        "role": "Chief of Staff"},
    "squad1_intel":      {"name": "Vaibhav Suryavanshi", "role": "Intel Scout — Squad 1"},
    "squad2_newsletter": {"name": "Sourav Ganguly",      "role": "Newsletter Strategist — Squad 2"},
    "squad2_twitter":    {"name": "Rohit Sharma",        "role": "Thread Opener — Squad 2"},
    "squad2_reels":      {"name": "Jasprit Bumrah",      "role": "Reel Scriptwriter — Squad 2"},
    "squad3_production": {"name": "Abhishek Sharma",     "role": "Production Chief — Squad 3"},
    "squad6_analytics":  {"name": "Yuvraj Singh",        "role": "Analytics All-Rounder — Squad 6"},
}

# Per-agent Telegram bots — gives each named agent its own bot identity
# (own avatar/name in Telegram's sidebar) instead of one shared bot.
# Create one bot per agent via @BotFather and set its token below; agents
# without a configured token simply don't post (best-effort, per-agent).
# All agents share the same TELEGRAM_CHAT_ID (the same recipient/chat).
TELEGRAM_BOT_TOKENS = {
    agent_key: os.getenv(f"TELEGRAM_BOT_TOKEN_{agent_key.upper()}", "")
    for agent_key in AGENT_PROFILES
}
