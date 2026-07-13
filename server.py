#!/usr/bin/env python3
"""Ragham Server v2.0 PWA - dependency-free HTTP + SQLite server."""
from __future__ import annotations

import base64
import hmac
import json
import mimetypes
import os
import signal
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.environ.get("RAGHAM_DATA_DIR", BASE_DIR / "data")).resolve()
DB_PATH = Path(os.environ.get("RAGHAM_DB_PATH", DATA_DIR / "ragham.sqlite3")).resolve()
HOST = os.environ.get("RAGHAM_HOST", "0.0.0.0")
PORT = int(os.environ.get("RAGHAM_PORT", os.environ.get("PORT", "8080")))
MAX_BODY_BYTES = int(os.environ.get("RAGHAM_MAX_BODY", str(25 * 1024 * 1024)))
BACKUP_LIMIT = int(os.environ.get("RAGHAM_BACKUP_LIMIT", "100"))
BASIC_USER = os.environ.get("RAGHAM_BASIC_USER", "").strip()
BASIC_PASSWORD = os.environ.get("RAGHAM_BASIC_PASSWORD", "")

STATE_COLLECTIONS = (
    "items",
    "contacts",
    "transactions",
    "invoices",
    "movements",
    "users",
    "auditLogs",
)
STATE_SCALARS = ("categories", "admin", "inventorySource")
DB_LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with DB_LOCK, connect_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL DEFAULT 0,
                payload TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO app_state(id, version, payload, updated_at) VALUES(1, 0, NULL, ?)",
            (utc_now(),),
        )
        conn.commit()


def normalize_state(value: Any) -> dict[str, Any]:
    state = value if isinstance(value, dict) else {}
    for key in STATE_COLLECTIONS:
        if not isinstance(state.get(key), list):
            state[key] = []
    if not isinstance(state.get("categories"), list):
        state["categories"] = []
    return state


def read_state() -> tuple[int, dict[str, Any] | None, str]:
    with DB_LOCK, connect_db() as conn:
        row = conn.execute("SELECT version, payload, updated_at FROM app_state WHERE id=1").fetchone()
        if not row:
            return 0, None, utc_now()
        payload = json.loads(row["payload"]) if row["payload"] else None
        return int(row["version"]), payload, str(row["updated_at"])


def object_id(row: Any, fallback: str) -> str:
    if isinstance(row, dict) and row.get("id") is not None:
        return str(row["id"])
    return fallback


