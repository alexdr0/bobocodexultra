# Bobo Codex Ultra — BCU

BCU adds OpenRouter models alongside native ChatGPT and Ollama models in the **Codex desktop app**. It runs a local routing service and keeps Codex's built-in OpenAI provider and existing ChatGPT sign-in. It does not patch the signed desktop application.

Requires macOS, the Codex desktop app, Python 3.14+ (for built-in zstd decompression), a working `codex` CLI on PATH, and an OpenRouter account/key. Check `python3 --version` before installing. Clone this repository, then:

```sh
cd bobocodexultra
python3 openrouter-codex install
bobocodexultra login
```

`bobocodexultra` and its alias `boboultracodex` install into `~/.local/bin`. That directory must be on your PATH. Credentials are entered using macOS Keychain's secure terminal prompt; never put a key into a command argument or send it to an assistant.

## Everyday desktop controls

```sh
bobocodexultra          # Compact desktop dashboard
bobocodexultra login    # Store/replace the OpenRouter key and turn shared mode on
bobocodexultra on       # Enable/repair shared desktop routing
bobocodexultra models   # Search, scroll, sort and select models in the terminal TUI
bobocodexultra off      # Restore the previous native/Ollama desktop setup
bobocodexultra doctor   # Check the service, provider, endpoint and catalog
bobocodexultra sync     # Refresh the combined catalog
bobocodexultra docs     # Full built-in command guide
```

Quit and reopen Codex after enabling/disabling shared mode or changing selected models. Codex loads its catalog at startup; existing tasks may keep earlier provider settings. BCU preserves the native default when enabling shared mode. Pick any native, Ollama or `(BCU)` model in the desktop selector.

`on` starts a per-user macOS LaunchAgent, which restarts the router after a crash and starts it at login. No root or sudo is required. `off` restores the previous endpoint/catalog/provider and retains unrelated settings changed afterward. Recovery backups are retained. The listener remains available for already-open tasks until they reload; turning off desktop routing does not delete credentials, selections, or usage data.

The model TUI supports `/` search, `S` sort, arrows or J/K scrolling, Page Up/Down, Space multi-select, `D` default, `I` details, Enter save, and Q cancel. Changes are staged until saved. Labels are exactly `[Model Name] (BCU)`, for example `Grok 4.6 (BCU)`. Provider prefixes are removed from labels; request model IDs remain unchanged.

The one-time login is interactive and uses a hidden Keychain prompt. For machines already signed in with BCU, `bobocodexultra on` is enough to activate shared mode. `bobocodexultra login` can also replace the saved key. Use `bobocodexultra auth login --no-desktop` if you only want to update the key.

Optional shortcuts and existing command groups still work:

```sh
bobocodexultra add author/model-id
bobocodexultra remove author/model-id
bobocodexultra default author/model-id  # BCU CLI profile default
bobocodexultra model list
bobocodexultra model manage
bobocodexultra auth login --no-desktop
bobocodexultra desktop on
bobocodexultra desktop off
bobocodexultra reset                    # Alias for off
```

## How the shared architecture works

```text
Codex Desktop (native OpenAI provider + ChatGPT sign-in)
                   |
       BCU on 127.0.0.1:11435/v1
                   |
       +-----------+-----------------------+
       |                                   |
Selected BCU model                 Native / Ollama model
       |                                   |
OpenRouter Responses API          Existing native endpoint
Keychain OpenRouter key            (your Ollama router, if configured)
                                           |
                                  +--------+---------+
                                  |                  |
                                Ollama        ChatGPT / OpenAI
```

BCU adopts the same local router architecture as Ollama. On a machine already configured for Ollama, BCU chains to its existing router rather than duplicating or overwriting Ollama's setup. Without an existing override, native requests go to ChatGPT or the OpenAI API according to their authentication headers.

