# BCU menu bar integration

The menu icon is owned by **BCU Desktop**, the same native SwiftUI/AppKit process as the setup assistant and settings window. There is no separate menu app to configure. See [Desktop setup and controls](DESKTOP.md) for the complete guide. Its mark is an **Inter Bold B inside a square outline with sharp corners**. The status-bar image adapts to macOS appearance and dims when shared routing is off. The Applications icon is white on black. Both use the vector outline from [Inter](https://github.com/rsms/inter), at weight 700 and optical size 14, so the font need not be installed. Inter is credited under its [SIL Open Font License](INTER-LICENSE.txt).

`bobocodexultra app install` or the compatible `menu install` compiles and installs `~/Applications/Bobo Codex Ultra.app`, locally signs it, writes a per-user login LaunchAgent, and opens it. A prebuilt `.dmg` can instead be dragged to Applications and configured in Setup. Source builds require Apple's Swift compiler; packaged-app users do not need it. Both need Python 3.14+ and macOS 13+. The original bundle identifier and login label, `com.bobocodexultra.menubar`, are retained. Quit an older BCU Menu before updating and avoid keeping duplicate app copies. The login item has `RunAtLoad` enabled and `KeepAlive` disabled, so an explicit quit stays quit until the next login or manual launch.

The menu shows shared/native mode and router health. **Open BCU…** opens Overview; the routing toggle opens that page for an explicit configuration change. **Manage Models…**, **Account…** and **Usage & Costs…** open their pages in the same window. **Open Codex Desktop** locates Codex by its application identifier. Models supports search, sorting, add/remove, default selection and reasoning controls. Names appear as `[Model Name] (Openrouter)`. Reopen Codex for selector changes to reload.

Closing the window hides the Dock icon and leaves the menu icon available; reopening the app restores the window. Login starts with `--background` and does not open the window. **Quit BCU** closes the window and icon, but leaves the separate router running. Turning routing off restores the earlier native/Ollama configuration. The app and router retain independent login items. Account accepts new keys through a native secure field and writes directly to Keychain; it never displays the saved key. The CLI's terminal login remains supported.

The model manager fetches OpenRouter's public tool-capable catalog and reports network failures. Existing selected models remain in local state. The menu's status refreshes periodically, but Codex loads its model picker at startup.

## Usage & Costs

Choose **Usage & Costs…** to open the shared desktop/legacy OpenRouter usage report. Date filters, model search and token/cost/name sorting accompany separate reported, estimated and known-cost totals. Cached and reasoning counts are visible without double counting. Unknown prices and unreadable history show warnings instead of silently claiming a complete total. Native ChatGPT and Ollama requests are excluded.

The window refreshes local history every 15 seconds while visible. **Refresh** reads local data and cached prices only; **Refresh Prices** fetches OpenRouter's public catalog for fallback estimates. Neither operation reads your API key or makes a model call. See [Usage accounting](USAGE.md) for details.

Quit the old app before updating. This does not interrupt the router or require a Codex restart. Source installation records a local Python hint; distributable apps instead detect supported Python locations at runtime. The app invokes its bundled CLI directly, so Finder/login launches do not depend on shell startup. If Python moves, use **Detect again** in Setup.

To build manually for development on macOS, use `swiftc -O -framework AppKit -framework SwiftUI BCUStatus.swift -o /tmp/bcu-menu-dev`; the packaged installer also creates `.icns`, `Info.plist` and the login item. The menu requires macOS 13 or later and Apple's Swift compiler. The router/CLI requires Python 3.14 or later for built-in zstd decompression.
