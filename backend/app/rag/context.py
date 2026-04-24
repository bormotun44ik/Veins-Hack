import json, sqlite3, logging
logger = logging.getLogger(__name__)

def build_person_context(person_id: str, conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT id, name, role, avatar_url, overload_score, baseline_sentiment, metadata_json FROM people WHERE id=?",
        (person_id,)
    ).fetchone()
    if not row:
        return {}

    signals = {}
    try:
        from app.signals import night_commits, fix_revert, pr_lag, bus_factor, co_isolation, weekend_activity
        signals = {
            "night_commits_ratio": night_commits.compute(person_id, conn),
            "fix_revert_ratio": fix_revert.compute(person_id, conn),
            "pr_review_lag_hours": pr_lag.compute(person_id, conn),
            "bus_factor": bus_factor.compute(person_id, conn),
            "co_author_isolation": co_isolation.compute(person_id, conn),
            "weekend_activity": weekend_activity.compute(person_id, conn),
        }
    except ImportError:
        pass

    mock_signals = {}
    try:
        meta = json.loads(row[6] or '{}')
        mock_signals = {
            "slack_silence_days": meta.get("slack_silence_days", 0),
            "velocity_delta": meta.get("velocity_delta", 0.0),
            "back_to_back_meetings_pct": meta.get("back_to_back_meetings_pct", 0.0),
        }
    except Exception:
        pass

    recent_events_raw = conn.execute(
        "SELECT type, timestamp, payload_json FROM events WHERE person_id=? ORDER BY timestamp DESC LIMIT 20",
        (person_id,)
    ).fetchall()
    recent_events = []
    for etype, ets, epj in recent_events_raw:
        try:
            p = json.loads(epj)
            text = p.get('message') or p.get('text') or p.get('title') or ''
            recent_events.append({"type": etype, "timestamp": ets, "short_text": text[:80]})
        except Exception:
            pass

    neighbors = []
    try:
        from app.graph.builder import build_graph
        G = build_graph(conn)
        neighbors = list(G.neighbors(person_id))
    except Exception:
        pass

    ctx = {
        "id": row[0], "name": row[1], "role": row[2],
        "overload_score": row[4] or 0.0,
        "baseline_sentiment": row[5] or 0.0,
        "signals": signals, "mock_signals": mock_signals,
        "recent_events": recent_events, "neighbors": neighbors,
        "recent_events_count": len(recent_events_raw),
    }

    # Size guard
    if len(json.dumps(ctx)) > 12000:
        ctx["recent_events"] = ctx["recent_events"][:8]

    return ctx
