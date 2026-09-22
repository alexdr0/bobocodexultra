# Bobo Codex Ultra — BCU

<img src="assets/BCU-icon.png" alt="BCU Inter B in a square icon" width="112">

BCU adds OpenRouter models alongside native ChatGPT and Ollama models in the **Codex desktop app**. It runs a local routing service and keeps Codex's built-in OpenAI provider and existing ChatGPT sign-in. It does not patch the signed desktop application.

[Download the latest GitHub release](https://github.com/alexdr0/bobocodexultra/releases/latest) or clone the repository below. Releases contain source code; the setup wizard installs the local CLI from that source, not a prebuilt app.

## Set up BCU on your Mac (guided terminal wizard)

You need macOS, the Codex desktop app, Python 3.14+ (for built-in zstd decompression), the `codex` CLI on your PATH, and an OpenRouter account with an API key. Clone the repository, run the read-only preflight, then start the wizard:

```sh
git clone https://github.com/alexdr0/bobocodexultra.git
cd bobocodexultra
python3 openrouter-codex setup --check
python3 openrouter-codex setup
```

The wizard installs the global `bobocodexultra` and `boboultracodex` commands, opens the searchable multi-select model picker (if your terminal supports it), uses macOS Keychain's hidden prompt for your API key, offers to enable the shared Codex Desktop model selector, and optionally sets your Codex subagent defaults. It is resumable: run `bobocodexultra setup` again if you cancel or need to change a choice. The default model lineup works if you skip the picker or its metadata endpoint is unavailable. The preflight makes no changes, and the wizard never runs a paid inference test.

Commands install into `~/.local/bin`. If that directory is not already on your PATH, add it to your shell startup configuration; for the current terminal you can run:

```sh
export PATH="$HOME/.local/bin:$PATH"  # Current terminal only
bobocodexultra doctor
```

Quit and reopen Codex Desktop after enabling shared mode or changing models; native ChatGPT and existing Ollama models remain available alongside entries labeled `[Model Name] (Openrouter)`. To undo the desktop routing, run `bobocodexultra off` and reopen Codex. The wizard does not open Codex, read your saved key, or take over unrelated config settings. No `sudo` is required.

### Manual setup and later changes

If you prefer individual commands, keep `openrouter-codex`, `bcu_router.py`, `bcu_games.py`, `bcu_doom_render.py`, and `BCUStatus.swift` together in the cloned directory and run:

```sh
bobocodexultra install  # Or: python3 openrouter-codex install
bobocodexultra login    # Secure Keychain prompt; activates shared desktop mode
bobocodexultra models   # Search and choose which BCU models appear
bobocodexultra reasoning # View reasoning defaults for selected BCU models
bobocodexultra doctor   # Check the local router and Codex integration
```

The optional menu bar companion installs with `bobocodexultra menu install`. For setup help run `bobocodexultra docs setup`. The full-screen picker needs an interactive UTF-8 terminal (`TERM=xterm-256color` or similar); the wizard keeps the existing lineup if the picker is unavailable and asks before continuing after a catalog error. See the [official Codex configuration reference](https://developers.openai.com/codex/config-reference/) for the underlying user-level settings.

Credentials are entered using macOS Keychain's secure terminal prompt; never put a key into a command argument, commit, issue, or assistant message. If you only want offline Snake, Pong, and Doom, the installation is enough—no key or desktop configuration is needed.

## Set up your Codex agents

BCU routes model requests; Codex itself spawns and manages subagents. After selecting your models, set up a selected BCU model as the default for children:

```sh
bobocodexultra agents setup                 # Selected default BCU model, its effort, limit 2
bobocodexultra agents status                # Inspect effective user-level defaults
bobocodexultra agents setup --model anthropic/claude-opus-5 --reasoning high --limit 3
bobocodexultra agents restore               # Restore pre-BCU defaults; keep unrelated edits
```

Use `--model` only with an ID shown by `bobocodexultra model list`. BCU edits only the `[agents]` table in your **user-level** `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`), saves a private local backup, and refuses to overwrite agent settings changed outside BCU. `bobocodexultra off` also restores BCU-managed agent defaults so child agents do not keep pointing to a removed BCU route. Custom-agent files and explicit spawn settings can override these defaults.

If you prefer to edit Codex settings yourself, add these settings to its existing `[agents]` table, or create the table once if none exists:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 2
```

Multi-agent tools are enabled by default, but the explicit settings make your intention and concurrency limit clear. For children to use a particular BCU model, run `bobocodexultra model list`, copy a **selected model's exact ID**, and add one line under that same `[agents]` table—for example, only if that ID is selected:

```toml
default_subagent_model = "anthropic/claude-opus-5"
default_subagent_reasoning_effort = "high"
```

Leave `default_subagent_model` unset if you prefer Codex's own default. An explicit model chosen when spawning a child takes precedence. Do not paste the example model ID blindly: choose a model you have access to, and remember that a model shown in the selector is not a guarantee of tool compatibility. Do not create a second `[agents]` table or overwrite existing user settings. Keep provider and authentication settings in the user-level configuration rather than a project's `.codex/config.toml`.

Reopen Codex, choose an `(Openrouter)` model, and try a small, read-only task asking Codex to delegate two independent checks to subagents and combine their findings. Then repeat with a native model if you want to verify both routes. Delegation still depends on the task's instructions and the selected model's tool behavior. As an **optional billed** CLI-only check, `bobocodexultra codex smoke --agents` exercises the separate OpenRouter CLI profile; it does not validate every Codex Desktop workflow. See the [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml) and [subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents) for current settings and custom roles.

## Control reasoning difficulty

Each selected BCU model can have its own default. BCU advertises low, medium, and high choices to Codex Desktop and saves the selected default in its catalog; the dedicated BCU CLI profile also follows the selected default model's effort. This does **not** change native ChatGPT/Ollama model metadata or their reasoning settings.

```sh
bobocodexultra reasoning                               # Show every selected BCU model's default
bobocodexultra reasoning medium                        # Change the default BCU model
bobocodexultra reasoning low --model anthropic/claude-opus-5
bobocodexultra doctor                                  # Inspect config and possible overrides
```

Relaunch Codex to refresh the selector. A user-level `model_reasoning_effort` or a task's explicit effort may override the catalog default; `doctor` displays a global effort if present. The router forwards low/medium/high on BCU requests but caps incoming `xhigh`, `max`, or `ultra` to `high` for its OpenRouter route. Provider support varies, so test a short task when changing effort; an upstream model can reject an unsupported value. BCU never rewrites native model entries to force these options.

If an `(Openrouter)` model in the Codex Desktop selector shows only **High** and will not let you choose Low or Medium, an older BCU-generated catalog may still advertise just one level. Run `bobocodexultra doctor` to check **GUI THINKING**, then `bobocodexultra model sync` to regenerate the catalog safely. Fully quit and reopen Codex Desktop; its catalog is loaded at startup, so an already-open task may still show the old choices. New BCU installations upgrade checksum-verified older catalogs automatically; files modified outside BCU are never silently replaced. This changes only BCU entries, not native/Ollama capabilities or your API key.

## macOS menu bar

`bobocodexultra menu install` builds the native Swift companion into `~/Applications/Bobo Codex Ultra.app`, opens it, and enables Launch at Login using a per-user LaunchAgent. Its icon is an **Inter Bold B inside a square outline with sharp corners**. The monochrome menu bar version adapts to light/dark appearances; the Applications icon is white on black. The letter is a vector outline, so Inter does not need to be installed. There is no Dock icon.

The menu shows whether shared mode and its local router are available. Turn routing on/off, open a graphical **Manage Models** window, enter the OpenRouter key in Terminal's secure prompt, open Codex Desktop or the documentation, toggle Launch at Login, and **Quit BCU Menu** from the same icon. Quit closes only the menu app; it does not stop the request router or affect an active Codex task. The model window loads the OpenRouter tool-capable catalog, supports live search and sorting by popular/name/context/selected, shows your existing choices including models temporarily absent from OpenRouter, and allows multiple add/remove actions and default changes. Reopen Codex to refresh its selector after a model change.

`bobocodexultra menu` opens the installed app (and installs it if necessary). Key entry always opens Terminal because Keychain's hidden interactive prompt needs a terminal. To stop launching at login, uncheck the menu item; to launch again after quitting, run `bobocodexultra menu`. The menu and router have independent login items: disabling one does not remove the other. The app is compiled and signed locally on your Mac; it uses only AppKit/SwiftUI and does not depend on a hosted menu process.

See [Menu bar design and controls](docs/MENUBAR.md) for the icon rationale, state behavior, installation details and limitations.

## Everyday desktop controls

```sh
bobocodexultra          # Compact desktop dashboard
bobocodexultra menu     # Open the menu bar companion
bobocodexultra login    # Store/replace the OpenRouter key and turn shared mode on
bobocodexultra on       # Enable/repair shared desktop routing
bobocodexultra models   # Search, scroll, sort and select models in the terminal TUI
bobocodexultra reasoning medium # Default effort for the selected default BCU model
bobocodexultra agents setup     # Set up Codex subagents with reversible defaults
bobocodexultra off      # Restore the previous native/Ollama desktop setup
bobocodexultra doctor   # Check the service, provider, endpoint and catalog
bobocodexultra traffic  # Active requests, queues, cooldowns and automatic retries
bobocodexultra sync     # Refresh the combined catalog
bobocodexultra docs     # Full built-in command guide
bobocodexultra snake    # Offline terminal Snake
bobocodexultra pong     # Offline terminal Pong against the CPU
bobocodexultra doom     # Six-stage terminal maze shooter
```

Quit and reopen Codex after enabling/disabling shared mode or changing selected models. Codex loads its catalog at startup; existing tasks may keep earlier provider settings. BCU preserves the native default when enabling shared mode. Pick any native, Ollama or `(Openrouter)` model in the desktop selector.

`on` starts a per-user macOS LaunchAgent, which restarts the router after a crash and starts it at login. No root or sudo is required. `off` restores the previous endpoint/catalog/provider and retains unrelated settings changed afterward. Recovery backups are retained. The listener remains available for already-open tasks until they reload; turning off desktop routing does not delete credentials, selections, or usage data.

The model TUI supports `/` search, `S` sort, arrows or J/K scrolling, Page Up/Down, Space multi-select, `D` default, `R` cycle low/medium/high reasoning, `I` details, Enter save, and Q cancel. Changes are staged until saved. Labels are exactly `[Model Name] (Openrouter)`, for example `Grok 4.6 (Openrouter)`. Provider prefixes are removed from labels; request model IDs remain unchanged.

The one-time login is interactive and uses a hidden Keychain prompt. For machines already signed in with BCU, `bobocodexultra on` is enough to activate shared mode. `bobocodexultra login` can also replace the saved key. Use `bobocodexultra auth login --no-desktop` if you only want to update the key.

## Multiple conversations and automatic recovery

Shared desktop routing queues busy conversations and subagents automatically. Native/Ollama traffic has 16 active slots and OpenRouter has 8, with per-model limits of 8 and 2 respectively. Each route has room for 64 waiting requests. A cooling or busy model does not block eligible requests for other models.

Temporary HTTP 429/503 rejections retry automatically, up to six upstream attempts within a 180-second queue/retry budget. BCU honors `Retry-After`; without a hint it uses exponential delays with jitter. All conversations using a model share its cooldown, followed by one recovery probe before normal parallelism resumes. Queued requests are discarded when their client disconnects. Billing/authentication failures, known exhausted quotas, ambiguous connection failures, and already-started streams are not automatically replayed.

Inspect activity with `bobocodexultra traffic`, `traffic --json`, or `doctor`. Limits are configurable in an optional `bcu/traffic.json` file under your Codex home. Update/install BCU and run `bobocodexultra on` when tasks are idle to activate an updated router. See [Traffic control and retries](docs/TRAFFIC.md) for defaults, tuning, memory bounds, retry limits, and the dedicated CLI profile distinction. Persistent provider limits or a full local queue can still return an error; BCU cannot create provider capacity.

## Offline terminal arcade

Run `bobocodexultra snake`, `bobocodexultra pong`, or `bobocodexultra doom` from any directory after installation. Games run locally in an interactive UTF-8 terminal, without login, an API key, the router, network access, or model charges. `boboultracodex` works too. Resize the terminal if prompted; press **P** to pause, **R** to restart, and **Q** or **Esc** to quit.

| Game | Controls | Goal |
| --- | --- | --- |
| Snake | Arrow keys or WASD | Eat food; avoid walls and your tail. |
| Pong | Up/Down or W/S | Beat the CPU to seven points. |
| Doom | W/S forward/back; A/D strafe; Left/Right turn; Space shoot; M toggle map | Survive six stages, clear each arena, then find the gate (`>`). |

`doom` is an original retro-style raycasting game, not id Software's Doom; it includes no Doom assets. Its graphics use a two-pixel-per-cell color renderer, procedural textured walls and perspective floor, stage lighting, hand-drawn enemy and pickup sprites, a first-person weapon, and a monochrome fallback. A larger UTF-8 terminal shows more detail; no image downloads or graphics dependencies are required. Its six stages add faster flankers (`F`), ranged shooters (`R`) with visible projectiles, and a tough final boss (`B` on the map). Ordinary enemies are `E`; medkits (`+`) restore health and ammo packs (`=`) refill your weapon. Defeat every enemy before entering the gate (`>`). Health, ammo and score carry between stages, with a small resupply on each transition. Shooting has a short cooldown, and enemies can pursue you around corners. If you run completely out of ammunition with no packs left, emergency ammo arrives after a short delay to prevent an unwinnable run. Press `R` to start over. See `bobocodexultra docs games` for the built-in controls. The arcade is separate from Codex Desktop's model selector and does not change provider settings.

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

Run `bobocodexultra usage` or choose **Usage & Costs…** from the BCU menu-bar icon to see shared desktop usage and legacy OpenRouter CLI-profile usage together. Reports show per-model input, cached input, output and total tokens, provider-reported costs, and separately labeled catalog estimates when reported costs are missing. Native ChatGPT and Ollama usage is excluded. Unknown prices are flagged as partial, not silently priced at zero.

```sh
bobocodexultra usage                   # Last 30 days
bobocodexultra usage --days 7           # Last week; --days 0 for all history
bobocodexultra usage --offline         # Local history and cached prices only
bobocodexultra usage --refresh-prices  # Refresh public fallback pricing
bobocodexultra usage --json            # Machine-readable report
bobocodexultra docs usage              # Built-in guide
```

The router records successful OpenRouter response usage in a private local SQLite ledger, using response IDs to avoid duplicates. It stores model IDs, timestamps, counters and reported cost only, at `$CODEX_HOME/bcu/usage.sqlite3` (default `~/.codex/bcu/usage.sqlite3`). Reports do not require an API key. No total is presented as an invoice; see [Usage accounting](docs/USAGE.md) for cost semantics, completeness and privacy. Update the CLI and reinstall the menu app to pick up this view; no Codex or router restart is needed for this reporting update.

Color and animation respect `NO_COLOR`, `CI`, `TERM=dumb`, `BOBOCODEXULTRA_NO_ANIM`, `--no-color` and `--no-animate`. Noninteractive output is plain text.

## Verification

The tests exercise real local HTTP sockets with fake upstreams: native body/auth passthrough, OpenRouter credential isolation, streaming, concurrent routes, tool translation, live catalog changes, browser/unknown-model rejection, service failure before activation, and restoring native configuration while preserving unrelated edits. Live read-only probes check the installed Codex model list and selected upstreams separately.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
```

The test suite does not require an API key or incur model charges. See [Contributing](CONTRIBUTING.md) for development guidance and [Security](SECURITY.md) for safe issue reporting.

References: [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [Ollama's local router](https://github.com/ollama/ollama/blob/v0.34.2/internal/proxy/codex_desktop.go), [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview).
