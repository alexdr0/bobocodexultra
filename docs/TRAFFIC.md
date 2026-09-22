# Traffic control and automatic retries

BCU schedules inference requests across all conversations and subagents using its shared desktop endpoint. Merely opening an idle conversation does not take an inference slot. Each active stream occupies a slot until it finishes or disconnects; queued and cooling requests do not occupy upstream slots. The native route includes Ollama when that is your saved upstream.

## Default limits

| Setting | Default | Meaning |
| --- | ---: | --- |
| `native_concurrency` | 16 | Native/Ollama upstream attempts active at once |
| `openrouter_concurrency` | 8 | OpenRouter upstream attempts active at once |
| `native_model_concurrency` | 8 | Active attempts per native model |
| `openrouter_model_concurrency` | 2 | Active attempts per OpenRouter model |
| `queue_limit` | 64 | Waiting requests per route, separate from active slots |
| `request_timeout` | 180 | Seconds available for queuing and starting retry attempts |
| `max_attempts` | 6 | Upstream attempts per incoming request, including the first |
| `backoff_base` | 2 | Initial delay in seconds when no valid retry hint exists |
| `backoff_max` | 30 | Maximum exponential delay; does **not** cap provider hints |
| `jitter` | 1 | Up to this many extra random seconds per cooldown |
| `body_budget_mb` | 256 | Aggregate accounted request-body budget, in MiB |

Native and OpenRouter active slots are reserved independently. Within a route, the oldest eligible request starts first; requests for a cooling or saturated model are skipped until eligible. This is fairness between requests, not equal shares between conversations. There is also a bounded shared admission gate for body readers, and an aggregate body budget. Extreme local admission/memory pressure can still affect both routes.

The body budget accounts three times the largest wire/decoded/normalized body size per accepted request, including queued and active requests. It bounds buffered input, but is not an exact process-memory limit: parsed JSON, temporary decompression, runtime objects, and response frames add overhead. Individual bodies remain limited to 64 MiB. Queues live only in memory and are not persisted across router restarts.

## Retry behavior

BCU retries explicit HTTP 429 and 503 rejections before sending response headers to Codex. It honors a valid `Retry-After` seconds value or HTTP date as a minimum. Without a valid hint, delays grow exponentially with jitter. All requests for the same route/model share this cooldown, including later retries initiated by Codex itself. After a cooldown, only one recovery probe runs until a successful HTTP response allows ordinary parallelism again. An older in-flight success cannot clear a newer cooldown.

Retries release their active slot and rejoin the queue. A retry uses the same model, body, and request authentication; OpenRouter credentials are read once from Keychain after the request is admitted to an upstream slot. Keys are never cached across logical requests or written into diagnostics. The final successful response is streamed normally; usage is recorded only from actual response usage data, not guessed for rejected attempts.

BCU does not retry these cases:

- Billing/authentication/permission errors and recognized exhausted-quota codes.
- Ambiguous transport failures, including an upstream connection lost before headers.
- Failures inside an HTTP 200 stream or after any downstream response has started.
- Opaque compressed error bodies, or oversized error bodies that cannot be classified safely.
- An ordinary HTTP 402. The sole exception is OpenRouter's explicit `openrouter_in_flight_budget` error with a valid `Retry-After` hint.

If attempts are exhausted or a provider hint exceeds the remaining budget, BCU returns the upstream error and retry metadata. A full queue, memory budget, or expired queue wait returns local HTTP 503 with `Retry-After`. The client may have its own retry count, so six BCU attempts is a per-incoming-request limit, not a lifetime limit for an entire Codex turn. Shared cooldowns continue across client retries. The wait budget controls queue/retry scheduling; individual network operations also have socket timeouts, and a slow operation can extend elapsed time. After response headers arrive, streaming retains the existing 180-second idle socket timeout.

Closing or cancelling the client's queued connection removes its request, including during cooldown waits. Active upstream connections close when disconnects are detected; BCU cannot retract work already accepted by a provider. It never silently switches models or credentials to escape a provider limit.

## Inspect and tune

```sh
bobocodexultra traffic          # Live snapshot of activity and cooldowns
bobocodexultra traffic --json   # Machine-readable snapshot
bobocodexultra doctor           # Traffic plus routing and recent upstream errors
bobocodexultra docs traffic     # Built-in guide
```

Counters reset when the router restarts. `retries` counts extra dispatched upstream attempts; `recovered` counts requests that receive a successful HTTP status after retrying (it does not guarantee the later stream completes). `queued_total` counts attempts that actually had to wait. Model details are limited to 16 entries, with an omitted-entry count; aggregate active and queued totals include all models. Prompts, response text, API keys, and raw error bodies are not included.

Optional overrides go in `$CODEX_HOME/bcu/traffic.json`, normally `~/.codex/bcu/traffic.json`. Omitted fields use defaults. For example:

```json
{
  "openrouter_concurrency": 4,
  "openrouter_model_concurrency": 1,
  "max_attempts": 6,
  "request_timeout": 180
}
```

Run `bobocodexultra on` when active tasks are finished to reload changed settings or newly installed router code. This restarts the router and clears in-memory queues and diagnostics; it does not require a Codex restart when the endpoint/catalog is unchanged. Invalid settings are rejected before restarting a running service. Raising concurrency does not raise provider limits; reduce it if overloads increase.

These controls apply to BCU's shared desktop proxy. The optional dedicated `codex launch` OpenRouter CLI profile connects directly to OpenRouter and does not use this scheduler. The router keeps per-request upstream connections rather than a connection pool; this release focuses on bounded concurrency, overload recovery, and task isolation.
