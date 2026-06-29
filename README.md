# AI Media Empire

Autonomous multi-agent content system covering 5 niches across 5 social accounts.

**Niches:** AI/Tech · Gaming (PS5 + Steam Deck) · Bengali Literature · Cricket/Football/WWE · Movies & TV

**Stack:** Python · Ollama/Llama3 (local) · Groq (fallback) · Edge-TTS · FFmpeg · MoviePy · GitHub Actions

**Cost:** $0

---

## Quick start

```bash
# 1. Clone and enter
git clone https://github.com/YOUR_USERNAME/ai-media-empire
cd ai-media-empire

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up secrets
cp .env.example .env
# Edit .env with your keys

# 4. Start Ollama (needed for local LLM)
ollama pull llama3:8b
ollama serve

# 5. Run the full pipeline
python main.py
```

---

## Architecture

```
Squad 1 (Intel)      → scrapes 9 sources daily → master_intel_digest.md
Squad 2 (Content)    → reads digest → 7 scripts for 5 accounts
Squad 3 (Multimedia) → voice + video assembly [ON HOLD]
Squad 4 (Monetise)   → affiliate links + sponsor outreach [PHASE 4]
Squad 5 (Infra)      → self-healing + error recovery
Squad 6 (Analytics)  → feedback loop into Squad 1 [PHASE 3]
Squad 7 (Audience)   → subscriber segmentation [PHASE 4]
Squad 8 (Brand)      → copyright + tone enforcement [PHASE 5]
```

## Daily flow

1. GitHub Actions triggers at 6am UTC (11:30am IST)
2. Squad 1 scrapes all sources with deduplication + rate limiting
3. Squad 2 generates 7 scripts (newsletter + 6 Reel scripts)
4. Approval email draft saved to `squad2_output/YYYY-MM-DD/`
5. You approve via Claude.ai Gmail MCP → post manually or via platform APIs

## GitHub Secrets needed

Go to repo Settings → Secrets → Actions and add:

- `GROQ_API_KEY` — from console.groq.com (free)
- `PEXELS_API_KEY` — from pexels.com/api (free)
- `AMAZON_AFFILIATE_TAG` — from Amazon Associates
- `BEEHIIV_API_KEY` — from beehiiv.com dashboard
---

## Phase roadmap

| Phase | Timeline | Goal |
|-------|----------|------|
| 1 | Weeks 1–2 | Stable daily pipeline |
| 2 | Weeks 3–5 | Hub account live, 100 subs |
| 3 | Weeks 6–9 | Video + 3 accounts, analytics |
| 4 | Weeks 10–14 | All 5 accounts, first affiliate revenue |
| 5 | Months 4–6 | First newsletter sponsor |
| 6 | Months 7–12 | $1k–$3k/month compounding |
