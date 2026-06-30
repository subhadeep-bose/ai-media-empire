# CLAUDE.md — Claude Code Instructions for ai-media-empire

This file is read automatically at the start of every Claude Code session.
Follow all rules here without being asked.

---

## Identity

This is an autonomous multi-niche media content pipeline. It scrapes 9 sources,
runs LLM summarisation (Ollama → Groq fallback), and generates 7 daily content
scripts across AI/Tech, Sports, Bengali Books, Movies, and Gaming niches.

---

## Branch & Commit Rules (non-negotiable)

### Always work on a feature branch
- NEVER commit directly to `main`
- Branch naming: `feature/<short-description>` or `fix/<short-description>`
- Create from latest main: `git checkout main && git pull && git checkout -b feature/your-thing`

### Conventional Commits — required format
```
<type>(<optional-scope>): <description>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Allowed types:**
| Type | When to use |
|------|-------------|
| `feat` | New scraper, generator, squad, or user-facing capability |
| `fix` | Bug fix in existing pipeline behaviour |
| `refactor` | Code restructure with no behaviour change |
| `test` | Adding or fixing tests |
| `ci` | Workflow / GitHub Actions changes |
| `docs` | README, CLAUDE.md, comments |
| `chore` | Deps, config, dedup index, generated files |

**Examples:**
```
feat(squad1): add Hacker News scraper with dedup
fix(llm): handle Groq 429 with exponential backoff
refactor: extract shared scraper base class
test(scrapers): add mock tests for cricket feed
ci: add commitlint check on pull requests
docs: update README with Squad 3 setup instructions
chore(deps): bump requests to 2.32.0
```

### PR rules
- Always create a PR from feature branch → main
- Never merge your own PR (leave it for review)
- PR title must follow conventional commit format
- Fill in the PR template fully

---

## Project Structure

```
config.py               # All magic numbers, paths, model names, AGENT_PROFILES — edit here first
llm.py                  # Shared Ollama→Groq LLM module — single source of truth
main.py                 # Pipeline orchestrator: Squad1 → Squad2 → Squad3 → Squad6 → Chief of Staff
chief_of_staff.py       # Aggregates per-agent report cards into a daily roundup card
reports/
  report_card.py        # Shared HTML report-card renderer used by every squad
squad1_intel/
  scrapers.py           # 9 scrapers — each returns List[dict] or [{"error": ...}]
  squad1_run.py         # Orchestrates scrapers → LLM digest
squad2_content/
  squad2_run.py         # Parallel LLM content generation (ThreadPoolExecutor)
tests/                  # pytest — run before every commit
.github/workflows/
  daily_run.yml         # Scheduled pipeline + artifact upload (daily-content-*)
  lint.yml              # Commitlint + PR checks
```

Repo is private — no GitHub Pages (requires GitHub Enterprise on private repos). Review daily
output via the `daily-content-*` artifact on each Actions run instead of a hosted dashboard.

Each squad is fronted by a named agent persona (Indian cricketers — see `config.AGENT_PROFILES`)
that calls `reports/report_card.py:render_report_card()` at the end of its run to file a per-run
HTML report card to `reports/YYYY-MM-DD/`. `chief_of_staff.py` runs last and aggregates every
agent's card into a daily roundup. When adding a new squad or generator, add its persona to
`AGENT_PROFILES` and have it render a report card — don't hardcode names inline.

---

## Coding Standards

- Use `logging` not `print` (logger = `logging.getLogger(__name__)`)
- Import paths and constants from `config.py` — never hardcode
- Import LLM calls from `llm.py` — never inline Groq/Ollama calls
- Each scraper returns `List[dict]` — on error return `[{"platform": "X", "error": "..."}]`
- Summaries must be truncated to `config.SUMMARY_MAX_CHARS` before passing to LLM
- All secrets come from environment variables — never write a `.env` file in CI
- Run `pytest tests/ -v` before committing — all tests must pass

---

## What NOT to do

- Don't push to `main` directly
- Don't hardcode API keys, model names, or file paths
- Don't use `print()` for logging
- Don't write `.env` files in CI steps
- Don't use `git push || true` — use retry loops
- Don't skip tests
- Don't add squads 3–8 until squad1+2 are stable (check Actions history first)
