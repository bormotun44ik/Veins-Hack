"""
Happy-path test for POST /ingest/event.
Uses in-memory SQLite seeded with minimal fixture.
"""
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """In-memory SQLite with minimal schema + one person."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY, name TEXT, role TEXT, avatar_url TEXT,
            overload_score REAL DEFAULT 0.0, baseline_sentiment REAL DEFAULT 0.0,
            metadata_json TEXT
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT, type TEXT, timestamp TEXT, payload_json TEXT
        );
        CREATE TABLE repos (id TEXT PRIMARY KEY, name TEXT, url TEXT);
        CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, priority TEXT,
            status TEXT, deadline TEXT, assignee_id TEXT);
        CREATE TABLE meetings (id TEXT PRIMARY KEY, title TEXT, datetime TEXT, duration_minutes INTEGER);
        CREATE TABLE edges (id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT, dst TEXT,
            type TEXT, weight REAL, metadata_json TEXT);
        CREATE TABLE IF NOT EXISTS llm_cache (
            prompt_hash TEXT PRIMARY KEY, model TEXT, response TEXT, created_at TEXT
        );
        INSERT INTO people VALUES ('ivan','Ivan Petrov','Senior Backend','',0.78,0.1,'{}');
    """)

    import app.db as db_module
    monkeypatch.setattr(db_module, "get_connection", lambda: conn)

    return conn


def test_ingest_commit_happy_path(seeded_db, monkeypatch):
    # Stub out all signal modules to return a constant
    import app.signals.night_commits as nc
    import app.signals.fix_revert as fr
    import app.signals.pr_lag as pl
    import app.signals.bus_factor as bf
    import app.signals.co_isolation as ci
    import app.signals.weekend_activity as wa

    for mod in (nc, fr, pl, bf, ci, wa):
        monkeypatch.setattr(mod, "compute", lambda pid, conn: 0.5)

    from app.main import app
    client = TestClient(app)

    payload = {
        "person_id": "ivan",
        "type": "commit",
        "payload": {"sha": "abc1234", "message": "fix: test", "repo_id": "veins-core",
                    "branch": "main", "co_authors": [], "files_touched": ["src/x.py"]},
    }
    resp = client.post("/ingest/event", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["person_id"] == "ivan"
    assert data["event_id"] > 0
    assert "old_overload_score" in data
    assert "new_overload_score" in data
    assert data["old_status"] in ("red", "yellow", "green")
    assert data["new_status"] in ("red", "yellow", "green")
    assert len(data["recomputed_signals"]) == 6


def test_ingest_person_not_found(seeded_db):
    from app.main import app
    client = TestClient(app)

    resp = client.post("/ingest/event", json={
        "person_id": "nobody",
        "type": "commit",
        "payload": {}
    })
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PERSON_NOT_FOUND"


def test_ingest_invalid_timestamp(seeded_db):
    from app.main import app
    client = TestClient(app)

    resp = client.post("/ingest/event", json={
        "person_id": "ivan",
        "type": "commit",
        "timestamp": "not-a-date",
        "payload": {}
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_EVENT"


def test_ingest_payload_too_large(seeded_db):
    from app.main import app
    client = TestClient(app)

    resp = client.post("/ingest/event", json={
        "person_id": "ivan",
        "type": "commit",
        "payload": {"big": "x" * 60_000}
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_EVENT"
