#!/usr/bin/env python3
"""
seed_demo_v2.py — загружает расширенный демо-датасет в SQLite (Phase 3).

7 людей (включая marina/nikita), 200 events за 14 дней, 84 historical_signals (12 нед × 7).

Usage:
    python scripts/seed_demo_v2.py               # seed без сброса (idempotent)
    python scripts/seed_demo_v2.py --fresh        # DELETE данных + переинсертить
    python scripts/seed_demo_v2.py --skip-historical
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
SAMPLES = DATA / "samples"
DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "db" / "veins.db"))

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

CREATE TABLE IF NOT EXISTS historical_signals (
  person_id TEXT NOT NULL,
  week_start TEXT NOT NULL,
  night_commits REAL,
  fix_revert REAL,
  tone_score REAL,
  co_authors_count INTEGER,
  events_count INTEGER,
  PRIMARY KEY (person_id, week_start)
);
"""

# Default overload scores matching CONTRACTS.md §Team roster
OVERLOAD_SCORES = {
    "ivan":   0.78,
    "marina": 0.62,
    "maria":  0.34,
    "tom":    0.37,
    "anna":   0.26,
    "nikita": 0.22,
    "peter":  0.20,
}


def _seed_people(conn: sqlite3.Connection, team: list) -> None:
    for p in team:
        overload = OVERLOAD_SCORES.get(p["id"], 0.3)
        metadata = {k: v for k, v in p.items()
                    if k not in ("id", "name", "role", "avatar_url", "baseline_sentiment")}
        conn.execute(
            """INSERT OR REPLACE INTO people
               (id, name, role, avatar_url, overload_score, baseline_sentiment, metadata_json)
               VALUES (?,?,?,?,?,?,?)""",
            (p["id"], p["name"], p["role"], p["avatar_url"],
             overload, p.get("baseline_sentiment", 0.0),
             json.dumps(metadata))
        )
    conn.commit()
    print(f"  ✅ Seeded {len(team)} people")


def _seed_events(conn: sqlite3.Connection) -> int:
    path = SAMPLES / "sample_events_v2.jsonl"
    if not path.exists():
        print(f"  ⚠️  {path} not found, skipping events")
        return 0

    count = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Skipping malformed line: {e}")
                continue
            conn.execute(
                "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
                (ev["person_id"], ev["type"], ev["timestamp"],
                 json.dumps(ev.get("payload", {})))
            )
            count += 1
    conn.commit()
    print(f"  ✅ Seeded {count} events")
    return count


def _seed_historical(conn: sqlite3.Connection) -> int:
    path = DATA / "historical_signals.json"
    if not path.exists():
        print(f"  ⚠️  {path} not found, skipping historical_signals")
        return 0

    try:
        with open(path) as f:
            hist = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ❌ Failed to load historical_signals.json: {e}")
        return 0

    # Always clear before insert — prevents stale schema issues
    conn.execute("DELETE FROM historical_signals WHERE 1=1")

    count = 0
    for entry in hist:
        conn.execute(
            """INSERT OR REPLACE INTO historical_signals
               (person_id, week_start, night_commits, fix_revert, tone_score,
                co_authors_count, events_count)
               VALUES (?,?,?,?,?,?,?)""",
            (entry["person_id"], entry["week_start"],
             entry.get("night_commits"), entry.get("fix_revert"),
             entry.get("tone_score"), entry.get("co_authors_count"),
             entry.get("events_count"))
        )
        count += 1
    conn.commit()
    print(f"  ✅ Seeded {count} historical_signals")
    return count


def _seed_repos(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO repos (id, name, url) VALUES (?,?,?)",
        ("veins-core", "Veins Core", "https://github.com/bormotun44ik/Veins-Hack")
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Veins demo database (Phase 3 v2)")
    parser.add_argument("--fresh", action="store_true",
                        help="DELETE all data before seeding (keeps schema)")
    parser.add_argument("--skip-historical", action="store_true",
                        help="Skip historical_signals seeding")
    args = parser.parse_args()

    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"🗄️  DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    # Init schema
    conn.executescript(SCHEMA)
    conn.commit()

    if args.fresh:
        print("🧹 --fresh: clearing data tables...")
        for table in ("events", "people", "historical_signals", "edges", "tasks", "meetings", "repos"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        print("  ✅ Cleared")

    # Load team
    team_path = DATA / "fake_team_v2.json"
    try:
        with open(team_path) as f:
            team = json.load(f)
        assert len(team) == 7, f"Expected 7 people, got {len(team)}"
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ Failed to load fake_team_v2.json: {e}")
        conn.close()
        return 1

    print(f"\n👥 Seeding people ({len(team)})...")
    _seed_people(conn, team)

    print("\n📦 Seeding repos...")
    _seed_repos(conn)

    print("\n📝 Seeding events...")
    event_count = _seed_events(conn)

    if not args.skip_historical:
        print("\n📈 Seeding historical_signals...")
        hist_count = _seed_historical(conn)
    else:
        hist_count = 0
        print("\n⏭️  Skipping historical_signals (--skip-historical)")

    # Validation assertions
    people_in_db = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    assert people_in_db == 7, f"Expected 7 people in DB, got {people_in_db}"

    if not args.skip_historical and hist_count > 0:
        hist_in_db = conn.execute("SELECT COUNT(*) FROM historical_signals").fetchone()[0]
        assert hist_in_db == 84, f"Expected 84 historical_signals, got {hist_in_db}"

        hist_ids = {r[0] for r in conn.execute("SELECT DISTINCT person_id FROM historical_signals")}
        team_ids = {p["id"] for p in team}
        assert hist_ids == team_ids, f"historical_signals missing people: {team_ids - hist_ids}"

    conn.close()

    print(f"\n🎉 Done!")
    print(f"   Seeded ~{event_count} events, 7 people, {hist_count} historical_signals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
