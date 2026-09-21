"""BCU local routing service: native authentication and per-model upstreams.

Python 3.14+ on macOS. No third-party dependencies. No prompt/header logging.
"""
from __future__ import annotations

import copy
from compression import zstd
from contextlib import contextmanager, closing
import fcntl
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import plistlib
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from urllib.parse import urlsplit

PORT = 11435
BASE = f"http://127.0.0.1:{PORT}/v1"
MAX_BODY = 64 * 1024 * 1024
SERVICE = "com.codex.openrouter-models"
ACCOUNT = "openrouter-api-key"
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length"}
BUILD_ID = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".bcu-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path: Path, value: object) -> None:
    write(path, (json.dumps(value, indent=2) + "\n").encode())


def read_json(path: Path):
    return json.loads(path.read_text())


def root_settings(text: str, values: dict) -> str:
    """Replace/remove only simple root keys, preserving unrelated TOML verbatim."""
    lines = text.splitlines(keepends=True)
    end = next((i for i, line in enumerate(lines) if re.match(r"\s*\[", line)), len(lines))
    found, result = set(), []
    for line in lines[:end]:
        m = re.match(r"\s*([A-Za-z_][\w]*)\s*=", line)
        key = m.group(1) if m else None
        if key not in values:
            result.append(line)
        else:
            if key in found:
                raise ValueError(f"Duplicate config key: {key}")
            found.add(key)
            if values[key] is not None:
                result.append(f"{key} = {json.dumps(values[key])}\n")
    if result and not result[-1].endswith("\n"):
        result[-1] += "\n"
    result.extend(f"{k} = {json.dumps(v)}\n" for k, v in values.items() if k not in found and v is not None)
    merged = "".join(result + lines[end:])
    parsed = tomllib.loads(merged)
    if any((k in parsed if v is None else parsed.get(k) != v) for k, v in values.items()):
        raise ValueError("Root settings could not be safely updated in this TOML layout.")
    return merged


def health(port=PORT) -> dict:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", "/_bcu/health")
        response = conn.getresponse()
        data = json.loads(response.read(16384))
        return data if response.status == 200 and data.get("service") == "bcu" else {}
    except (OSError, ValueError, http.client.HTTPException):
        return {}
    finally:
        conn.close()


