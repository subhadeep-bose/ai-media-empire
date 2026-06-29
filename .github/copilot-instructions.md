# GitHub Copilot Instructions — ai-media-empire

## Project context
Autonomous multi-niche media pipeline. Scrapes 9 sources → LLM digest → 7 content scripts.
Stack: Python 3.11, requests, BeautifulSoup4, Ollama (local), Groq API (cloud fallback).

## Architecture rules Copilot must follow

### Imports
- Config values (paths, timeouts, model names) → always from `config.py`
- LLM calls → always via `llm.call_llm()`, `llm.call_groq()`, or `llm.call_ollama()`
- Never inline `requests.post` to Groq or `ollama.chat` outside of `llm.py`

### Logging
- Use `logging.getLogger(__name__)` — never `print()`
- Use `log.exception()` inside except blocks to capture stack traces

### Scraper contract
Every scraper function signature:
```python
def scrape_something(seen: set) -> list[dict]:
    # Returns list of {"platform": str, "title": str, "summary": str}
    # On error returns [{"platform": str, "error": str}]
```
- Truncate summaries to `config.SUMMARY_MAX_CHARS` before returning
- Always call `_sleep()` after each HTTP request
- Always call `mark_seen(title, seen)` before appending to results

### LLM prompts
- Keep prompts under ~800 tokens input to stay within free-tier TPM limits
- Always include a graceful skip instruction: "If no relevant content, output: NO X CONTENT TODAY"
- Never ask the LLM to invent facts, scores, quotes, or statistics

### Tests
- New scraper → add a mock test in `tests/test_scrapers.py`
- New LLM caller pattern → add a mock test in `tests/test_llm.py`
- Use `unittest.mock.patch("requests.get")` to mock HTTP — never hit real URLs in tests

### Conventional commits (required)
```
feat|fix|refactor|test|ci|docs|chore(<scope>): <description>
```
Examples:
- `feat(squad1): add Hacker News scraper`
- `fix(llm): handle empty choices array from Groq`
- `test(scrapers): add mock for ESPN cricket feed`

### Secrets
- Never write secrets to files — read from `os.getenv()`
- Never log API keys even partially
