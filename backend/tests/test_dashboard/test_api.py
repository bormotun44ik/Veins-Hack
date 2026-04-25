"""Happy-path tests for /dashboard endpoint."""
import json
import sqlite3
import pytest


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE people (
        id TEXT PRIMARY KEY, name TEXT, role TEXT, avatar_url TEXT,
        overload_score REAL DEFAULT 0.0, baseline_sentiment REAL DEFAULT 0.0,
        metadata_json TEXT DEFAULT '{}'
    )""")
    conn.execute("""CREATE TABLE events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT, type TEXT,
        timestamp TEXT, payload_json TEXT
    )""")
    conn.execute("""CREATE TABLE llm_cache (
        prompt_hash TEXT PRIMARY KEY, model TEXT, response TEXT, created_at TEXT
    )""")
    people = [
        ("ivan",  "Ivan Petrov",   "Senior Backend Engineer", "https://i.pravatar.cc/150?u=ivan",  0.78, 0.0, '{}'),
        ("maria", "Maria Ivanova", "Tech Lead",               "https://i.pravatar.cc/150?u=maria", 0.34, 0.0, '{}'),
        ("tom",   "Tom Schneider", "DevOps Engineer",         "https://i.pravatar.cc/150?u=tom",   0.37, 0.0, '{}'),
        ("anna",  "Anna Kowalska", "Frontend Engineer",       "https://i.pravatar.cc/150?u=anna",  0.26, 0.0, '{}'),
        ("peter", "Peter Dimitrov","QA Engineer",             "https://i.pravatar.cc/150?u=peter", 0.20, 0.0, '{}'),
    ]
    conn.executemany(
        "INSERT INTO people VALUES (?,?,?,?,?,?,?)", people
    )
    conn.commit()
    return conn


def test_get_summary():
    from app.dashboard.aggregator import get_summary
    conn = _make_db()
    s = get_summary(conn)
    assert s["red_count"] == 1
    assert s["green_count"] >= 2
    assert s["peak"]["person_id"] == "ivan"
    assert s["avg_overload"] > 0


def test_get_shoutouts():
    from app.dashboard.aggregator import get_shoutouts
    conn = _make_db()
    shoutouts = get_shoutouts(conn)
    ids = [s["person_id"] for s in shoutouts]
    assert "peter" in ids
    assert len(shoutouts) <= 3
    # sorted asc by overload
    scores = [s["overload_score"] for s in shoutouts]
    assert scores == sorted(scores)


def test_get_heatmap():
    from app.dashboard.aggregator import get_heatmap
    conn = _make_db()
    heatmap = get_heatmap(conn)
    assert "ivan" in heatmap
    assert len(heatmap) == 5
    ivan_entry = heatmap["ivan"]
    assert "commit_tone_delta" in ivan_entry
    for v in ivan_entry.values():
        assert 0.0 <= v <= 1.0