class Controller:
    def __init__(self, home: Path, executable: Path | None = None):
        self.home = home.resolve()
        self.directory = self.home / "bcu"
        self.state = self.directory / "state.json"
        self.routes = self.directory / "routes.json"
        self.catalog = self.directory / "models.json"
        self.config = self.home / "config.toml"
        self.executable = executable or Path.home() / ".local/bin/bobocodexultra"
        self.label = "com.bobocodexultra.router." + hashlib.sha256(str(self.home).encode()).hexdigest()[:10]
        self.plist = Path.home() / "Library/LaunchAgents" / (self.label + ".plist")

    @contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.directory / ".lock").open("a") as f:
            os.chmod(f.name, 0o600)
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def native_source(self, parsed: dict) -> Path:
        if parsed.get("model_catalog_json"):
            candidate = Path(parsed["model_catalog_json"]).expanduser().resolve()
        else:
            candidate = self.home / "models_cache.json"
        if candidate == self.catalog or not candidate.is_file():
            raise ValueError("Native model catalog is unavailable. Open Codex in native mode first, then run BCU on.")
        data = read_json(candidate)
        if not data.get("models") or not all(isinstance(m.get("slug"), str) for m in data["models"]):
            raise ValueError("Native model catalog has no usable models; nothing changed.")
        return candidate

    def refresh(self, state=None) -> None:
        state = state or read_json(self.state)
        native = read_json(Path(state["native_catalog"]))["models"]
        selected = read_json(self.home / "openrouter-codex-models.json")["models"]
        native_ids = {m["slug"] for m in native}
        bcu_ids = {m["slug"] for m in selected}
        if native_ids & bcu_ids:
            raise ValueError("Native and BCU model IDs collide; refusing ambiguous routing.")
        combined = copy.deepcopy(native + selected)
        for i, model in enumerate(combined):
            model["priority"] = i
            # Some desktop-produced native catalogs omit this required CLI
            # schema field. Fill only absent capability fields conservatively.
            model.setdefault("supports_parallel_tool_calls", False)
        previous = read_json(self.routes) if self.routes.exists() else {}
        routes = {"native_base": state.get("native_base"),
                  "native_models": sorted(native_ids), "bcu_models": sorted(bcu_ids),
                  "known_bcu_models": sorted(set(previous.get("known_bcu_models", [])) | bcu_ids),
                  "home": str(self.home)}
        # Route new entries before exposing them to the selector. Retired BCU IDs
        # remain reserved so an old task can never send them to ChatGPT by mistake.
        for path, value in ((self.routes, routes), (self.catalog, {"models": combined})):
            encoded = (json.dumps(value, indent=2) + "\n").encode()
            if not path.exists() or path.read_bytes() != encoded:
                write(path, encoded)

    def service_start(self) -> None:
        running = health()
        if running:
            if running.get("home") != str(self.home):
                raise ValueError("Port 11435 belongs to BCU for a different Codex home.")
        else:
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", PORT))
                except OSError as exc:
                    raise ValueError("Port 11435 is occupied by another service; config was not activated.") from exc
        payload = {"Label": self.label, "ProgramArguments": [str(Path(sys.executable).resolve()),
                   str(self.executable), "_serve"], "RunAtLoad": True, "KeepAlive": True,
                   "ThrottleInterval": 3, "WorkingDirectory": str(self.directory),
                   "EnvironmentVariables": {"CODEX_HOME": str(self.home)},
                   "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null"}
        if self.plist.exists() and plistlib.loads(self.plist.read_bytes()).get("Label") != self.label:
            raise ValueError("An unrelated launch agent occupies BCU's service path.")
        write(self.plist, plistlib.dumps(payload))
        if running.get("build") == BUILD_ID:
            return
        domain = f"gui/{os.getuid()}"
        loaded = subprocess.run(["launchctl", "print", f"{domain}/{self.label}"], capture_output=True).returncode == 0
        command = ["launchctl", "kickstart", "-k", f"{domain}/{self.label}"] if loaded else ["launchctl", "bootstrap", domain, str(self.plist)]
        result = subprocess.run(command, capture_output=True)
        if result.returncode:
            raise ValueError("Could not start BCU's login service. Run this command from your macOS desktop session.")
        for _ in range(40):
            running = health()
            if running.get("home") == str(self.home) and running.get("build") == BUILD_ID:
                return
            time.sleep(0.15)
        raise ValueError("BCU service did not become healthy. Config was not activated; run BCU doctor.")

    def enable(self) -> None:
        with self.locked():
            if self.state.exists():
                state = read_json(self.state)
                current = tomllib.loads(self.config.read_text())
                if any(current.get(k) != v for k, v in state["managed"].items()):
                    raise ValueError("BCU settings changed outside the CLI. Run off, then on to capture the new native setup.")
                self.refresh(state)
                self.service_start()
                return
            original = self.config.read_bytes() if self.config.exists() else b""
            parsed = tomllib.loads(original.decode())
            if parsed.get("model_provider", "openai") != "openai":
                raise ValueError("Return to the native OpenAI provider before enabling mixed mode.")
            if parsed.get("profile"):
                raise ValueError("A global profile overrides routing. Clear that profile selection before enabling BCU.")
            native_base = parsed.get("openai_base_url")
            if native_base:
                target = urlsplit(native_base)
                if target.scheme not in ("http", "https") or target.username or target.password or target.query or target.fragment:
                    raise ValueError("Native upstream URL is unsupported.")
                if target.scheme == "http" and target.hostname not in ("127.0.0.1", "localhost", "::1"):
                    raise ValueError("Native HTTP upstream must be loopback-only.")
                if target.hostname in ("127.0.0.1", "localhost") and target.port == PORT:
                    raise ValueError("Native upstream already points at BCU without restore state; refusing a routing loop.")
            managed = {"model_provider": "openai", "openai_base_url": BASE, "model_catalog_json": str(self.catalog)}
            active = root_settings(original.decode(), managed).encode()
            backup = self.directory / "backups" / f"native-{time.time_ns()}.toml"
            write(backup, original)
            state = {"version": 1, "backup": str(backup), "sha256": hashlib.sha256(original).hexdigest(),
                     "native_catalog": str(self.native_source(parsed)), "native_base": native_base,
                     "managed": managed, "original": {k: parsed.get(k) for k in managed},
                     "original_model": parsed.get("model"), "active_sha256": hashlib.sha256(active).hexdigest()}
            self.refresh(state)
            # Start and verify the service before pointing the desktop at it.
            self.service_start()
            write_json(self.state, state)
            if (self.config.read_bytes() if self.config.exists() else b"") != original:
                self.state.unlink()
                raise ValueError("Codex config changed during activation; retry on.")
            write(self.config, active)

    def disable(self) -> None:
        with self.locked():
            if not self.state.exists():
                return
            state = read_json(self.state)
            backup = Path(state["backup"]).resolve()
            if backup.parent != (self.directory / "backups").resolve():
                raise ValueError("Restore backup is outside BCU's backup directory.")
            original = backup.read_bytes()
            if hashlib.sha256(original).hexdigest() != state["sha256"]:
                raise ValueError("Native backup checksum mismatch; config was not changed.")
            current = self.config.read_bytes()
            if hashlib.sha256(current).hexdigest() == state["active_sha256"]:
                restored = original
            else:
                parsed = tomllib.loads(current.decode())
                values = {k: state["original"].get(k) for k, v in state["managed"].items() if parsed.get(k) == v}
                known = read_json(self.routes).get("known_bcu_models", [])
                if parsed.get("model") in known:
                    values["model"] = state.get("original_model")
                restored = root_settings(current.decode(), values).encode()
            write(self.directory / "backups" / f"before-off-{time.time_ns()}.toml", current)
            write(self.config, restored)
            self.state.unlink()
            # Keep the listener available for already-open tasks. They retain
            # their endpoint until Codex restarts. Off changes routing, not auth.


