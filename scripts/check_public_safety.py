#!/usr/bin/env python3
"""Heuristic privacy check of every Git blob reachable from local history.

Reports blob identities and paths, never matching secret values. This complements,
but cannot replace, a human review before publishing a repository.
"""

from __future__ import annotations

import re
import subprocess
import sys


PATTERNS = {
    "credential-like value": re.compile(
        rb"(?:sk" + rb"-or-v1-[A-Za-z0-9_-]{20,}|"
        rb"sk-[A-Za-z0-9_-]{40,}|"
        rb"ghp_[A-Za-z0-9]{30,}|"
        rb"github_pat_[A-Za-z0-9_]{40,}|"
        rb"AKIA[0-9A-Z]{16}|"
        rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)"
    ),
    "personal email": re.compile(
        rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    ),
    "absolute home path": re.compile(
        rb"/(?:Users|home)/[A-Za-z0-9._-]+/"
    ),
}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def main() -> int:
    objects = git("rev-list", "--objects", "--all").splitlines()
    seen: set[bytes] = set()
    problems = 0
    for item in objects:
        oid, _, path = item.partition(b" ")
        if oid in seen or git("cat-file", "-t", oid.decode()).strip() != b"blob":
            continue
        seen.add(oid)
        content = git("cat-file", "-p", oid.decode())
        # Binary art can contain metadata too; scan its bytes without echoing them.
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                print(f"Review {label} in blob {oid.decode()[:12]} ({path.decode(errors='replace')})",
                      file=sys.stderr)
                problems += 1
    if problems:
        print(f"Public-safety check found {problems} potential issue(s); do not publish yet.", file=sys.stderr)
        return 1
    print(f"No common credential, personal email, or home-path patterns in {len(seen)} history blobs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
