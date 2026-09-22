# Troubleshooting

Run `bobocodexultra doctor` first. It reports the desktop mode, local router health, provider, endpoint, catalog size and whether a Keychain item is present; it never prints the key.

## BCU models do not appear

Run `bobocodexultra on` and `bobocodexultra sync`, then quit and reopen Codex. The app loads its model catalog at startup. If the model is still absent, use `bobocodexultra models` to check whether it is selected. The selector label ends in `(Openrouter)`; the internal model ID retains its provider slug.

## ChatGPT models disappear or requests take the wrong route

Check that `doctor` shows provider `openai`, endpoint `http://127.0.0.1:11435/v1`, and a healthy service. If a native setup was already using Ollama, BCU delegates native requests to that saved Ollama endpoint. `bobocodexultra off` restores the original catalog and endpoint; quit and reopen Codex afterward. Existing tasks can retain earlier settings until reloaded.

## The service does not start

BCU requires Python 3.14+, the macOS desktop login session, and a free local port 11435. Check `python3 --version` and run `bobocodexultra on` to retry. If another application owns port 11435, BCU refuses activation so native Codex settings remain intact. BCU's LaunchAgent is in `~/Library/LaunchAgents/`, and its local state is in `$CODEX_HOME/bcu/`.

## OpenRouter returns an error

Use `bobocodexultra auth status` to check Keychain presence without printing the key. Verify model access and account balance directly in OpenRouter. A selected model may lack full Responses API, tool, or subagent compatibility even when OpenRouter lists it as tool-capable. Start with a short task. An upstream 429 is a rate limit, not evidence that the local router selected the wrong provider.

## “Exceeded retry limit” / HTTP 429

The provider rejected requests until retries were exhausted. OpenRouter limits are separate from your native ChatGPT allowance. BCU now queues concurrent requests and automatically retries temporary 429/503 rejections with a shared model cooldown. Use `bobocodexultra traffic` to inspect active requests, waiters, cooldowns, and recovery totals. Persistent failures need a check of the model provider's rate limits and your OpenRouter account limits; adding credits is not a universal fix for 429s.

BCU forwards `Retry-After` and quota headers on OpenRouter error responses. Older builds discarded those headers, which could cause the client to retry too soon. Update/install BCU, then run `bobocodexultra on` when active tasks have finished to load the updated router. No Codex restart is needed for this router-only fix.

Run `bobocodexultra doctor` after a failure. It shows the recent upstream route, model, HTTP status, and retry delay reported at the time of failure. These are in-memory diagnostics, reset on router restart; they contain no prompt text, credentials, or upstream error bodies. A `native` route can include an existing Ollama router. BCU retries at most six upstream attempts within a 180-second queue/retry budget per incoming request; Codex may independently retry a final error, but the shared cooldown continues across those requests. HTTP 402 is retried only when OpenRouter explicitly identifies a temporary in-flight budget limit and supplies `Retry-After`. Other billing/authentication and known quota errors return directly. Models are never switched automatically.

If the local queue or buffered-body budget fills, BCU returns HTTP 503 with `Retry-After`. Inspect `traffic` before raising limits: higher concurrency can make provider throttling worse. An upstream wait hint longer than the request's remaining budget is returned rather than retried early. See [Traffic control](TRAFFIC.md) for settings and limits.

See [OpenRouter error and retry guidance](https://openrouter.ai/docs/api/reference/errors-and-debugging) and [OpenAI Docs rate-limit guidance](https://developers.openai.com/api/docs/guides/rate-limits/).

## Reasoning choice does not seem to take effect

Run `bobocodexultra reasoning` to inspect each selected BCU model's default, then change one with `bobocodexultra reasoning medium --model author/model-id` and relaunch Codex. `bobocodexultra doctor` shows whether a user-level `model_reasoning_effort` may override the catalog default. Explicit task or custom-agent settings can also win. The BCU OpenRouter route caps `xhigh`, `max`, and `ultra` requests at `high`; this does not affect native/Ollama requests. If a provider rejects a lower effort, try another selected model or return that model to `high`.

## Subagents use the wrong model after changing the selection

Run `bobocodexultra agents status` and `bobocodexultra model list`. If a BCU-managed default points to a model you want to remove, run `bobocodexultra agents setup --model NEW_SELECTED_ID` first, or `bobocodexultra agents restore`. `bobocodexultra off` restores BCU-managed agent defaults automatically when they have not been changed externally. If the agent settings were edited manually, BCU refuses to overwrite them and reports that a manual merge is needed. Explicit spawn options and custom-agent files override the global defaults.

## Switching models in a long task fails

If the task contains provider-specific compacted or encrypted reasoning history, make a new task with a visible summary. BCU does not translate native compaction to OpenRouter. A newly saved selection also needs a Codex restart to appear in the menu.

## `usage` does not include desktop requests

Older releases read only the dedicated OpenRouter CLI profile and missed shared desktop requests. Update/install the CLI, then run `bobocodexultra usage --offline --days 0`. The command now reads the existing `$CODEX_HOME/bcu/usage.sqlite3` ledger alongside legacy CLI records; previously recorded desktop history is retained. Use `--days 0` to include records older than the default 30-day window. Native ChatGPT/Ollama calls are intentionally excluded.

For the graphical view, quit the old menu companion, run `bobocodexultra app install`, then choose **Usage & Costs…** or the desktop **Usage** page. The app uses its bundled CLI and detects Python independently of shell initialization. If Python moves, choose **Detect again** in Setup. No router or Codex restart is needed for reporting changes.

An unreadable ledger produces a warning and a partial report, not a false zero total. Missing prices produce a known-cost subtotal; `usage --refresh-prices` refreshes fallback public pricing without reading your API key. Retired model IDs may still have no price. Do not delete the ledger to repair a report; it contains your retained desktop history. See [Usage accounting](USAGE.md).

## Desktop setup cannot continue

Use **Setup → Check → Check prerequisites**. The desktop app needs Python 3.14+ even when installed from a disk image. Install Python and Codex from their official sources, then use **Detect again**. If existing Codex configuration is invalid, the preflight reports it and does not overwrite it. The app's CLI repair action reinstalls the bundled public files without changing routing.

## macOS warns about the downloaded app

Current disk images are locally signed, not Developer ID signed or Apple-notarized. BCU does not bypass Gatekeeper. Use the source build if you do not want to trust an unnotarized download; see [Desktop distribution](DESKTOP.md#build-and-distribution). Do not confuse an Apple Development certificate with a Developer ID distribution certificate.

## Duplicate or old menu icon

Quit the old BCU Menu before installing the desktop version. They share the same bundle identifier and login-item label, and the new app prevents multiple instances from running. Avoid keeping separate copies in both system and user Applications folders. Closing the window intentionally leaves the menu icon running; **Quit BCU** closes both without stopping the router.
