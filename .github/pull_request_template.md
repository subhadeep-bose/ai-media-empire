## Summary
<!-- What does this PR do? 2-3 bullet points max. -->
- 
- 

## Type of change
<!-- Check all that apply -->
- [ ] `feat` — new capability (scraper, generator, squad)
- [ ] `fix` — bug fix
- [ ] `refactor` — restructure, no behaviour change
- [ ] `test` — tests only
- [ ] `ci` — workflow/Actions change
- [ ] `docs` — documentation
- [ ] `chore` — deps, config, generated files

## Testing
- [ ] `pytest tests/ -v` passes locally
- [ ] Ran `python main.py` (or squad script) and verified output
- [ ] No hardcoded secrets, paths, or model names introduced

## Checklist
- [ ] Branch name follows `feature/` or `fix/` convention
- [ ] All commits follow conventional commit format
- [ ] PR title follows conventional commit format
- [ ] `config.py` updated if any new magic numbers added
- [ ] New scrapers use `_sleep()`, `mark_seen()`, and truncate to `SUMMARY_MAX_CHARS`
- [ ] New LLM calls go through `llm.call_llm()`, not inline

## Related issues / context
<!-- Link any related issues or paste relevant logs -->
