# AI Media Empire

[![Daily Pipeline](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml/badge.svg)](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Last Commit](https://img.shields.io/github/last-commit/subhadeep-bose/ai-media-empire)](https://github.com/subhadeep-bose/ai-media-empire/commits/main)

> Autonomous multi-niche media content pipeline — scrapes 9 sources daily, generates 7 content pieces across 5 social accounts, and uploads them as a downloadable Actions artifact each run. Cost: $0.

**Niches:** AI/Tech · Gaming (PS5 + Steam Deck) · Bengali Literature · Cricket · Football · WWE · Movies & TV

**Stack:** Python 3.11 · Ollama/Llama3 (local) · Groq (fallback) · BeautifulSoup · GitHub Actions

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
              │  5 × Reel scripts        │
              └────────────┬────────────┘
                           │ bundle_YYYY-MM-DD.json
              ┌────────────▼────────────┐
              │  SQUAD 3 — Multimedia    │
              │  Edge-TTS voice + SRT    │
              │  Stock clips + FFmpeg    │
              │  YouTube/IG metadata     │
              └────────────┬────────────┘
                           │ squad3_output/YYYY-MM-DD
              ┌────────────▼────────────┐
              │  SQUAD 6 — Analytics     │
              │  Skip-streak tracking    │
              │  niche_boosts.json       │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   Chief of Staff Roundup │
              │  reports/YYYY-MM-DD      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   daily-content Artifact │
              │  (uploaded every run)   │
              └─────────────────────────┘
                           │
                    Manual Post
              (Instagram · Twitter · Beehiiv · YouTube)
```

`niche_boosts.json` feeds back into Squad 1's next run, scraping more aggressively for niches
that have gone quiet — closing the loop without manual tuning.

---

## Named Agents

Each squad runs under a named persona (Indian cricketers) and files a dark-themed HTML
report card to `reports/YYYY-MM-DD/` every run, summarised by a Chief of Staff roundup card:

| Agent | Role |
|---|---|
| MS Dhoni | Chief of Staff — daily roundup |
| Vaibhav Suryavanshi | Intel Scout — Squad 1 |
| Sourav Ganguly | Newsletter Strategist — Squad 2 |
| Rohit Sharma | Thread Opener — Squad 2 |
| Jasprit Bumrah | Reel Scriptwriter — Squad 2 |
| Abhishek Sharma | Production Chief — Squad 3 |
| Yuvraj Singh | Analytics All-Rounder — Squad 6 |

Report cards are included in the `daily-content-*` Actions artifact alongside scripts and media.

---

## Features

- **9 scrapers** — GitHub Trending, arXiv CS.AI, Reddit r/artificial, Reddit r/soccer, Reddit r/movies, Reddit r/SteamDeck, ESPNcricinfo, WrestlingInc, Goodreads Bengali shelf
- **7 content generators** — AI newsletter, Twitter thread, and 5 Instagram Reel scripts (AI/Tech, Sports, Bengali Books, Movies, Gaming)
- **Ollama + Groq dual-LLM** — local-first with cloud fallback, zero hard dependency on paid APIs
- **Deduplication** — SHA-256 hash index in `seen_items.json` prevents re-processing items across runs
- **Real RSS extraction** — Reddit content tags stripped of HTML and truncated, not hardcoded placeholder text
- **Parallel generation** — `ThreadPoolExecutor(max_workers=3)` for Squad 2 to respect API TPM limits
- **File locking** — `fcntl.flock` on Linux to prevent concurrent write corruption of `seen_items.json`
- **Hallucination guards** — sports and Bengali book scripts include strict "ONLY use facts from the digest" rules
- **Multimedia production** — Edge-TTS voiceover + SRT captions + Pexels stock clips assembled into vertical video via FFmpeg, plus YouTube/Instagram metadata generation
- **Self-healing orchestration** — `main.py` retries a failed squad with incremental backoff before giving up; TTS synthesis itself retries on transient `edge-tts` failures
- **Analytics feedback loop** — Squad 6 tracks consecutive skip streaks per niche and boosts next-run scrape volume for niches that have gone quiet
- **Named agents + report cards** — every squad files a per-run HTML report card under a named persona, rolled up into a daily Chief of Staff summary

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/subhadeep-bose/ai-media-empire
cd ai-media-empire

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest ruff  # dev-only, not needed at runtime

# 3. Optional: start local Ollama (falls back to Groq if unavailable)
ollama pull llama3:8b
ollama serve

# 4. Set environment variables (or add to .env)
export GROQ_API_KEY=your_key_here
export PEXELS_API_KEY=your_key_here  # optional — enables Squad 3 video assembly

# 5. Run the full pipeline (or run main.py to chain all squads with retries)
python squad1_intel/squad1_run.py
python squad2_content/squad2_run.py
python squad3_production/squad3_run.py
python squad6_analytics/analytics_run.py
python chief_of_staff.py

# 6. Run tests and lint
pytest tests/ -v
ruff check .
```

FFmpeg must also be installed and on `PATH` for Squad 3's video assembly step.

---

## GitHub Actions Setup

1. Fork or push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add the secret: `GROQ_API_KEY` (from [console.groq.com](https://console.groq.com) — free tier)
4. Optional: add `PEXELS_API_KEY` (from [pexels.com/api](https://www.pexels.com/api/)) to enable Squad 3's stock-footage video assembly — without it, Squad 3 still produces audio, captions, and metadata, just no assembled `.mp4`
5. Optional: add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFY_EMAIL_TO` to enable the daily approval email (see [Daily notifications](#daily-notifications) below) — `GITHUB_TOKEN` is provided automatically, no secret needed for the GitHub Issue roundup
6. The pipeline runs automatically at **06:00 UTC** every day
7. Trigger manually from the **Actions** tab → **Daily media empire run** → **Run workflow**

Pull requests are checked by a separate `lint.yml` workflow: conventional-commit linting, `ruff check .`, and `pytest tests/ -v`.

---

## Reviewing daily output

Each scheduled run uploads its full output (digest, scripts, audio, video, captions, metadata) as a
`daily-content-<run_id>` artifact on the **Actions** tab (retained 7 days) — download it from there to
review and approve before posting manually.

### Daily notifications

`notify.py` runs after the Chief of Staff roundup and surfaces it through two best-effort,
independently optional channels — missing credentials for one just logs a warning and skips it,
the other still runs:

- **GitHub Issue** — opens (or comments on, if already open) a `daily-roundup`-labelled issue
  with the day's summary and a link to the Actions run. Uses the automatically-provided
  `GITHUB_TOKEN`, no extra secret needed.
- **Approval email** — emails the Squad 2 approval draft plus the roundup summary via SMTP.
  Needs `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `NOTIFY_EMAIL_TO` as repo
  secrets (for Gmail: an [app password](https://myaccount.google.com/apppasswords), not your
  account password).
- **Telegram dashboard** — sends a stat-tile snapshot of the full day's run (items collected,
  reels written, audio/video produced, per-squad breakdown, top items) to a Telegram chat.
  `dashboard.py` builds a dark-themed HTML dashboard from the per-agent report-card JSON
  sidecars and renders it to a PNG via headless Chromium (Playwright); the PNG is sent with
  `sendPhoto`, falling back to a text-only `sendMessage` if PNG rendering isn't available.
  Needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repo secrets — create a bot via
  [@BotFather](https://t.me/BotFather) and get your chat ID from
  [@userinfobot](https://t.me/userinfobot) or the `getUpdates` API.

#### Per-agent Telegram bots

In addition to the single roundup bot above, each named agent (see `config.AGENT_PROFILES`) can
post its own report card to Telegram under its own bot identity — its own name and avatar in
Telegram's chat list, separate from the others. `telegram_bot.py:send_agent_update()` is called by
each squad script right after it renders its report card; it screenshots that agent's HTML card to
PNG (via the same `reports/png_render.py` helper `dashboard.py` uses) and sends it through that
agent's bot.

This is entirely optional and per-agent independent — an agent only posts if its bot token is set.
Create one bot per agent via @BotFather and set `TELEGRAM_BOT_TOKEN_<AGENT_KEY>` (e.g.
`TELEGRAM_BOT_TOKEN_SQUAD1_INTEL`) as a repo secret; all agents share the same `TELEGRAM_CHAT_ID`.
See `.env.example` for the full list of per-agent variable names.

A separate, pre-existing `Alert on failure` step in `daily_run.yml` opens a `pipeline-failure`-labelled
issue if the run fails outright, independent of `notify.py`.

---

## Project Structure

```
ai-media-empire/
├── config.py                  # All constants and paths (single source of truth)
├── llm.py                     # Shared Ollama + Groq LLM module
├── main.py                    # Pipeline orchestrator (Squad1 -> Squad2 -> Squad3 -> Squad6 -> Chief of Staff)
├── chief_of_staff.py          # Aggregates each agent's report card into a daily roundup
├── notify.py                  # Posts the roundup as a GitHub Issue + sends the approval email
├── dashboard.py                # Builds a stat-tile HTML/PNG dashboard for Telegram delivery
├── telegram_bot.py             # Per-agent Telegram bot sender (own bot identity per agent)
├── reports/
│   └── report_card.py         # Shared HTML report-card renderer for named agents
│
├── squad1_intel/
│   ├── scrapers.py            # 9 source scrapers with dedup + rate limiting
│   └── squad1_run.py          # Squad 1 orchestrator
│
├── squad2_content/
│   └── squad2_run.py          # Squad 2 parallel content generator
│
├── squad2_output/
│   ├── bundle_YYYY-MM-DD.json # Full content bundle per day
│   └── YYYY-MM-DD/            # Individual script files + approval email
│
├── squad3_production/
│   ├── squad3_run.py          # Squad 3 orchestrator
│   ├── tts.py                 # Edge-TTS voiceover + SRT captions (retries on transient failures)
│   ├── visuals.py             # Pexels stock-clip fetcher
│   ├── video.py                # FFmpeg assembly of voiceover + captions + clips
│   └── metadata.py            # YouTube/Instagram metadata generation
│
├── squad3_output/
│   └── YYYY-MM-DD/<niche>/    # audio.mp3, captions.srt, video.mp4, youtube_meta.json, instagram_caption.txt
│
├── squad6_analytics/
│   └── analytics_run.py       # Tracks per-niche skip streaks, writes niche_boosts.json
│
├── tests/
│   ├── __init__.py
│   ├── test_scrapers.py       # Unit tests for dedup, truncation, error format
│   ├── test_llm.py            # Unit tests for Groq retry, fallback, error handling
│   ├── test_squad2.py         # Niche-section extraction and reel-generator tests
│   ├── test_squad3.py         # TTS, captions, metadata tests
│   ├── test_squad3_video.py   # Stock-clip fetch + FFmpeg assembly tests
│   ├── test_analytics.py      # Skip-streak tracking tests
│   ├── test_chief_of_staff.py # Report-card roundup aggregation tests
│   ├── test_notify.py         # GitHub Issue + approval email notification tests
│   ├── test_report_card.py    # HTML report-card renderer tests
│   ├── test_dashboard.py      # Stat-tile dashboard builder tests
│   └── test_main_resilience.py# Squad retry/backoff orchestration tests
│
├── .github/
│   ├── workflows/
│   │   ├── daily_run.yml      # Main pipeline (scrape → generate → produce → test → upload artifact)
│   │   └── lint.yml           # Conventional commits, ruff, pytest on every PR
│   ├── copilot-instructions.md
│   └── pull_request_template.md
│
├── ruff.toml                  # Lint config (line length, ignored rules)
├── commitlint.config.js       # Conventional-commit type/scope rules
├── seen_items.json            # Dedup index (committed back after each run)
├── master_intel_digest.md     # LLM-processed intel digest (Squad 1 output)
├── analytics_history.json     # Squad 6 — per-niche skip-streak history
├── niche_boosts.json          # Squad 6 — niches Squad 1 should scrape harder next run
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
| `PEXELS_API_KEY` | No | Enables Squad 3 stock-footage video assembly; without it, video assembly is skipped |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `NOTIFY_EMAIL_TO` | No | Enables the daily approval email from `notify.py`; without all five, the email is skipped |
| `GITHUB_TOKEN` | No (auto-set in Actions) | Enables the daily roundup GitHub Issue from `notify.py`; without it, the issue post is skipped |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | No | Enables the Telegram dashboard snapshot from `notify.py`; without both, the Telegram send is skipped |
| `TELEGRAM_BOT_TOKEN_<AGENT_KEY>` (e.g. `TELEGRAM_BOT_TOKEN_SQUAD1_INTEL`) | No | Per-agent bot token from `telegram_bot.py`, one per `config.AGENT_PROFILES` key; an agent without its token configured just skips its own Telegram update. Shares `TELEGRAM_CHAT_ID` above |

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
| `SKIP_MARKERS` | see `config.py` | Sentinel strings Squad 2 writes (and Squad 3 reads) when a niche has no real content |
| `VIDEO_WIDTH` / `VIDEO_HEIGHT` | `1080` / `1920` | Output video resolution (portrait/Reels) |
| `STOCK_CLIPS_PER_REEL` | `3` | Stock clips fetched per assembled video |
| `SQUAD_RETRY_ATTEMPTS` | `2` | Extra retries per squad in `main.py` before giving up |
| `SQUAD_RETRY_WAIT_BASE_SECS` | `30` | Backoff base (seconds) between squad retries |
| `SQUAD_TIMEOUT_SECS` | `600` | Max seconds a squad subprocess may run |
| `ANALYTICS_SKIP_STREAK_THRESHOLD` | `3` | Consecutive skips before Squad 6 boosts scrape volume |
| `NICHE_BOOST_MULTIPLIER` | `2` | Scrape multiplier applied to boosted niches |
| `AGENT_PROFILES` | see `config.py` | Named-persona → role mapping used by report cards |

---

## Roadmap

| Squad | Status | Description |
|---|---|---|
| Squad 1 — Intel | ✅ Live | 9-source scraper with dedup and LLM digest |
| Squad 2 — Content | ✅ Live | 7 parallel script generators |
| Squad 3 — Multimedia | ✅ Live | Edge-TTS voice + FFmpeg video assembly |
| Squad 4 — Monetise | 🔜 Phase 4 | Affiliate links + sponsor outreach |
| Squad 5 — Infra | ✅ Live | Self-healing, alerting, retry orchestration |
| Squad 6 — Analytics | ✅ Live | Performance feedback loop into Squad 1 |
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
