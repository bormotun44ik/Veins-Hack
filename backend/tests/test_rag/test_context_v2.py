"""Happy-path tests for Agent N: context_v2, historical, role_focus."""
import sqlite3
import json
import pytest


@pytest.fixture
def conn():
    """In-memory SQLite with minimal schema."""
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            avatar_url TEXT,
            overload_score REAL DEFAULT 0.0,
            baseline_sentiment REAL DEFAULT 0.0,
            metadata_json TEXT
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT,
            type TEXT,
            timestamp TEXT,
            payload_json TEXT
        );
        CREATE TABLE historical_signals (
            person_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            night_commits REAL,
            fix_revert REAL,
            tone_score REAL,
            co_authors_count INTEGER,
            events_count INTEGER,
            PRIMARY KEY (person_id, week_start)
        );
    """)
    c.execute("""INSERT INTO people VALUES
        ('ivan','Ivan Petrov','Senior Backend Engineer',NULL,0.78,0.6,'{}')""")
    c.execute("""INSERT INTO people VALUES
        ('peter','Peter D','QA Engineer',NULL,0.20,0.6,'{}')""")
    c.execute("""INSERT INTO historical_signals VALUES
        ('ivan','2026-01-06',0.10,0.15,0.6,4,20)""")
    c.commit()
    return c


def test_get_historical_signals(conn):
    from app.rag.historical import get_historical_signals
    h = get_historical_signals("ivan", conn)
    assert h["night_commits_ratio"] == pytest.approx(0.10)
    assert h["fix_revert_ratio"] == pytest.approx(0.15)
    assert h["tone_score"] == pytest.approx(0.6)


def test_get_historical_signals_missing(conn):
    from app.rag.historical import get_historical_signals
    h = get_historical_signals("unknown", conn)
    assert h == {}


def test_build_trend_narrative(conn):
    from app.rag.historical import get_historical_signals, build_trend_narrative
    hist = get_historical_signals("ivan", conn)
    current = {"night_commits_ratio": 0.80, "fix_revert_ratio": 0.90}
    trend = build_trend_narrative("ivan", hist, current, "Ivan Petrov", "Senior Backend Engineer")
    assert "3 months ago" in trend["baseline"]
    assert "10%" in trend["baseline"]
    assert "80%" in trend["current"]
    assert trend["delta_summary"]


def test_build_trend_narrative_empty_historical(conn):
    from app.rag.historical import build_trend_narrative
    trend = build_trend_narrative("ivan", {}, {}, "Ivan", "Senior Backend Engineer")
    assert trend == {}


def test_get_role_focus(conn):
    from app.rag.role_focus import get_role_focus
    rf = get_role_focus("Senior Backend Engineer")
    assert "technical debt" in rf["primary_concerns"]
    assert len(rf["manager_questions"]) >= 1


def test_get_role_focus_empty_string():
    from app.rag.role_focus import get_role_focus
    assert get_role_focus("") == {}


def test_get_role_focus_unknown_role():
    from app.rag.role_focus import get_role_focus
    assert get_role_focus("Unknown Role") == {}


def test_peer_comparison(conn):
    from app.rag.context_v2 import _build_peer_comparison
    pc = _build_peer_comparison("ivan", conn)
    assert pc["rank_in_team"] == 1
    assert pc["team_size"] == 2
    assert pc["best_peer"]["id"] == "peter"
    assert pc["team_avg_overload"] == pytest.approx(0.49)
