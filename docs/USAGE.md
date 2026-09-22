# Usage accounting

`bobocodexultra usage` and the menu-bar **Usage & Costs…** window use the same report. The default period is 30 days; `--days 7` selects a week and `--days 0` includes all retained history. The menu offers 24 hours, 7 days, 30 days and all time, plus model search and token/cost/name sorting.

## Sources and counters

Shared desktop requests come from the response-ID-deduplicated SQLite ledger at `$CODEX_HOME/bcu/usage.sqlite3`. Legacy CLI records come from retained Codex sessions explicitly marked with the `openrouter` provider. Shared desktop rollouts use a different provider and are deliberately excluded from that scan to avoid double counting. Unrelated native rollouts are skipped immediately. Native ChatGPT and Ollama token usage is outside this report's scope.

Input tokens include cached input. Output tokens include reasoning tokens; reasoning is shown separately for visibility, never added again. Request records are not conversation turns: an agent can make several requests in one turn. Data is limited to what BCU recorded locally; deleted history, calls made elsewhere, and responses without final usage cannot be reconstructed from a catalog. Token totals can include repeatedly submitted conversation context, so they are not a measure of unique text.

## Costs

BCU prefers each response's reported `usage.cost`, including a legitimate zero. For records without that cost, it estimates from token counters and OpenRouter's public pricing catalog, using cache pricing when available. Reported costs and estimates remain separate in every summary. Estimates use current prices, not historical rates or an account invoice. Retired or unknown model IDs without pricing remain unpriced; **known cost** is then only a partial subtotal. See [OpenRouter usage accounting](https://openrouter.ai/docs/guides/guides/usage-accounting).

`--offline` avoids network access and uses existing cached prices. The normal command fetches public prices only when fallback pricing is needed and the cache is older than an hour. `--refresh-prices` forces a refresh; it cannot be combined with `--offline`. Catalog failures do not hide token totals or already-reported costs. No usage-report operation reads the API key or makes a billed model call.

The menu refreshes local data every 15 seconds while its usage window is visible. **Refresh** stays offline; **Refresh Prices** explicitly refreshes the public catalog. Closing the window stops its periodic usage refresh.

## JSON and completeness

`usage --json` emits schema version 2, with `summary`, model-ID-keyed `models`, `period_days`, pricing timestamp, ledger status and warnings. Each aggregate has source counts, token counters, `reported_cost_usd`, `estimated_cost_usd`, `known_cost_usd`, nullable `total_cost_usd`, and `cost_source` (`reported`, `estimated`, `mixed`, `partial` or `none`). The top-level `estimated_total_usd` is only the estimated portion, not the combined cost. `total_cost_usd` is null when some prices are unavailable or retained records could not be read.

Corrupt/unreadable ledgers or skipped records produce warnings and `data_complete: false`. A missing ledger can simply mean no desktop requests have been recorded yet; legacy records remain available. Completeness only describes reading retained local sources, not completeness against an OpenRouter invoice. The ledger is opened read-only; the report never creates, clears or repairs it.

The ledger stores model IDs, timestamps, response IDs and usage counters/costs, not prompts or credentials. JSON reports contain aggregates rather than conversation contents or local session paths. Keep your local usage history private when filing public issues.
