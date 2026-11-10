"""SQLite storage for local development.

PostgreSQL with pgvector remains the production target in the product spec.
SQLite keeps listing, search, and question flows usable on a laptop without
extra services. Semantic ranking is handled by the search agent.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend" / "data" / "pathfinder.db"
DEFAULT_UPLOADS = ROOT / "backend" / "data" / "uploads"
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('family', 'representative', 'admin')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY,
    owner_user_id INTEGER REFERENCES users(id),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    website TEXT NOT NULL DEFAULT '',
    street TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT '',
    postal_code TEXT NOT NULL DEFAULT '',
    care_levels TEXT NOT NULL DEFAULT '[]',
    amenities TEXT NOT NULL DEFAULT '[]',
    staff_ratio TEXT NOT NULL DEFAULT '',
    license_number TEXT NOT NULL DEFAULT '',
    license_state TEXT NOT NULL DEFAULT '',
    beds_available INTEGER,
    waitlist INTEGER NOT NULL DEFAULT 0,
    availability_notes TEXT NOT NULL DEFAULT '',
    policies TEXT NOT NULL DEFAULT '',
    validation_status TEXT NOT NULL DEFAULT 'draft',
    validation_flags TEXT NOT NULL DEFAULT '[]',
    published INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing_tiers (
    id INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    care_level TEXT NOT NULL DEFAULT '',
    monthly_min REAL,
    monthly_max REAL,
    includes TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    field_key TEXT NOT NULL,
    label TEXT NOT NULL,
    value_text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_label TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    last_checked TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    facility_id INTEGER NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    stored_name TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    facility_id INTEGER,
    user_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    return Path(os.environ.get("PATHFINDER_DB", DEFAULT_DB))


def upload_dir() -> Path:
    return Path(os.environ.get("PATHFINDER_UPLOADS", DEFAULT_UPLOADS))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    upload_dir().mkdir(parents=True, exist_ok=True)
    with LOCK:
        connection = connect()
        try:
            connection.executescript(SCHEMA)
            connection.commit()
        finally:
            connection.close()
