# How BCU fits into Codex Desktop

Codex has one active provider and loads a model catalog on startup. BCU leaves the built-in `openai` provider active and changes only the provider's base URL to a loopback address. It copies the existing catalog, then appends the selected OpenRouter models with an `(Openrouter)` display suffix. That catalog controls visibility, not per-model routing: the local service supplies the routing that the catalog cannot.

```text
Codex Desktop ── model request ──► 127.0.0.1:11435/v1
                                    ├─ BCU model ID ──► OpenRouter Responses API
                                    │                   Keychain credential only
                                    └─ native ID ──────► previously configured endpoint
                                                        (Ollama router, or OpenAI)
```

On this machine's earlier Ollama integration, the previously configured endpoint is Ollama's local Codex router. Ollama then dispatches its own model IDs to Ollama and native IDs to ChatGPT/OpenAI. BCU never needs the ChatGPT credential to select an OpenRouter model, and never sends native credentials to OpenRouter.

The router reads `$CODEX_HOME/bcu/routes.json` on each request. The file contains only model IDs and the saved native upstream URL. Adding or removing BCU models updates it and the combined catalog; removed IDs stay on a reserved list so old tasks cannot silently route them as native. Codex still needs a restart to show a changed selector. Model ID collisions between native and BCU catalogs fail activation.

For native models, BCU forwards the request body and original authentication to the saved upstream. For BCU models it reads the API key from Keychain for that request and constructs a fresh allowlist of outgoing headers. It translates Codex namespace, freeform and tool-discovery tools to OpenRouter's function-tool shape, then restores Codex's expected tool events in the response stream. Requests can run concurrently, including requests made by subagents. Codex, not BCU, executes tools and applies permissions.

The service binds loopback and is managed by a per-user LaunchAgent. `on` writes a backup of the original config, prepares the combined catalog, starts a healthy router, then updates the config. `off` restores the original provider, base URL and catalog, retaining unrelated later settings; a second recovery backup is saved. The listener remains available for tasks that still have the old endpoint until those tasks reload.

The threaded router uses separate native/OpenRouter queues and active limits, with additional limits per model. It chooses the oldest eligible waiter so a cooling or busy model does not hold up other models. Overload responses release their active slot and rejoin the queue after setting a shared model cooldown. Recovery starts with one probe; an older response cannot clear a newer cooldown. Retry and quota response headers pass through when retries are exhausted. No response is replayed once downstream streaming has started.

The health endpoint, `traffic`, and `doctor` expose queue depths, active counts, retry totals, and bounded in-memory error metadata (route, model, status, time, and parsed retry delay), never upstream error bodies or credentials. Request counters count upstream attempts, including retries and unsuccessful responses. Diagnostics reset on service restart. See [Traffic control](TRAFFIC.md) for resource bounds and the exact retry policy.

## Desktop control plane

`BCUStatus.swift` now owns one native desktop window, first-run setup assistant and menu-bar icon. The app invokes its bundled public CLI through a detected Python 3.14+ interpreter; configuration writes retain the CLI's existing validation, backups and ownership checks. `app status` supplies a non-secret settings snapshot. `app traffic` validates and saves limits without restarting the router; applying them is a separate explicit action. Secure credential entry goes directly to macOS Keychain, never through subprocess arguments. The desktop UI and menu share one store, while inference routing remains an independent LaunchAgent. See [Desktop setup](DESKTOP.md) and [Menu lifecycle](MENUBAR.md).

## Compatibility limits

OpenRouter's Responses API is stateless, so BCU sends full visible history with `store=false`; a native `previous_response_id` cannot be resumed there. Provider-encrypted reasoning cannot be transferred, and opaque native compaction state cannot be converted to OpenRouter. Start a new Codex task with a visible summary when changing providers after compaction. OpenRouter does not provide Codex's native `/responses/compact` route. Unsupported tool types are rejected rather than silently dropped.

Only inference requests on the configured Responses endpoint go through BCU. Other Codex app traffic, plugins and connectors retain their own paths. A model being listed in the catalog does not guarantee its upstream supports every Codex feature.

References: [OpenAI Docs configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [Ollama's Codex desktop router](https://github.com/ollama/ollama/blob/v0.34.2/internal/proxy/codex_desktop.go), [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview).
