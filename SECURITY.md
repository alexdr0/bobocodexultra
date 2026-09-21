# Security and privacy

Please do not include an API key, authorization header, cookie, ChatGPT account ID, conversation transcript, local rollout, or unredacted configuration in a GitHub issue or pull request. Revoke a key immediately if it is exposed.

Before making a fork or release public, run `python3 scripts/check_public_safety.py` and review all tracked files and commit metadata manually. The checker scans reachable Git history for common credential, personal-email, and local-home-path patterns without printing any matching values. It cannot prove that a repository is free of every private detail. `.gitignore` prevents new local state from being added accidentally, but it cannot hide a secret already present in Git history.

BCU stores the OpenRouter credential in macOS Keychain. It binds its HTTP service only to `127.0.0.1:11435`, rejects browser-origin and unexpected-host requests, and sends an allowlisted set of headers to OpenRouter. Native ChatGPT/Ollama requests retain their existing authentication and go only to the previously configured native endpoint. Other processes running under your macOS account can still access loopback; protect your local session accordingly.

Report a vulnerability privately through GitHub's vulnerability-reporting feature if it is available for this repository. If not available, file a minimal issue asking the maintainer for a private reporting channel, with no exploit details or secrets in the public issue.

For a routing concern, run `bobocodexultra off`, quit and reopen Codex, then inspect `bobocodexultra doctor`. Turning off BCU restores the previously configured native endpoint while retaining recovery backups.
