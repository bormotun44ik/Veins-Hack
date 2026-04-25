"""Tests for fallback.py and smart_cache.py (Agent O)."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
import pytest


# ── fallback.py tests ──────────────────────────────────────────────────────

def _make_ctx(**overrides):
    ctx = {
        "name": "Ivan Petrov",
        "role": "Senior Backend Engineer",
        "overload_score": 0.78,
        "signals": {
            "night_commits_ratio": 1.0,
            "fix_revert_ratio": 1.0,
            "commit_tone_delta": -0.7,
            "pr_review_lag_hours": 38.0,
            "bus_factor": 0.78,
            "co_author_isolation": 1.0,
            "weekend_activity": 0.4,
        },
        "trend_narrative": {"delta_summary": "Night 10%→95%"},
        "peer_comparison": {"rank_in_team": 1, "team_avg_overload": 0.32},
        "role_focus": {
            "manager_questions": [
                "Is there an active incident?",
                "Who can pair on auth-module?",
                "Is 1:1 cadence appropriate?",
            ]
        },
    }
    ctx.update(overrides)
    return ctx


def test_fallback_returns_3_insights_3_actions():
    from app.llm.fallback import generate_fallback_insight
    result = generate_fallback_insight(_make_ctx())
    assert len(result["insights"]) == 3
    assert len(result["actions"]) == 3


def test_fallback_no_signals():
    from app.llm.fallback import generate_fallback_insight
    result = generate_fallback_insight({"name": "X", "role": "", "signals": {}})
    assert len(result["insights"]) == 3
    assert len(result["actions"]) == 3


def test_fallback_includes_trend():
    from app.llm.fallback import generate_fallback_insight
    result = generate_fallback_insight(_make_ctx())
    assert any("3mo" in i or "Trend" in i for i in result["insights"])


def test_fallback_includes_peer_rank():
    from app.llm.fallback import generate_fallback_insight
    result = generate_fallback_insight(_make_ctx())
    assert any("Ranks #1" in i for i in result["insights"])


# ── smart_cache.py tests ───────────────────────────────────────────────────

def _mem_conn():
    conn = sqlite3.connect(":memory:")
    from app.llm.smart_cache import init_smart_cache
    init_smart_cache(conn)
    return conn


def test_signals_hash_stable():
    from app.llm.smart_cache import signals_hash
    sigs = {"night_commits_ratio": 0.5, "fix_revert_ratio": 0.3}
    h1 = signals_hash(sigs)
    h2 = signals_hash(sigs)
    assert h1 == h2


def test_signals_hash_small_change_same_bucket():
    from app.llm.smart_cache import signals_hash
    sigs1 = {"night_commits_ratio": 0.50, "fix_revert_ratio": 0.30}
    sigs2 = {"night_commits_ratio": 0.54, "fix_revert_ratio": 0.32}
    # Both within green zone (< 0.4)? No — 0.50 is yellow. Same bucket anyway if within threshold
    # Let's use values well within same bucket
    sigs_a = {"night_commits_ratio": 0.10}
    sigs_b = {"night_commits_ratio": 0.15}
    assert signals_hash(sigs_a) == signals_hash(sigs_b)


def test_signals_hash_status_boundary_changes_hash():
    from app.llm.smart_cache import signals_hash
    sigs_below = {"night_commits_ratio": 0.39}
    sigs_above = {"night_commits_ratio": 0.41}
    assert signals_hash(sigs_below) != signals_hash(sigs_above)


def test_cache_miss_on_empty():
    from app.llm.smart_cache import get_cached_insight
    conn = _mem_conn()
    result = get_cached_insight("ivan", {"night_commits_ratio": 0.8}, conn)
    assert result is None


def test_cache_save_and_hit():
    from app.llm.smart_cache import get_cached_insight, save_insight_snapshot
    conn = _mem_conn()
    sigs = {"night_commits_ratio": 0.8, "fix_revert_ratio": 0.9}
    data = {"insights": ["a", "b", "c"], "actions": ["x", "y", "z"]}
    save_insight_snapshot("ivan", sigs, data, "opus", conn)
    hit = get_cached_insight("ivan", sigs, conn)
    assert hit is not None
    assert hit["response"]["insights"] == ["a", "b", "c"]
    assert hit["model"] == "opus"


def test_cache_miss_after_significant_signal_change():
    from app.llm.smart_cache import get_cached_insight, save_insight_snapshot
    conn = _mem_conn()
    sigs_old = {"night_commits_ratio": 0.10}
    sigs_new = {"night_commits_ratio": 0.80}
    data = {"insights": ["old"], "actions": ["old"]}
    save_insight_snapshot("ivan", sigs_old, data, "opus", conn)
    hit = get_cached_insight("ivan", sigs_new, conn)
    assert hit is None


def test_cache_expired_after_ttl():
    from app.llm.smart_cache import get_cached_insight, save_insight_snapshot, signals_hash
    conn = _mem_conn()
    sigs = {"night_commits_ratio": 0.5}
    data = {"insights": ["x"], "actions": ["y"]}
    sig_hash = signals_hash(sigs)

    # Insert with old timestamp (25h ago)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO signal_snapshots
               (person_id, signals_hash, signals_json, insight_response, model, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
        ("ivan", sig_hash, json.dumps(sigs), json.dumps(data), "opus", old_ts),
    )
    conn.commit()

    hit = get_cached_insight("ivan", sigs, conn)
    assert hit is None  # expired
