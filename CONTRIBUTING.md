# Contributing

BCU has three moving pieces: `openrouter-codex` manages the Codex configuration, terminal model picker and installation; `bcu_router.py` handles model-based HTTP routing; `BCUStatus.swift` is the optional native menu bar companion. `bcu_games.py` implements the offline terminal arcade. Keep the macOS Keychain as the only persistent API-key store. No credentials, bearer tokens, cookies, prompts, generated text, private model selections, local configuration or runtime databases belong in commits or test output.

Use Python 3.14+ on macOS. Run the tests without a real key:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -q
```

The routing tests start temporary loopback HTTP servers and mock both upstreams. They need local socket permission, but no public network access or billing. Tests should cover provider choice, auth-header separation, concurrent subagent requests, streaming, and `off` recovery when those areas change.

Before opening a pull request, check that `README.md`, `docs/ARCHITECTURE.md`, `docs/MENUBAR.md`, and `docs/TROUBLESHOOTING.md` match observable behavior. Describe any Responses API tool types or state transitions you cannot faithfully translate. Do not send live customer data through test providers. An optional billed smoke check against your own account is `bobocodexultra codex smoke --agents`.

The repository intentionally does not contain real `$CODEX_HOME` contents or macOS Keychain items. If you report a bug, share only a redacted `bobocodexultra doctor` summary and relevant sanitized errors.
