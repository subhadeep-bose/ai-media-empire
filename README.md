# AI Media Empire

[![Daily Pipeline](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml/badge.svg)](https://github.com/subhadeep-bose/ai-media-empire/actions/workflows/daily_run.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Last Commit](https://img.shields.io/github/last-commit/subhadeep-bose/ai-media-empire)](https://github.com/subhadeep-bose/ai-media-empire/commits/main)

> Autonomous multi-niche media content pipeline — scrapes 30+ sources daily, generates 9 content pieces across 5 niches, auto-publishes to Twitter with Telegram approval, and uploads everything as a downloadable Actions artifact each run. Cost: $0.

**Niches:** AI/Tech · Gaming (PS5 + Steam Deck) · Bengali Literature · Cricket · Football · WWE · Movies & TV

**Stack:** Python 3.11 · Ollama/Llama3 (local) · Groq (fallback) · BeautifulSoup · tweepy · Pillow · GitHub Actions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (06:00 UTC)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │      SQUAD 1 — Intel     │
              │  30+ scrapers (RSS/HTML) │
              │  Dedup · Rate limit      │
              │  Ollama → Groq fallback  │
              └────────────┬────────────┘
                           │ master_intel_digest.md
              ┌────────────▼────────────┐
              │     SQUAD 2 — Content    │
              │  9 generators (parallel) │
              │  Newsletter · Thread     │
              │  Hot Take · Weekly Poll  │
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
              │  SQUAD 4 — Publishing    │
              │  Telegram approval gate  │
              │  Pillow tweet cards      │
              │  tweepy v4 → Twitter     │
              └────────────┬────────────┘
                           │ thread_history.json
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
              │  (uploaded every run)    │
              └─────────────────────────┘
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
| Hardik Pandya | Publishing Engine — Squad 4 |
| Yuvraj Singh | Analytics All-Rounder — Squad 6 |

Report cards are included in the `daily-content-*` Actions artifact alongside scripts and media.

---

## Features

- **30+ scrapers** — TLDR AI, Hacker News (Algolia), arXiv CS.AI, r/MachineLearning, r/artificial, r/LocalLLaMA, VentureBeat AI, MIT Tech Review, The Verge AI, Ben's Bites, GitHub Trending (AI/Tech) · r/PS5, IGN, Eurogamer, PC Gamer, Rock Paper Shotgun, r/SteamDeck (Gaming) · BBC Sport, CricBuzz, r/Cricket, r/soccer, r/SquaredCircle (Sports) · Variety, Hollywood Reporter, Deadline, r/movies, r/television (Movies & TV) · Goodreads Bengali shelf
- **9 content generators** — AI newsletter, 7-tweet thread with reply-bait closer, daily hot take, Monday poll, and 5 Instagram Reel scripts (AI/Tech, Sports, Bengali Books, Movies, Gaming)
- **Squad 4 auto-publishing** — Telegram inline-keyboard approval gate → Pillow-rendered branded tweet cards → tweepy v4 posts to Twitter; hero card on tweet 1 only, tweets 2–7 plain text for reach
- **Delayed hot take** — Squad 2 stages the hot take to `pending_hot_take.json`; `tweet_hot_take.yml` fires at 12:00 UTC (+6 h) to post it separately for a second engagement window
- **Weekly pin rotation** — every Sunday, `pin_best_thread.yml` fetches impression counts for the last 7 threads and pins the winner; falls back to a Telegram notification if the account is on free tier
- **Ollama + Groq dual-LLM** — local-first with cloud fallback, zero hard dependency on paid APIs
- **Deduplication** — SHA-256 hash index in `seen_items.json` prevents re-processing items across runs
- **Parallel generation** — `ThreadPoolExecutor(max_workers=3)` for Squad 2 to respect API TPM limits
- **Hallucination guards** — all generators use `extract_niche_section()` to filter the digest to their niche before calling the LLM; sports and Bengali book scripts have additional strict "ONLY use facts from the digest" rules
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

# 4. Set environment variables
export GROQ_API_KEY=your_key_here
export PEXELS_API_KEY=your_key_here      # optional — enables Squad 3 video assembly
export TWITTER_API_KEY=your_key_here     # required for Squad 4 Twitter posting
export TWITTER_API_SECRET=your_key_here
export TWITTER_ACCESS_TOKEN=your_key_here
export TWITTER_ACCESS_TOKEN_SECRET=your_key_here
export TWITTER_HANDLE=@yourhandle        # shown on tweet card footer

# 5. Run the full pipeline
python squad1_intel/squad1_run.py
python squad2_content/squad2_run.py
python squad3_production/squad3_run.py
python squad4_publish/squad4_run.py      # opens Telegram approval, then posts to Twitter
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
3. Add the required secrets:

| Secret | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes (if no Ollama) | From [console.groq.com](https://console.groq.com) — free tier |
| `TWITTER_API_KEY` | Yes (Squad 4) | Twitter Developer Portal → your app |
| `TWITTER_API_SECRET` | Yes (Squad 4) | Twitter Developer Portal → your app |
| `TWITTER_ACCESS_TOKEN` | Yes (Squad 4) | Generate for your account in the Developer Portal |
| `TWITTER_ACCESS_TOKEN_SECRET` | Yes (Squad 4) | Generate for your account in the Developer Portal |
| `TWITTER_HANDLE` | No | Your `@handle` — shown on tweet card footer |
| `PEXELS_API_KEY` | No | From [pexels.com/api](https://www.pexels.com/api/) — enables Squad 3 video |
| `TELEGRAM_BOT_TOKEN` | No | Enables Squad 4 approval gate + Telegram dashboard |
| `TELEGRAM_CHAT_ID` | No | Your Telegram chat ID (from [@userinfobot](https://t.me/userinfobot)) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `NOTIFY_EMAIL_TO` | No | Enables daily approval email |

4. The pipeline runs automatically at **06:00 UTC** daily; the delayed hot take posts at **12:00 UTC**; pin rotation runs every **Sunday at 18:00 UTC**
5. Trigger manually from the **Actions** tab → **Daily media empire run** → **Run workflow**

Pull requests are checked by a separate `lint.yml` workflow: conventional-commit linting, `ruff check .`, and `pytest tests/ -v`.

### Workflows

| Workflow | Schedule | Description |
|---|---|---|
| `daily_run.yml` | 06:00 UTC daily | Full pipeline: Squad 1 → 2 → 3 → 4 → 6 → Chief of Staff |
| `tweet_hot_take.yml` | 12:00 UTC daily | Posts the staged hot take from `pending_hot_take.json` |
| `pin_best_thread.yml` | 18:00 UTC Sunday | Checks impression counts for last 7 threads, pins the winner |
| `lint.yml` | Every PR | Conventional commits, ruff, pytest |
| `api_health_check.yml` | Weekly | Pings Groq/Pexels/Telegram, opens an issue if any key is invalid |
| `manual_retry.yml` | On demand | Re-runs a single squad without redoing the whole day |
| `weekly_trend_digest.yml` | Weekly | Posts a per-niche skip-streak health summary to Telegram |

### --date override

Every squad script accepts an optional `--date YYYY-MM-DD` flag (`runtime_args.py`), defaulting to today. This only controls which `date_str` the run's output is filed under — scrapers always fetch live data.

### Moderation pass

Squad 3 checks each script against a small denylist (`config.MODERATION_DENYLIST`) before TTS/video assembly. A flagged niche is skipped the same way an empty niche is — this is a blunt safety net for an obvious LLM slip, not a full moderation system.

### Groq usage tracking

`llm.py` records each Groq call's `total_tokens` to `llm_usage_history.json` via `usage_tracker.py`. The Chief of Staff roundup card shows the day's running total under "Groq Tokens Used Today".

---

## Reviewing daily output

Each scheduled run uploads its full output (digest, scripts, audio, video, captions, metadata) as a `daily-content-<run_id>` artifact on the **Actions** tab (retained 7 days). Squad 4's Telegram approval gate lets you review and approve Twitter content directly on your phone before it posts.

### Daily notifications

`notify.py` runs after the Chief of Staff roundup and surfaces it through three optional channels:

- **GitHub Issue** — opens (or comments on) a `daily-roundup`-labelled issue with the day's summary. Uses the auto-provided `GITHUB_TOKEN`, no extra secret needed.
- **Approval email** — emails the Squad 2 approval draft plus the roundup summary via SMTP. Needs `SMTP_*` secrets.
- **Telegram dashboard** — sends a stat-tile PNG snapshot of the full run to a Telegram chat. Needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

#### Per-agent Telegram bots

Each named agent can post its own report card under its own bot identity (own avatar/name in Telegram). Set `TELEGRAM_BOT_TOKEN_<AGENT_KEY>` (e.g. `TELEGRAM_BOT_TOKEN_SQUAD4_PUBLISH`) as a repo secret; all agents share the same `TELEGRAM_CHAT_ID`. See `.env.example` for the full list.

---

## Project Structure

```
ai-media-empire/
├── config.py                  # All constants and paths (single source of truth)
├── llm.py                     # Shared Ollama + Groq LLM module
├── main.py                    # Pipeline orchestrator (Squad1 → 2 → 3 → 4 → 6 → Chief of Staff)
├── chief_of_staff.py          # Aggregates each agent's report card into a daily roundup
├── notify.py                  # Posts roundup as GitHub Issue + approval email + Telegram
├── dashboard.py               # Builds stat-tile HTML/PNG dashboard for Telegram delivery
├── telegram_bot.py            # Per-agent Telegram bot sender
├── post_hot_take.py           # Entrypoint for tweet_hot_take.yml delayed posting workflow
├── reports/
│   └── report_card.py         # Shared HTML report-card renderer for named agents
│
├── squad1_intel/
│   ├── scrapers.py            # 30+ source scrapers with dedup + rate limiting
│   └── squad1_run.py          # Squad 1 orchestrator
│
├── squad2_content/
│   └── squad2_run.py          # 9 parallel content generators
│
├── squad2_output/
│   ├── bundle_YYYY-MM-DD.json # Full content bundle per day
│   └── YYYY-MM-DD/            # Individual script files + approval email
│
├── squad3_production/
│   ├── squad3_run.py          # Squad 3 orchestrator
│   ├── tts.py                 # Edge-TTS voiceover + SRT captions
│   ├── visuals.py             # Pexels stock-clip fetcher
│   ├── video.py               # FFmpeg assembly
│   └── metadata.py            # YouTube/Instagram metadata generation
│
├── squad3_output/
│   └── YYYY-MM-DD/<niche>/    # audio.mp3, captions.srt, video.mp4, metadata JSON
│
├── squad4_publish/
│   ├── squad4_run.py          # Squad 4 orchestrator — approval → brand → post
│   ├── approval_bot.py        # Telegram inline-keyboard approval gate
│   ├── tweet_card.py          # Pillow renderer: hero card (thread) + hot-take card
│   ├── twitter_publisher.py   # tweepy v4: post_thread / post_hot_take / post_poll / pin
│   └── pin_best_thread.py     # Weekly pin rotation entrypoint
│
├── squad6_analytics/
│   └── analytics_run.py       # Tracks per-niche skip streaks, writes niche_boosts.json
│
├── tests/
│   ├── test_scrapers.py
│   ├── test_llm.py
│   ├── test_squad2.py         # 22 tests covering generators + niche extraction
│   ├── test_squad3.py
│   ├── test_squad3_video.py
│   ├── test_analytics.py
│   ├── test_chief_of_staff.py
│   ├── test_notify.py
│   ├── test_report_card.py
│   ├── test_dashboard.py
│   └── test_main_resilience.py
│
├── .github/
│   └── workflows/
│       ├── daily_run.yml
│       ├── tweet_hot_take.yml
│       ├── pin_best_thread.yml
│       ├── lint.yml
│       ├── api_health_check.yml
│       ├── manual_retry.yml
│       └── weekly_trend_digest.yml
│
├── pending_hot_take.json      # Staged hot take for delayed post (written by Squad 2)
├── thread_history.json        # Posted thread IDs for pin rotation (written by Squad 4)
├── seen_items.json            # Dedup index
├── master_intel_digest.md     # LLM-processed intel digest (Squad 1 output)
├── analytics_history.json     # Per-niche skip-streak history
├── niche_boosts.json          # Niches Squad 1 should scrape harder next run
├── requirements.txt
└── .env                       # Local secrets (never committed)
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes (if no Ollama) | Groq API key |
| `OLLAMA_MODEL` | No | Ollama model name (default: `llama3:8b`) |
| `TWITTER_API_KEY` / `TWITTER_API_SECRET` / `TWITTER_ACCESS_TOKEN` / `TWITTER_ACCESS_TOKEN_SECRET` | Yes (Squad 4) | Twitter OAuth 1.0a credentials |
| `TWITTER_HANDLE` | No | Your `@handle`, shown on tweet card footer |
| `BRAND_BG_COLOR` / `BRAND_ACCENT_COLOR` / `BRAND_TEXT_COLOR` | No | Tweet card colours (hex, default: `#0D1117` / `#6C63FF` / `#FFFFFF`) |
| `APPROVAL_TIMEOUT_SECS` | No | Seconds to wait for Telegram approval (default: `1800`) |
| `PEXELS_API_KEY` | No | Enables Squad 3 stock-footage video assembly |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | No | Enables Squad 4 approval gate + Telegram dashboard |
| `TELEGRAM_BOT_TOKEN_<AGENT_KEY>` | No | Per-agent bot token (e.g. `TELEGRAM_BOT_TOKEN_SQUAD4_PUBLISH`) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `NOTIFY_EMAIL_TO` | No | Enables daily approval email |

### config.py Settings

| Setting | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model ID |
| `GROQ_MAX_TOKENS_INTEL` | `2500` | Max tokens for digest generation |
| `GROQ_MAX_TOKENS_CONTENT` | `1000` | Max tokens per content piece |
| `GROQ_RATE_LIMIT_RETRIES` | `4` | Retry attempts on rate limit |
| `GROQ_RATE_LIMIT_WAIT_BASE` | `15` | Base wait seconds (15, 30, 45, 60) |
| `SCRAPER_TIMEOUT` | `10` | HTTP request timeout in seconds |
| `ITEMS_PER_SOURCE` | `5` | Max items fetched per scraper |
| `TWEET_CARD_WIDTH` / `TWEET_CARD_HEIGHT` | `1200` / `675` | Tweet card PNG dimensions |
| `SKIP_MARKERS` | see `config.py` | Sentinel strings Squad 2 writes when a niche has no real content |
| `VIDEO_WIDTH` / `VIDEO_HEIGHT` | `1080` / `1920` | Output video resolution (portrait/Reels) |
| `SQUAD_RETRY_ATTEMPTS` | `2` | Extra retries per squad in `main.py` |
| `ANALYTICS_SKIP_STREAK_THRESHOLD` | `3` | Consecutive skips before Squad 6 boosts scrape volume |
| `NICHE_BOOST_MULTIPLIER` | `2` | Scrape multiplier applied to boosted niches |
| `AGENT_PROFILES` | see `config.py` | Named-persona → role mapping used by report cards |

---

## Roadmap

| Squad | Status | Description |
|---|---|---|
| Squad 1 — Intel | ✅ Live | 30+ source scraper with dedup and LLM digest |
| Squad 2 — Content | ✅ Live | 9 parallel generators (newsletter, thread, hot take, poll, 5 reels) |
| Squad 3 — Multimedia | ✅ Live | Edge-TTS voice + FFmpeg video assembly |
| Squad 4 — Publishing | ✅ Live | Telegram approval → Pillow cards → Twitter auto-post + pin rotation |
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
