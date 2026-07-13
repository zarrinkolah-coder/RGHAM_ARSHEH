#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

from server import init_db, replace_state

if len(sys.argv) != 2:
    raise SystemExit("Usage: python import_json.py path/to/ragham-data.json")
path = Path(sys.argv[1]).expanduser().resolve()
if not path.is_file():
    raise SystemExit(f"File not found: {path}")
value = json.loads(path.read_text(encoding="utf-8-sig"))
if isinstance(value, list):
    value = {"items": value, "contacts": [], "transactions": [], "invoices": [], "movements": [], "users": [], "auditLogs": [], "categories": []}
if not isinstance(value, dict):
    raise SystemExit("The JSON root must be an object or an array of items.")
init_db()
version, state, updated_at = replace_state(value)
print(f"Imported successfully. Version={version}, updated_at={updated_at}")
print(f"Items={len(state.get('items', []))}, users={len(state.get('users', []))}, transactions={len(state.get('transactions', []))}")
