# AI Media Empire

[![Daily Pipeline](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml/badge.svg)](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-live-brightgreen)](https://subhadeep-bose.github.io/ai-media-empire/)
[![Last Commit](https://img.shields.io/github/last-commit/subhadeep-bose/ai-media-empire)](https://github.com/subhadeep-bose/ai-media-empire/commits/main)

> Autonomous multi-niche media content pipeline — scrapes 9 sources daily, generates 7 content pieces across 5 social accounts, and publishes a live dashboard. Cost: $0.

**Niches:** AI/Tech · Gaming (PS5 + Steam Deck) · Bengali Literature · Cricket · Football · WWE · Movies & TV

**Stack:** Python 3.11 · Ollama/Llama3 (local) · Groq (fallback) · BeautifulSoup · GitHub Actions · GitHub Pages

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (06:00 UTC)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │      SQUAD 1 — Intel     │
              │  9 scrapers (RSS/HTML)   │
              │  Dedup · Rate limit      │
              │  Ollama → Groq fallback  │
              └────────────┬────────────┘
                           │ master_intel_digest.md
              ┌────────────▼────────────┐
              │     SQUAD 2 — Content    │
              │  7 generators (parallel) │
              │  Newsletter · Thread     │
              │  6 × Reel scripts        │
              └────────────┬────────────┘
                           │ bundle_YYYY-MM-DD.json
              ┌────────────▼────────────┐
              │   Approval Email Draft   │
              │  squad2_output/YYYY-MM-DD│
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  GitHub Pages Dashboard  │
              │  docs/index.html (auto)  │
              └─────────────────────────┘
                           │
                    Manual Post
              (Instagram · Twitter · Beehiiv)
```

---

## Features

- **9 scrapers** — GitHub Trending, arXiv CS.AI, Reddit r/artificial, Reddit r/soccer, Reddit r/movies, Reddit r/SteamDeck, ESPNcricinfo, WrestlingInc, Goodreads Bengali shelf
- **7 content generators** — AI newsletter, Twitter thread, and 5 Instagram Reel scripts (AI/Tech, Sports, Bengali Books, Movies, Gaming)
- **Ollama + Groq dual-LLM** — local-first with cloud fallback, zero hard dependency on paid APIs
- **Deduplication** — SHA-256 hash index in `seen_items.json` prevents re-processing items across runs
- **Real RSS extraction** — Reddit content tags stripped of HTML and truncated, not hardcoded placeholder text
- **Parallel generation** — `ThreadPoolExecutor(max_workers=3)` for Squad 2 to respect API TPM limits
- **GitHub Pages dashboard** — auto-generated `docs/index.html` after every run
- **File locking** — `fcntl.flock` on Linux to prevent concurrent write corruption of `seen_items.json`
- **Hallucination guards** — sports and Bengali book scripts include strict "ONLY use facts from the digest" rules

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/subhadeep-bose/ai-media-empire
cd ai-media-empire

# 2. Install dependencies
pip install requests beautifulsoup4 python-dotenv lxml pytest

# 3. Optional: start local Ollama (falls back to Groq if unavailable)
ollama pull llama3:8b
ollama serve

# 4. Set environment variable (or add to .env)
export GROQ_API_KEY=your_key_here

# 5. Run the full pipeline
python squad1_intel/squad1_run.py
python squad2_content/squad2_run.py
python generate_site.py

# 6. Run tests
pytest tests/ -v
```

---

## GitHub Actions Setup

1. Fork or push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add the secret: `GROQ_API_KEY` (from [console.groq.com](https://console.groq.com) — free tier)
4. The pipeline runs automatically at **06:00 UTC** every day
5. Trigger manually from the **Actions** tab → **Daily media empire run** → **Run workflow**

---

## GitHub Pages Setup

1. Go to **Settings → Pages**
2. Set **Source** to **Deploy from a branch**
3. Set **Branch** to `main`, folder `/docs`
4. Click **Save**

The dashboard will be live at `https://<your-username>.github.io/ai-media-empire/` after the next pipeline run.

Alternatively, use the included `pages.yml` workflow which deploys automatically when `docs/` changes.

---

## Project Structure

```
ai-media-empire/
├── config.py                  # All constants and paths (single source of truth)
├── llm.py                     # Shared Ollama + Groq LLM module
├── generate_site.py           # Builds docs/index.html from latest bundle
├── main.py                    # Legacy entry point (calls both squads)
│
├── squad1_intel/
│   ├── scrapers.py            # 9 source scrapers with dedup + rate limiting
│   └── squad1_run.py          # Squad 1 orchestrator
│
├── squad2_content/
│   └── squad2_run.py          # Squad 2 parallel content generator
│
├── docs/
│   └── index.html             # Auto-generated GitHub Pages dashboard
│
├── squad2_output/
│   ├── bundle_YYYY-MM-DD.json # Full content bundle per day
│   └── YYYY-MM-DD/            # Individual script files + approval email
│
├── tests/
│   ├── __init__.py
│   ├── test_scrapers.py       # Unit tests for dedup, truncation, error format
│   └── test_llm.py            # Unit tests for Groq retry, fallback, error handling
│
├── .github/workflows/
│   ├── daily_run.yml          # Main pipeline (scrape → generate → test → deploy)
│   └── pages.yml              # GitHub Pages deployment on docs/ change
│
├── seen_items.json            # Dedup index (committed back after each run)
├── master_intel_digest.md     # LLM-processed intel digest (Squad 1 output)
├── requirements.txt
└── .env                       # Local secrets (never committed)
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes (if no Ollama) | Groq API key from console.groq.com |
| `OLLAMA_MODEL` | No | Ollama model name (default: `llama3:8b`) |

### config.py Settings

| Setting | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model ID |
| `GROQ_MAX_TOKENS_INTEL` | `1500` | Max tokens for digest generation |
| `GROQ_MAX_TOKENS_CONTENT` | `1000` | Max tokens per content piece |
| `GROQ_RATE_LIMIT_RETRIES` | `4` | Number of retry attempts on rate limit |
| `GROQ_RATE_LIMIT_WAIT_BASE` | `15` | Base wait seconds (15, 30, 45, 60) |
| `SCRAPER_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `RATE_LIMIT_SECS` | `2` | Sleep between scraper requests |
| `ITEMS_PER_SOURCE` | `5` | Max items fetched per scraper |
| `SUMMARY_MAX_CHARS` | `150` | Max chars for item summaries |

---

## Roadmap

| Squad | Status | Description |
|---|---|---|
| Squad 1 — Intel | ✅ Live | 9-source scraper with dedup and LLM digest |
| Squad 2 — Content | ✅ Live | 7 parallel script generators |
| Squad 3 — Multimedia | 🔜 Phase 3 | Edge-TTS voice + FFmpeg video assembly |
| Squad 4 — Monetise | 🔜 Phase 4 | Affiliate links + sponsor outreach |
| Squad 5 — Infra | 🔜 Phase 3 | Self-healing, alerting, retry orchestration |
| Squad 6 — Analytics | 🔜 Phase 3 | Performance feedback loop into Squad 1 |
| Squad 7 — Audience | 🔜 Phase 4 | Subscriber segmentation and personalisation |
| Squad 8 — Brand | 🔜 Phase 5 | Copyright checking + tone enforcement |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Run tests: `pytest tests/ -v`
4. Open a pull request

Please keep scrapers respectful of rate limits and do not hardcode credentials.

---

## License

MIT © Subhadeep Bose — see [LICENSE](LICENSE) for details.
