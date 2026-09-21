# Troubleshooting

Run `bobocodexultra doctor` first. It reports the desktop mode, local router health, provider, endpoint, catalog size and whether a Keychain item is present; it never prints the key.

## BCU models do not appear

Run `bobocodexultra on` and `bobocodexultra sync`, then quit and reopen Codex. The app loads its model catalog at startup. If the model is still absent, use `bobocodexultra models` to check whether it is selected. The selector label ends in `(BCU)`; the internal model ID retains its provider slug.

## ChatGPT models disappear or requests take the wrong route

Check that `doctor` shows provider `openai`, endpoint `http://127.0.0.1:11435/v1`, and a healthy service. If a native setup was already using Ollama, BCU delegates native requests to that saved Ollama endpoint. `bobocodexultra off` restores the original catalog and endpoint; quit and reopen Codex afterward. Existing tasks can retain earlier settings until reloaded.

## The service does not start

BCU requires Python 3.14+, the macOS desktop login session, and a free local port 11435. Check `python3 --version` and run `bobocodexultra on` to retry. If another application owns port 11435, BCU refuses activation so native Codex settings remain intact. BCU's LaunchAgent is in `~/Library/LaunchAgents/`, and its local state is in `$CODEX_HOME/bcu/`.

## OpenRouter returns an error

Use `bobocodexultra auth status` to check Keychain presence without printing the key. Verify model access and account balance directly in OpenRouter. A selected model may lack full Responses API, tool, or subagent compatibility even when OpenRouter lists it as tool-capable. Start with a short task. An upstream 429 is a rate limit, not evidence that the local router selected the wrong provider.

## Switching models in a long task fails

If the task contains provider-specific compacted or encrypted reasoning history, make a new task with a visible summary. BCU does not translate native compaction to OpenRouter. A newly saved selection also needs a Codex restart to appear in the menu.

## `usage` does not include desktop requests

The router stores response token counters and reported cost in `$CODEX_HOME/bcu/usage.sqlite3`. The current `bobocodexultra usage` command covers the older dedicated OpenRouter CLI profile, not the shared desktop router's ledger. Do not treat a current-price estimate as a billing statement.