def apply_patch(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = normalize_state(json.loads(json.dumps(current, ensure_ascii=False)))
    collections = patch.get("collections") if isinstance(patch, dict) else {}
    scalars = patch.get("scalars") if isinstance(patch, dict) else {}
    if not isinstance(collections, dict):
        collections = {}
    if not isinstance(scalars, dict):
        scalars = {}

    for key, changes in collections.items():
        if key not in STATE_COLLECTIONS or not isinstance(changes, dict):
            continue
        rows = result.get(key, [])
        mapping: dict[str, Any] = {
            object_id(row, f"__index_{index}"): row for index, row in enumerate(rows)
        }
        deletes = changes.get("deletes", [])
        if isinstance(deletes, list):
            for item_id in deletes:
                mapping.pop(str(item_id), None)
        upserts = changes.get("upserts", [])
        if isinstance(upserts, list):
            for index, row in enumerate(upserts):
                if not isinstance(row, dict):
                    continue
                mapping[object_id(row, f"__upsert_{time.time_ns()}_{index}")] = row
        result[key] = list(mapping.values())

    for key, value in scalars.items():
        if key in STATE_SCALARS:
            result[key] = value
    return normalize_state(result)


def save_patch(base_version: int, patch: dict[str, Any]) -> tuple[bool, int, dict[str, Any], str]:
    with DB_LOCK, connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT version, payload FROM app_state WHERE id=1").fetchone()
        current_version = int(row["version"] if row else 0)
        current_state = normalize_state(json.loads(row["payload"])) if row and row["payload"] else normalize_state({})
        if base_version != current_version:
            conn.rollback()
            return False, current_version, current_state, utc_now()

        new_state = apply_patch(current_state, patch)
        new_payload = json.dumps(new_state, ensure_ascii=False, separators=(",", ":"))
        now = utc_now()
        if row and row["payload"]:
            conn.execute(
                "INSERT INTO state_backups(version, payload, created_at) VALUES(?, ?, ?)",
                (current_version, row["payload"], now),
            )
        new_version = current_version + 1
        conn.execute(
            "UPDATE app_state SET version=?, payload=?, updated_at=? WHERE id=1",
            (new_version, new_payload, now),
        )
        if BACKUP_LIMIT > 0:
            conn.execute(
                "DELETE FROM state_backups WHERE id NOT IN (SELECT id FROM state_backups ORDER BY id DESC LIMIT ?)",
                (BACKUP_LIMIT,),
            )
        conn.commit()
        return True, new_version, new_state, now


def replace_state(value: Any) -> tuple[int, dict[str, Any], str]:
    new_state = normalize_state(value)
    with DB_LOCK, connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT version, payload FROM app_state WHERE id=1").fetchone()
        current_version = int(row["version"] if row else 0)
        now = utc_now()
        if row and row["payload"]:
            conn.execute(
                "INSERT INTO state_backups(version, payload, created_at) VALUES(?, ?, ?)",
                (current_version, row["payload"], now),
            )
        version = current_version + 1
        conn.execute(
            "UPDATE app_state SET version=?, payload=?, updated_at=? WHERE id=1",
            (version, json.dumps(new_state, ensure_ascii=False, separators=(",", ":")), now),
        )
        if BACKUP_LIMIT > 0:
            conn.execute(
                "DELETE FROM state_backups WHERE id NOT IN (SELECT id FROM state_backups ORDER BY id DESC LIMIT ?)",
                (BACKUP_LIMIT,),
            )
        conn.commit()
        return version, new_state, now


class RaghamHandler(SimpleHTTPRequestHandler):
    server_version = "RaghamServer/2.0-PWA"
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{utc_now()}] {self.client_address[0]} - {fmt % args}")

    def end_headers(self) -> None:
        path = urlparse(self.path).path
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; connect-src 'self'; font-src 'self' data:; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'self'; form-action 'self'; manifest-src 'self'; worker-src 'self' blob:",
        )
        if path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        elif path in ("/", "/index.html", "/service-worker.js", "/manifest.webmanifest"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        else:
            self.send_header("Cache-Control", "public, max-age=3600")
        if path == "/service-worker.js":
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def require_site_auth(self) -> bool:
        if not BASIC_USER:
            return True
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
                user, password = decoded.split(":", 1)
                if hmac.compare_digest(user, BASIC_USER) and hmac.compare_digest(password, BASIC_PASSWORD):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Ragham Server", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> Any:
        length_value = self.headers.get("Content-Length", "0")
        try:
            length = int(length_value)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise OverflowError("request body too large")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if not self.require_site_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            version, _, updated_at = read_state()
            self.send_json(HTTPStatus.OK, {"ok": True, "version": version, "updated_at": updated_at, "app": "2.1.0-pwa"})
            return
        if parsed.path == "/api/version":
            self.send_json(HTTPStatus.OK, {"name": "Ragham", "version": "2.1.0", "pwa": True})
            return
        if parsed.path == "/api/state":
            version, state, updated_at = read_state()
            self.send_json(HTTPStatus.OK, {"version": version, "state": state, "updated_at": updated_at})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_PATCH(self) -> None:  # noqa: N802
        if not self.require_site_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path != "/api/state":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = self.read_json()
            base_version = int(payload.get("base_version", -1))
            patch = payload.get("patch", {})
            ok, version, state, updated_at = save_patch(base_version, patch)
            if not ok:
                self.send_json(
                    HTTPStatus.CONFLICT,
                    {"error": "version_conflict", "version": version, "state": state, "updated_at": updated_at},
                )
                return
            self.send_json(HTTPStatus.OK, {"ok": True, "version": version, "state": state, "updated_at": updated_at})
        except OverflowError as exc:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
        except Exception as exc:  # pragma: no cover
            print("PATCH error:", repr(exc))
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "server_error"})

    def do_PUT(self) -> None:  # noqa: N802
        if not self.require_site_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path != "/api/state":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = self.read_json()
            value = payload.get("state", payload)
            version, state, updated_at = replace_state(value)
            self.send_json(HTTPStatus.OK, {"ok": True, "version": version, "state": state, "updated_at": updated_at})
        except OverflowError as exc:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json", "detail": str(exc)})
        except Exception as exc:  # pragma: no cover
            print("PUT error:", repr(exc))
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "server_error"})


def main() -> None:
    init_db()
    httpd = ThreadingHTTPServer((HOST, PORT), RaghamHandler)
    httpd.daemon_threads = True

    def stop_server(signum: int, _frame: Any) -> None:
        print(f"\nReceived signal {signum}; stopping Ragham Server...")
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop_server)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_server)

    print("=" * 58)
    print("Ragham Server v2.0 PWA")
    print(f"Listening on: http://{HOST}:{PORT}")
    print(f"Database: {DB_PATH}")
    print("Press Ctrl+C to stop.")
    print("=" * 58)
    try:
        httpd.serve_forever(poll_interval=0.5)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
