#!/usr/bin/env python3
"""
seed_demo.py — загружает демо-данные в SQLite БД Veins.

Usage:
    python scripts/seed_demo.py --fresh     # сбросить БД и сидировать заново
    python scripts/seed_demo.py             # сидировать без сброса (idempotent)
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
SAMPLES = DATA / "samples"

DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "db" / "veins.db"))


# ──────────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT,
  avatar_url TEXT,
  overload_score REAL DEFAULT 0.0,
  baseline_sentiment REAL DEFAULT 0.0,
  metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id TEXT NOT NULL,
  type TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY (person_id) REFERENCES people(id)
);
CREATE INDEX IF NOT EXISTS idx_events_person_type ON events(person_id, type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  priority TEXT,
  status TEXT,
  deadline TEXT,
  assignee_id TEXT,
  FOREIGN KEY (assignee_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS meetings (
  id TEXT PRIMARY KEY,
  title TEXT,
  datetime TEXT,
  duration_minutes INTEGER
);

CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  type TEXT NOT NULL,
  weight REAL DEFAULT 1.0,
  metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);

CREATE TABLE IF NOT EXISTS llm_cache (
  prompt_hash TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  response TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def drop_all(conn: sqlite3.Connection) -> None:
    tables = ["llm_cache", "edges", "meetings", "tasks", "repos", "events", "people"]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Loaders
# ──────────────────────────────────────────────────────────────────────────────

def seed_people(conn: sqlite3.Connection) -> int:
    path = DATA / "fake_team.json"
    if not path.exists():
        print(f"  [skip] {path} not found", file=sys.stderr)
        return 0

    team = json.loads(path.read_text())
    count = 0
    for p in team:
        extra = {k: v for k, v in p.items()
                 if k not in ("id", "name", "role", "avatar_url", "baseline_sentiment")}
        conn.execute(
            """INSERT OR REPLACE INTO people
               (id, name, role, avatar_url, overload_score, baseline_sentiment, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                p["id"], p["name"], p.get("role"), p.get("avatar_url"),
                0.0,  # will be recomputed by signals
                p.get("baseline_sentiment", 0.0),
                json.dumps(extra),
            ),
        )
        count += 1

    # Update overload_score from sample_person if available
    sp = SAMPLES / "sample_person.json"
    if sp.exists():
        person = json.loads(sp.read_text())
        conn.execute(
            "UPDATE people SET overload_score = ? WHERE id = ?",
            (person.get("overload_score", 0.0), person["id"]),
        )

    # Hardcode scores from sample_graph
    sg = SAMPLES / "sample_graph.json"
    if sg.exists():
        graph = json.loads(sg.read_text())
        for node in graph.get("nodes", []):
            conn.execute(
                "UPDATE people SET overload_score = ? WHERE id = ?",
                (node.get("overload_score", 0.0), node["id"]),
            )

    conn.commit()
    return count


def seed_events(conn: sqlite3.Connection) -> int:
    path = SAMPLES / "sample_events.jsonl"
    if not path.exists():
        print(f"  [skip] {path} not found", file=sys.stderr)
        return 0

    count = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        ev = json.loads(line)
        conn.execute(
            """INSERT OR IGNORE INTO events (id, person_id, type, timestamp, payload_json)
               VALUES (?, ?, ?, ?, ?)""",
            (ev["id"], ev["person_id"], ev["type"], ev["timestamp"],
             json.dumps(ev["payload"])),
        )
        count += 1
    conn.commit()
    return count


def seed_tasks(conn: sqlite3.Connection) -> int:
    path = DATA / "mock_jira.json"
    if not path.exists():
        return 0
    tasks = json.loads(path.read_text())
    count = 0
    for t in tasks:
        conn.execute(
            """INSERT OR REPLACE INTO tasks (id, title, priority, status, deadline, assignee_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (t["id"], t["title"], t.get("priority"), t.get("status"),
             t.get("deadline"), t.get("assignee_id")),
        )
        count += 1
    conn.commit()
    return count


def seed_meetings(conn: sqlite3.Connection) -> int:
    path = DATA / "mock_calendar.json"
    if not path.exists():
        return 0
    meetings = json.loads(path.read_text())
    count = 0
    for m in meetings:
        conn.execute(
            """INSERT OR REPLACE INTO meetings (id, title, datetime, duration_minutes)
               VALUES (?, ?, ?, ?)""",
            (m["id"], m.get("title"), m.get("datetime"), m.get("duration_minutes")),
        )
        count += 1
    conn.commit()
    return count


def seed_edges(conn: sqlite3.Connection) -> int:
    path = SAMPLES / "sample_graph.json"
    if not path.exists():
        return 0
    graph = json.loads(path.read_text())
    count = 0
    for link in graph.get("links", []):
        conn.execute(
            """INSERT INTO edges (src, dst, type, weight, metadata_json)
               VALUES (?, ?, ?, ?, ?)""",
            (link["source"], link["target"], link["type"],
             link.get("weight", 1.0), json.dumps(link.get("metadata", {}))),
        )
        count += 1
    conn.commit()
    return count


def seed_repos(conn: sqlite3.Connection) -> int:
    repos = [
        ("veins-core", "Veins Core Backend", "https://github.com/bormotun44ik/Veins-Hack"),
        ("veins-frontend", "Veins Frontend", "https://github.com/bormotun44ik/Veins-Hack"),
    ]
    for r in repos:
        conn.execute("INSERT OR IGNORE INTO repos (id, name, url) VALUES (?, ?, ?)", r)
    conn.commit()
    return len(repos)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Veins demo database")
    parser.add_argument("--fresh", action="store_true",
                        help="Drop all tables before seeding (clean slate)")
    args = parser.parse_args()

    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))

    if args.fresh:
        print("🗑  Dropping existing tables…")
        drop_all(conn)

    print("🔧  Initialising schema…")
    init_db(conn)

    print("🌱  Seeding data…")
    n_people   = seed_people(conn)
    n_events   = seed_events(conn)
    n_tasks    = seed_tasks(conn)
    n_meetings = seed_meetings(conn)
    n_edges    = seed_edges(conn)
    n_repos    = seed_repos(conn)

    conn.close()

    print(
        f"\n✅  Seeded {n_events} events, {n_people} people, "
        f"{n_tasks} tasks, {n_meetings} meetings, "
        f"{n_edges} edges, {n_repos} repos"
    )
    print(f"   DB: {db_file.resolve()}")


if __name__ == "__main__":
    main()