For the request flow, catalog refresh rules, trust boundaries and failure recovery, see [Architecture](docs/ARCHITECTURE.md). For common setup errors, see [Troubleshooting](docs/TROUBLESHOOTING.md).

- **Catalog:** copies the existing native/Ollama catalog and appends selected BCU entries. It preserves native metadata, supplying conservative defaults only for required missing schema fields. ID collisions stop activation instead of guessing a route.
- **Routing:** each request is dispatched by model ID. Selection changes reload without restarting the service; the desktop selector still needs an app restart. Removed BCU IDs remain reserved so old tasks cannot accidentally send them to ChatGPT.
- **Authentication:** native credentials are passed only to the saved native endpoint. OpenRouter receives a fresh allowlist of headers and its own Keychain key. ChatGPT account headers, bearer tokens and cookies are not copied to OpenRouter.
- **Streaming:** supports HTTP Responses streaming, zstd-compressed requests, concurrent model requests, and WebSocket-to-HTTP fallback. Native request bodies pass through unchanged.
- **Tools:** converts namespaced and freeform tools into OpenRouter function tools and restores Codex's response shapes. It also translates client-side tool search and agent messages. Codex continues to execute tools and enforce its own permissions.
- **Subagents:** use the same per-request model routing. A parent's model does not pin every child request to the same upstream. Real model behavior and tool compliance still vary.
- **Persistence:** configuration backups, routing metadata and the combined catalog are under `$CODEX_HOME/bcu/`. The default is `~/.codex/bcu/`. The LaunchAgent is under `~/Library/LaunchAgents/`.

The service only binds loopback, rejects browser-origin and unexpected Host requests, restricts upstream paths, never follows upstream redirects, and does not log prompts, generated text, or credential headers. Local applications running as your user remain within the local trust boundary, as with Ollama's local service.

## Compatibility boundaries

OpenRouter's Responses API is stateless. BCU sends full visible history with `store=false`; it cannot reuse native `previous_response_id` state. Provider-encrypted reasoning is omitted on the OpenRouter route. Switching a task containing opaque native compaction to BCU is rejected with a recovery message; start a new task with a visible summary. OpenRouter does not offer Codex's native `/responses/compact` endpoint. Very long tasks may need a new task/summary. The adapter rejects unsupported tool types explicitly.

Models being listed does not prove identical behavior across all providers. Test a model on a small task before relying on its tool/subagent behavior. Native requests keep their existing path through the native/Ollama implementation. BCU retains a separate OpenRouter CLI profile for backwards compatibility:

```sh
bobocodexultra codex launch
bobocodexultra codex smoke --agents  # Optional billed check
```

## Usage and appearance

The router records successful OpenRouter response usage in a private local SQLite ledger, using response IDs to avoid duplicates. It stores model IDs, timestamps, counters and reported cost only. The current `bobocodexultra usage` command reports **legacy OpenRouter CLI-profile sessions only**; shared desktop usage is not included in that command yet. No cost total is presented as an invoice. The ledger path is `$CODEX_HOME/bcu/usage.sqlite3` (default `~/.codex/bcu/usage.sqlite3`).

Color and animation respect `NO_COLOR`, `CI`, `TERM=dumb`, `BOBOCODEXULTRA_NO_ANIM`, `--no-color` and `--no-animate`. Noninteractive output is plain text.

## Verification

The tests exercise real local HTTP sockets with fake upstreams: native body/auth passthrough, OpenRouter credential isolation, streaming, concurrent routes, tool translation, live catalog changes, browser/unknown-model rejection, service failure before activation, and restoring native configuration while preserving unrelated edits. Live read-only probes check the installed Codex model list and selected upstreams separately.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
```

The test suite does not require an API key or incur model charges. See [Contributing](CONTRIBUTING.md) for test and change guidelines, and [Security](SECURITY.md) for safe issue reporting.

References: [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [Ollama's local router](https://github.com/ollama/ollama/blob/v0.34.2/internal/proxy/codex_desktop.go), [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview).
