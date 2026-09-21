# Bobo Codex Ultra — BCU

![BCU circuit-B icon](assets/BCU-icon.png)

BCU adds OpenRouter models alongside native ChatGPT and Ollama models in the **Codex desktop app**. It runs a local routing service and keeps Codex's built-in OpenAI provider and existing ChatGPT sign-in. It does not patch the signed desktop application.

## Set up BCU on your Mac

You need macOS, the Codex desktop app, Python 3.14+ (for built-in zstd decompression), the `codex` CLI on your PATH, and an OpenRouter account with an API key. Check the prerequisites first:

```sh
python3 --version       # Must be 3.14 or newer
command -v codex        # Must print a path
```

Clone the repository and install from its root; keep `openrouter-codex`, `bcu_router.py`, `bcu_games.py`, and `BCUStatus.swift` together:

```sh
git clone https://github.com/alexdr0/bobocodexultra.git
cd bobocodexultra
python3 openrouter-codex install
export PATH="$HOME/.local/bin:$PATH"  # Current terminal only
bobocodexultra --help
```

`bobocodexultra` and its alias `boboultracodex` install into `~/.local/bin`. Add that directory to your shell's PATH in your shell startup configuration to use the command in future terminals. You do not need `sudo`.

```sh
bobocodexultra login    # Secure Keychain prompt; activates shared desktop mode
bobocodexultra models   # Search and choose which BCU models appear
bobocodexultra doctor   # Check the local router and Codex integration
```

Quit and reopen Codex Desktop to refresh its model selector. Your native ChatGPT and existing Ollama models remain available alongside entries labeled `[Model Name] (BCU)`. To return to the previous native setup, run `bobocodexultra off` and reopen Codex. The optional menu bar companion installs with `bobocodexultra menu install`.

Credentials are entered using macOS Keychain's secure terminal prompt; never put a key into a command argument, commit, issue, or assistant message. If you only want offline Snake, Pong, and Doom, the installation is enough—no key or desktop configuration is needed.

## Set up your Codex agents

BCU routes model requests; Codex itself spawns and manages subagents. After selecting your models, edit your **user-level** `~/.codex/config.toml` (or `$CODEX_HOME/config.toml` if you use a custom Codex home). Add these settings to its existing `[agents]` table, or create the table once if none exists:

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 2
```

Multi-agent tools are enabled by default, but the explicit settings make your intention and concurrency limit clear. For children to use a particular BCU model, run `bobocodexultra model list`, copy a **selected model's exact ID**, and add one line under that same `[agents]` table—for example, only if that ID is selected:

```toml
default_subagent_model = "anthropic/claude-opus-5"
```

Leave `default_subagent_model` unset if you prefer Codex's own default. An explicit model chosen when spawning a child takes precedence. Do not paste the example model ID blindly: choose a model you have access to, and remember that a model shown in the selector is not a guarantee of tool compatibility. Do not create a second `[agents]` table or overwrite existing user settings. Keep provider and authentication settings in the user-level configuration rather than a project's `.codex/config.toml`.

Reopen Codex, choose a `(BCU)` model, and try a small, read-only task asking Codex to delegate two independent checks to subagents and combine their findings. Then repeat with a native model if you want to verify both routes. Delegation still depends on the task's instructions and the selected model's tool behavior. As an **optional billed** CLI-only check, `bobocodexultra codex smoke --agents` exercises the separate OpenRouter CLI profile; it does not validate every Codex Desktop workflow. See the [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml) for the current agent settings.

## macOS menu bar

`bobocodexultra menu install` builds the native Swift companion into `~/Applications/Bobo Codex Ultra.app`, opens it, and enables Launch at Login using a per-user LaunchAgent. A small **circuit-B** appears in the menu bar: the monochrome template version adapts to dark/light menu bars, while the Applications icon uses a violet tile, cyan outline and pink status nodes. There is no Dock icon.

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
bobocodexultra off      # Restore the previous native/Ollama desktop setup
bobocodexultra doctor   # Check the service, provider, endpoint and catalog
bobocodexultra sync     # Refresh the combined catalog
bobocodexultra docs     # Full built-in command guide
bobocodexultra snake    # Offline terminal Snake
bobocodexultra pong     # Offline terminal Pong against the CPU
bobocodexultra doom     # Original terminal maze shooter
```

Quit and reopen Codex after enabling/disabling shared mode or changing selected models. Codex loads its catalog at startup; existing tasks may keep earlier provider settings. BCU preserves the native default when enabling shared mode. Pick any native, Ollama or `(BCU)` model in the desktop selector.

`on` starts a per-user macOS LaunchAgent, which restarts the router after a crash and starts it at login. No root or sudo is required. `off` restores the previous endpoint/catalog/provider and retains unrelated settings changed afterward. Recovery backups are retained. The listener remains available for already-open tasks until they reload; turning off desktop routing does not delete credentials, selections, or usage data.

The model TUI supports `/` search, `S` sort, arrows or J/K scrolling, Page Up/Down, Space multi-select, `D` default, `I` details, Enter save, and Q cancel. Changes are staged until saved. Labels are exactly `[Model Name] (BCU)`, for example `Grok 4.6 (BCU)`. Provider prefixes are removed from labels; request model IDs remain unchanged.

The one-time login is interactive and uses a hidden Keychain prompt. For machines already signed in with BCU, `bobocodexultra on` is enough to activate shared mode. `bobocodexultra login` can also replace the saved key. Use `bobocodexultra auth login --no-desktop` if you only want to update the key.

## Offline terminal arcade

Run `bobocodexultra snake`, `bobocodexultra pong`, or `bobocodexultra doom` from any directory after installation. Games run locally in an interactive UTF-8 terminal, without login, an API key, the router, network access, or model charges. `boboultracodex` works too. Resize the terminal if prompted; press **P** to pause, **R** to restart, and **Q** or **Esc** to quit.

| Game | Controls | Goal |
| --- | --- | --- |
| Snake | Arrow keys or WASD | Eat food; avoid walls and your tail. |
| Pong | Up/Down or W/S | Beat the CPU to seven points. |
| Doom | W/S forward/back; A/D strafe; Left/Right turn; Space shoot; M toggle map | Clear the maze of enemies while preserving health and ammo. |

`doom` is a small original retro-style raycasting game, not id Software's Doom; it includes no Doom assets. See `bobocodexultra docs games` for the built-in controls. The arcade is separate from Codex Desktop's model selector and does not change provider settings.

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

The test suite does not require an API key or incur model charges. See [Contributing](CONTRIBUTING.md) for development guidance and [Security](SECURITY.md) for safe issue reporting.

References: [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [Ollama's local router](https://github.com/ollama/ollama/blob/v0.34.2/internal/proxy/codex_desktop.go), [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview).
