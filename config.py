from pathlib import Path
import os

REPO_ROOT = Path(__file__).parent

# LLM
GROQ_MODEL = "llama-3.1-8b-instant"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
GROQ_MAX_TOKENS_INTEL = 1500
GROQ_MAX_TOKENS_CONTENT = 1000
GROQ_RATE_LIMIT_RETRIES = 4
GROQ_RATE_LIMIT_WAIT_BASE = 15

# Scrapers
SCRAPER_TIMEOUT = 10
RATE_LIMIT_SECS = 2
ITEMS_PER_SOURCE = 5
SUMMARY_MAX_CHARS = 150

# Paths
SEEN_ITEMS_PATH = REPO_ROOT / "seen_items.json"
DIGEST_PATH = REPO_ROOT / "master_intel_digest.md"
OUTPUT_DIR = REPO_ROOT / "squad2_output"
LOG_DIR = REPO_ROOT / "logs"

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