def keychain_key() -> str:
    result = subprocess.run(["/usr/bin/security", "find-generic-password", "-a", ACCOUNT,
                             "-s", SERVICE, "-w"], capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError("OpenRouter key is unavailable. Run bobocodexultra login in Terminal.")
    value = result.stdout.decode().strip()
    if not value or "\n" in value or "\r" in value:
        raise ValueError("Keychain returned an invalid credential.")
    return value


class ToolBridge:
    """Flatten Codex namespace/custom tools and restore the Responses wire shape."""
    def __init__(self, payload: dict):
        self.aliases = {}
        self.names = {}
        tools = []

        def add(items, namespace=None):
            for item in items:
                kind = item.get("type")
                if kind == "namespace":
                    add(item.get("tools", []), item["name"])
                elif kind in ("function", "custom", "tool_search"):
                    item = dict(item)
                    if kind == "tool_search":
                        item["name"] = "tool_search"
                    alias = f"bcu_tool_{len(self.aliases)}"
                    if (namespace, item["name"]) in self.names:
                        continue
                    spec = {"name": item["name"], "namespace": namespace, "custom": kind == "custom", "search": kind == "tool_search"}
                    self.aliases[alias] = spec
                    self.names[(namespace, item["name"])] = alias
                    tool = {"type": "function", "name": alias,
                            "description": f"{namespace + '.' if namespace else ''}{item['name']}: " + (item.get("description") or "")}
                    if kind == "custom":
                        tool["parameters"] = {"type": "object", "properties": {"input": {"type": "string"}},
                                              "required": ["input"], "additionalProperties": False}
                        tool["description"] += "\nPut the complete raw tool input in the input string."
                        if item.get("format"):
                            tool["description"] += "\nRequired input format: " + json.dumps(item["format"])
                    else:
                        tool["parameters"] = item.get("parameters", {"type": "object", "properties": {}})
                    tools.append(tool)
                elif kind in ("web_search", "web_search_preview"):
                    tools.append(item)
                else:
                    raise ValueError(f"OpenRouter bridge does not support tool type {kind!r} yet.")
        add(payload.get("tools") or [])
        # Codex sends newly discovered tool schemas in tool_search_output, not
        # necessarily in the top-level tools array on subsequent turns.
        if isinstance(payload.get("input"), list):
            for item in payload["input"]:
                if item.get("type") == "tool_search_output":
                    add(item.get("tools", []))
        if "tools" in payload:
            payload["tools"] = tools
        if isinstance(payload.get("tool_choice"), dict):
            choice = payload["tool_choice"]
            alias = self.names.get((choice.get("namespace"), choice.get("name")))
            if alias:
                payload["tool_choice"] = {"type": "function", "name": alias}
        self.call_items = {}
        self.reasoning_ids = {}

    def input(self, item: dict) -> dict | None:
        item = copy.deepcopy(item)
        kind = item.get("type")
        if kind in ("reasoning", "compaction", "compaction_trigger"):
            # Provider-encrypted state is not portable. Visible history remains.
            return None
        if kind == "agent_message":
            parts = []
            for part in item.get("content", []):
                text = part.get("text", part.get("encrypted_content", ""))
                if text:
                    parts.append(text)
            return {"type": "message", "role": "user", "content": [{"type": "input_text",
                "text": f"Agent message from {item.get('author', '')} to {item.get('recipient', '')}:\n" + "\n".join(parts)}]}
        if kind == "tool_search_call":
            return {"type": "function_call", "call_id": item["call_id"],
                    "name": self.names.get((None, "tool_search"), "tool_search"),
                    "arguments": json.dumps(item.get("arguments", {}))}
        if kind == "tool_search_output":
            return {"type": "function_call_output", "call_id": item["call_id"],
                    "output": "Discovered tools are now available in your tool definitions. " + json.dumps(item.get("tools", []))}
        if kind in ("function_call", "custom_tool_call"):
            alias = self.names.get((item.get("namespace"), item.get("name")))
            if alias:
                item["name"] = alias
            if kind == "custom_tool_call":
                item["type"] = "function_call"
                item["arguments"] = json.dumps({"input": item.pop("input", "")})
            item.pop("namespace", None)
        elif kind == "custom_tool_call_output":
            item["type"] = "function_call_output"
        if kind == "message" or item.get("role"):
            item.pop("phase", None)
        item.pop("id", None)
        return item

    def output(self, item: dict) -> dict:
        item = copy.deepcopy(item)
        if item.get("type") == "reasoning":
            item["id"] = "rs_bcu_" + item.get("id", "reasoning").removeprefix("rs_bcu_")
        spec = self.aliases.get(item.get("name"))
        if item.get("type") == "function_call" and spec:
            item["name"] = spec["name"]
            if spec["namespace"]:
                item["namespace"] = spec["namespace"]
            if spec["custom"]:
                item["type"] = "custom_tool_call"
                args = item.pop("arguments", "")
                item["input"] = json.loads(args).get("input", "") if args else ""
            elif spec["search"]:
                item.pop("name", None)
                item["type"] = "tool_search_call"
                item["execution"] = "client"
                item["arguments"] = json.loads(item["arguments"]) if item.get("arguments") else {}
        return item

    def event(self, event: dict) -> list[dict]:
        event = copy.deepcopy(event)
        kind = event.get("type", "")
        if isinstance(event.get("item"), dict):
            original = event["item"]
            spec = self.aliases.get(original.get("name"))
            if spec:
                self.call_items[original.get("id")] = spec
            event["item"] = self.output(original)
            if original.get("type") == "reasoning" and original.get("id"):
                self.reasoning_ids[original["id"]] = event["item"]["id"]
        if event.get("item_id") in self.reasoning_ids:
            event["item_id"] = self.reasoning_ids[event["item_id"]]
        if kind.startswith("response.function_call_arguments."):
            spec = self.call_items.get(event.get("item_id"))
            if spec and spec["search"]:
                return []  # Complete search arguments arrive in output_item.done.
            if spec and spec["custom"]:
                if kind.endswith(".delta"):
                    return []
                value = json.loads(event.pop("arguments", "{}" )).get("input", "")
                event["type"] = "response.custom_tool_call_input.done"
                event["input"] = value
                delta = {k: v for k, v in event.items() if k != "input"}
                delta.update(type="response.custom_tool_call_input.delta", delta=value)
                return [delta, event]
        response = event.get("response")
        if isinstance(response, dict) and isinstance(response.get("output"), list):
            response["output"] = [self.output(item) for item in response["output"]]
        return [event]


def normalize(payload: dict) -> tuple[dict, ToolBridge]:
    payload = copy.deepcopy(payload)
    if payload.get("previous_response_id"):
        raise ValueError("OpenRouter requires full history, not previous_response_id. Start a new task after switching providers.")
    if isinstance(payload.get("input"), list) and any(isinstance(i, dict) and i.get("type") == "compaction" for i in payload["input"]):
        raise ValueError("This task contains provider-specific compacted history. Fork/start a new task with a visible summary before switching to BCU.")
    for key in ("previous_response_id", "service_tier", "prompt_cache_key", "prompt_cache_retention",
                "client_metadata", "include", "context_management", "safety_identifier"):
        payload.pop(key, None)
    payload["store"] = False
    reasoning = payload.get("reasoning")
    if isinstance(reasoning, dict):
        reasoning.pop("summary", None)
        if reasoning.get("effort") in ("xhigh", "max", "ultra"):
            reasoning["effort"] = "high"
    bridge = ToolBridge(payload)
    if isinstance(payload.get("input"), list):
        payload["input"] = [new for item in payload["input"] if (new := bridge.input(item)) is not None]
    return payload, bridge


class Ledger:
    """Only counts/IDs, never prompt text, generated text, or credentials."""
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS usage (id TEXT PRIMARY KEY, timestamp REAL, model TEXT, data TEXT)")
            db.commit()
        os.chmod(path, 0o600)

    def record(self, response: dict, model: str):
        if not response.get("id") or not isinstance(response.get("usage"), dict):
            return
        raw = response["usage"]
        data = {k: raw.get(k) for k in ("input_tokens", "output_tokens", "total_tokens", "cost")}
        for key in ("input_tokens_details", "output_tokens_details"):
            details = raw.get(key) or {}
            data[key] = {k: details[k] for k in ("cached_tokens", "reasoning_tokens") if k in details}
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.execute("INSERT OR REPLACE INTO usage VALUES (?, ?, ?, ?)",
                       (response["id"], time.time(), model, json.dumps(data)))
            db.commit()


class RouterServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, routes: Path, key_reader=keychain_key, openrouter_base="https://openrouter.ai/api/v1"):
        self.routes = routes
        self.key_reader = key_reader
        self.openrouter_base = openrouter_base
        self.ledger = Ledger(routes.parent / "usage.sqlite3")
        self.counts = {"native": 0, "openrouter": 0, "errors": 0, "usage_errors": 0}
        self.count_lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(address, Handler)

    def handle_error(self, request, client_address):
        # Never write tracebacks containing provider payloads or credentials.
        with self.count_lock:
            self.counts["errors"] += 1

    def record_usage(self, response, model):
        try:
            self.ledger.record(response, model)
        except sqlite3.Error:
            with self.count_lock:
                self.counts["usage_errors"] += 1


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(120)
        self.started = False

    def error(self, status, message):
        body = json.dumps({"error": {"message": message, "type": "bcu_router_error"}}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def permitted(self):
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in expected or self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site"):
            self.error(403, "BCU accepts local application requests only.")
            return False
        return True

    def do_GET(self):
        if not self.permitted():
            return
        if self.path == "/_bcu/health":
            routes = read_json(self.server.routes)
            body = json.dumps({"service": "bcu", "version": 1, "build": BUILD_ID, "home": routes["home"],
                               "counts": self.server.counts, "models": len(routes["bcu_models"])}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.headers.get("Upgrade", "").lower() == "websocket":
            self.error(426, "BCU uses HTTP Responses streaming; retry over HTTP.")
        else:
            self.error(404, "Unknown BCU route.")

    def do_POST(self):
        if not self.permitted():
            return
        if self.path not in ("/v1/responses", "/v1/responses/compact"):
            self.error(404, "Unknown BCU route.")
            return
        if not self.server.slots.acquire(blocking=False):
            self.error(503, "BCU is handling its maximum concurrent requests; retry shortly.")
            return
        upstream = None
        try:
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Chunked request bodies are unsupported; send Content-Length.")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("Request size is missing or exceeds 64 MiB.")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request body.")
            encoding = self.headers.get("Content-Encoding", "identity").lower()
            if encoding == "zstd":
                decoder = zstd.ZstdDecompressor()
                decoded = decoder.decompress(raw, max_length=MAX_BODY + 1)
                if len(decoded) > MAX_BODY or not decoder.eof or decoder.unused_data:
                    raise ValueError("Compressed body is invalid or too large.")
            elif encoding == "identity":
                decoded = raw
            else:
                raise ValueError("Unsupported request compression.")
            payload = json.loads(decoded)
            if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
                raise ValueError("A model ID is required.")
            model = payload["model"]
            routes = read_json(self.server.routes)
            is_bcu = model in routes["bcu_models"]
            if not is_bcu and (model in routes["known_bcu_models"] or model not in routes["native_models"]):
                self.error(400, "This model is not enabled. Run bobocodexultra models or sync.")
                return
            bridge = None
            if is_bcu:
                if self.path.endswith("/compact"):
                    self.error(400, "OpenRouter has no native compaction endpoint. Use Codex local compaction or start a new task with a summary.")
                    return
                payload, bridge = normalize(payload)
                body = json.dumps(payload).encode()
                # An allowlist prevents ChatGPT/Ollama credentials, cookies, account
                # identifiers and provider-specific headers reaching OpenRouter.
                headers = {"Content-Type": "application/json", "Accept": "text/event-stream" if payload.get("stream") else "application/json",
                           "Authorization": "Bearer " + self.server.key_reader(), "Accept-Encoding": "identity",
                           "User-Agent": "bobocodexultra/2"}
                base = self.server.openrouter_base
            else:
                # Preserve native request bodies/credentials, including compression.
                # The existing Ollama router continues its own per-model dispatch.
                body = raw
                connection_tokens = {v.strip().lower() for v in self.headers.get("Connection", "").split(",")}
                headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP | connection_tokens}
                # Only remove opaque state known to originate from BCU. Native
                # history otherwise passes through byte-for-byte, including zstd.
                if isinstance(payload.get("input"), list):
                    visible = [i for i in payload["input"] if not (i.get("type") == "reasoning" and str(i.get("id", "")).startswith("rs_bcu_"))]
                    if len(visible) != len(payload["input"]):
                        payload["input"] = visible
                        body = json.dumps(payload).encode()
                        headers = {k: v for k, v in headers.items() if k.lower() != "content-encoding"}
                headers["Accept-Encoding"] = "identity"
                base = routes.get("native_base") or ("https://chatgpt.com/backend-api/codex" if self.headers.get("ChatGPT-Account-ID") else "https://api.openai.com/v1")
            target = urlsplit(base)
            connection_type = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
            upstream = connection_type(target.hostname, target.port, timeout=180)
            path = target.path.rstrip("/") + self.path.removeprefix("/v1")
            upstream.request("POST", path, body, headers)
            response = upstream.getresponse()
            if is_bcu and not 200 <= response.status < 300:
                self.error(response.status if response.status >= 400 else 502,
                           f"OpenRouter returned HTTP {response.status}. Check model access, credit, and API compatibility.")
                return
            self.send_response(response.status)
            self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
            # Forward native quota/request metadata without cookies or redirects.
            for k, v in response.getheaders():
                if k.lower().startswith(("x-ratelimit-", "x-codex-")) or k.lower() in ("retry-after", "x-request-id", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Connection", "close")
            self.end_headers()
            self.started = True
            self.close_connection = True
            with self.server.count_lock:
                self.server.counts["openrouter" if is_bcu else "native"] += 1
            if not is_bcu:
                while chunk := response.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            elif "text/event-stream" in response.getheader("Content-Type", ""):
                pending = b""
                while chunk := response.read1(65536):
                    pending += chunk
                    if len(pending) > MAX_BODY:
                        raise ValueError("Oversized stream event.")
                    while b"\n\n" in pending or b"\r\n\r\n" in pending:
                        delimiter = b"\r\n\r\n" if b"\r\n\r\n" in pending and (b"\n\n" not in pending or pending.index(b"\r\n\r\n") < pending.index(b"\n\n")) else b"\n\n"
                        frame, pending = pending.split(delimiter, 1)
                        self.sse(frame, bridge, model)
                if pending.strip():
                    self.sse(pending, bridge, model)
            else:
                result = json.loads(response.read(MAX_BODY + 1))
                self.server.record_usage(result, model)
                result["output"] = [bridge.output(i) for i in result.get("output", [])]
                self.wfile.write(json.dumps(result).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass  # Disconnect cancels the upstream by closing it in finally.
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException, subprocess.TimeoutExpired) as exc:
            with self.server.count_lock:
                self.server.counts["errors"] += 1
            if not self.started:
                # Deliberate validation messages are safe; never print upstream
                # exception bodies, URLs with secrets, subprocess output, or headers.
                message = str(exc) if type(exc) is ValueError and not isinstance(exc, json.JSONDecodeError) else "BCU could not complete this request; run bobocodexultra doctor."
                self.error(400 if isinstance(exc, ValueError) else 502, message)
        finally:
            if upstream:
                upstream.close()
            self.server.slots.release()

    def sse(self, frame, bridge, model):
        data = b"\n".join(line[5:].lstrip() for line in frame.splitlines() if line.startswith(b"data:"))
        if not data or data == b"[DONE]":
            self.wfile.write(frame + b"\n\n")
        else:
            event = json.loads(data)
            response = event.get("response")
            if event.get("type") in ("response.completed", "response.incomplete") and isinstance(response, dict):
                self.server.record_usage(response, model)
            for converted in bridge.event(event):
                self.wfile.write(("data: " + json.dumps(converted) + "\n\n").encode())
        self.wfile.flush()


def serve(home: Path):
    os.umask(0o077)
    control = Controller(home)
    server = RouterServer(("127.0.0.1", PORT), control.routes)

    def refresh_loop():
        while True:
            time.sleep(3)
            if control.state.exists():
                try:
                    with control.locked():
                        control.refresh()
                except (OSError, ValueError, KeyError):
                    with server.count_lock:
                        server.counts["errors"] += 1
    threading.Thread(target=refresh_loop, daemon=True).start()
    server.serve_forever()
