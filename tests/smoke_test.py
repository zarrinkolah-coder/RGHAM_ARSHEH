#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def load_server(temp_dir: str):
    os.environ["RAGHAM_DATA_DIR"] = temp_dir
    os.environ["RAGHAM_DB_PATH"] = str(Path(temp_dir) / "test.sqlite3")
    os.environ["RAGHAM_BACKUP_LIMIT"] = "2"
    spec = importlib.util.spec_from_file_location("ragham_server_test", ROOT / "server.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_pwa_files() -> None:
    required = [
        STATIC / "index.html",
        STATIC / "styles.css",
        STATIC / "app.js",
        STATIC / "manifest.webmanifest",
        STATIC / "service-worker.js",
        STATIC / "offline.html",
        STATIC / "icons/icon-192.png",
        STATIC / "icons/icon-512.png",
        STATIC / "icons/icon-maskable-192.png",
        STATIC / "icons/icon-maskable-512.png",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert not missing, f"missing PWA files: {missing}"

    manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    for key in ("name", "short_name", "start_url", "scope", "display", "icons"):
        assert manifest.get(key), f"manifest field missing: {key}"
    assert manifest["display"] == "standalone"
    sizes = {icon.get("sizes") for icon in manifest["icons"]}
    assert "192x192" in sizes and "512x512" in sizes
    assert any("maskable" in icon.get("purpose", "") for icon in manifest["icons"])

    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html
    assert 'src="./app.js"' in html
    assert 'href="./styles.css"' in html
    assert "fonts.googleapis.com" not in html
    assert "fonts.googleapis.com" not in (STATIC / "styles.css").read_text(encoding="utf-8")

    app_js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "serviceWorker.register" in app_js
    assert "beforeinstallprompt" in app_js
    assert "SERVER_PENDING_KEY" in app_js


def validate_database() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        server = load_server(temp_dir)
        server.init_db()
        version, state, _ = server.read_state()
        assert version == 0 and state is None

        first = {
            "items": [{"id": "i1", "name": "کالای آزمایشی"}],
            "contacts": [],
            "transactions": [],
            "invoices": [],
            "movements": [],
            "users": [],
            "auditLogs": [],
            "categories": ["آزمایش"],
            "admin": {"id": "admin", "name": "مدیر"},
        }
        version, saved, _ = server.replace_state(first)
        assert version == 1 and saved["items"][0]["id"] == "i1"

        ok, version, saved, _ = server.save_patch(
            1,
            {"collections": {"items": {"upserts": [{"id": "i1", "name": "کالای اصلاح‌شده"}], "deletes": []}}},
        )
        assert ok and version == 2
        assert saved["items"][0]["name"] == "کالای اصلاح‌شده"

        server.replace_state(first)
        server.replace_state(first)
        server.replace_state(first)
        with sqlite3.connect(server.DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM state_backups").fetchone()[0]
        assert count <= 2, f"backup limit not applied: {count}"


def main() -> None:
    validate_pwa_files()
    validate_database()
    print("Ragham PWA smoke tests passed")


if __name__ == "__main__":
    main()
