# BCU Desktop and macOS setup

BCU Desktop is a compact native SwiftUI/AppKit app with an understated sidebar, light/dark appearance, and a first-run setup assistant. Its interface takes inspiration from simple model-management apps such as Ollama, but uses BCU's own name, icon and controls. BCU is independent of Ollama, OpenAI and OpenRouter.

## Install from a disk image

When a release supplies a `BoboCodexUltra-<version>-<architecture>.dmg`, open it, drag **Bobo Codex Ultra** into **Applications**, then open the copied app. You can also copy it into your own `~/Applications` folder. Do not enable launch at login while running from the mounted disk image. Disk images are architecture-specific; use `arm64` for Apple silicon and `x86_64` for Intel.

The app needs macOS 13+, a separately installed **Python 3.14+**, and the Codex desktop app/CLI. The disk image contains compiled BCU and its public Python source, **not** a Python runtime. Installing the packaged app does not require Swift or developer tools. The assistant detects common Python installations and offers official download/setup links if prerequisites are missing. It never silently downloads or executes third-party installers.

The seven setup steps are:

1. **Welcome:** explain installation and what BCU will change.
2. **Check:** detect Python/Codex CLI and validate existing configuration without modifying it.
3. **Install:** put the global CLI in `~/.local/bin` and prepare model metadata. No root or `sudo` is needed. Add `~/.local/bin` to your shell PATH if needed; the desktop app does not require that PATH change.
4. **Connect:** enter the OpenRouter key in a native secure field; an existing key can be reused without reading it.
5. **Models:** select the lineup and default thinking effort. Return to Setup after browsing models.
6. **Enable:** explicitly opt into shared routing, or leave the existing endpoint unchanged. Wait for active requests to finish before enabling/restarting routing.
7. **Finish:** optionally enable launch at login, open Codex, or visit Agents to configure subagent defaults.

Steps only advance after their action succeeds. Existing configuration, selected models and usage history are reused. Quitting and reopening the assistant starts its navigation at Welcome, but completed installation/configuration is retained. Setup can be revisited from the sidebar at any time.

## One app, one menu icon

The sidebar contains **Overview**, **Setup**, **Models**, **Account**, **Agents**, **Routing**, **Usage** and **Settings**. The menu-bar icon belongs to this same app and opens the same window and state. There is no second menu companion to configure.

Closing the window keeps the icon available and hides the Dock icon. Reopening BCU or choosing **Open BCU…** restores the desktop window. Login launches use `--background` and do not open the window. **Quit BCU** closes both the desktop UI and its menu icon, but does **not** stop the separately managed routing service. Use Overview to turn shared routing off and restore the previous native/Ollama endpoint.

BCU retains the original menu app's bundle identifier and login-item label so an existing installation uses the same identity. Quit the old app before replacing it; do not keep two app copies running. The existing `menu` commands remain aliases for opening/installing the unified desktop app:

```sh
bobocodexultra app          # Open the desktop app
bobocodexultra app install  # Build/install from source (requires Apple's Swift compiler)
bobocodexultra menu         # Compatibility alias
```

## Configuration

- **Models:** browse/search/sort, add/remove, set a default, and choose low/medium/high reasoning per selected model. BCU does not promise that every upstream supports every effort. Reopen Codex to refresh selector metadata.
- **Account:** replace the key in macOS Keychain without exposing the saved value or activating routing. macOS can ask for Keychain permission; BCU never dismisses that consent automatically.
- **Agents:** select a model, thinking effort and concurrency limit, or restore earlier defaults. Writes go through the same CLI backup/ownership checks as terminal setup. Explicit custom-agent configuration can override these defaults.
- **Routing:** edit all documented concurrency, queue, retry and memory limits. Save validates the values and backs up the previous JSON; it does **not** restart the router. **Apply / restart router…** requires an explicit confirmation and should be used only while requests are idle. Doctor and traffic diagnostics are available here.
- **Usage:** the existing desktop/legacy accounting report, with search, date filters and separately labeled cost estimates. [Accounting details](USAGE.md).
- **Settings:** system/light/dark appearance, launch at login, setup, CLI repair and documentation.

The app invokes the bundled CLI directly with a detected Python interpreter. It does not depend on shell initialization and does not rewrite unrelated Codex settings. Native ChatGPT and Ollama models are unaffected by BCU reasoning/default settings.

## Credential boundary

New keys travel from a native `SecureField` directly to macOS Security APIs. The field is cleared on submission or when leaving Account. No key is passed in process arguments, environment variables, configuration, logs or analytics. The UI never retrieves the saved value.

New login-Keychain items grant access only to BCU and Apple's `/usr/bin/security` helper, which the existing router uses. Existing items retain their access controls when updated, so macOS may ask permission. The classic macOS Keychain access-control APIs used for this compatibility are deprecated by Apple; BCU intentionally does not switch existing users to a separate app-only Keychain inaccessible to their router. The CLI's interactive Keychain login remains available as a fallback.

## Build and distribution

From the full source folder on macOS with Python 3.14+ and Apple's Swift compiler:

```sh
python3 openrouter-codex app build --output dist
```

This creates a compressed, drag-to-Applications disk image for the build Mac's architecture. It refuses to overwrite an existing image. Builds target macOS 13, include public source and license files from an explicit allowlist, and omit local paths/runtime hints from the distributable app's `Info.plist`. Compiled source paths are remapped to `/BCU`. Private configs, credentials, model selections, logs and usage databases are never copied. `dist/`, `.app` and `.dmg` outputs are Git-ignored.

**Signing limitation:** these builds are ad-hoc signed, not Developer ID signed or Apple-notarized. Gatekeeper may warn or block a downloaded build. BCU does not remove quarantine or disable Gatekeeper. For warning-free public distribution, a maintainer must sign the final bundle with a Developer ID Application certificate, submit the image using Apple's notarization service, and staple the ticket before publishing. Apple Development certificates are not substitutes for Developer ID distribution certificates. Source installation remains available if you do not want to trust an unnotarized binary.

The build does not publish or upload an installer automatically.
