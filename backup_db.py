#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
import os
import shutil
import sqlite3

base = Path(__file__).resolve().parent
data_dir = Path(os.environ.get("RAGHAM_DATA_DIR", base / "data"))
db = Path(os.environ.get("RAGHAM_DB_PATH", data_dir / "ragham.sqlite3"))
backup_dir = Path(os.environ.get("RAGHAM_BACKUP_DIR", base / "backups"))
backup_dir.mkdir(parents=True, exist_ok=True)
if not db.exists():
    raise SystemExit(f"Database not found: {db}")
target = backup_dir / f"ragham-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
source_conn = sqlite3.connect(db)
target_conn = sqlite3.connect(target)
with target_conn:
    source_conn.backup(target_conn)
target_conn.close()
source_conn.close()
print(target)
