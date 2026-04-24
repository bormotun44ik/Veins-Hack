import sqlite3
from fastapi import APIRouter
from app.errors import BadLayer, PersonNotFound
from app.graph.builder import build_graph
from app.graph.layers import stress_layer, collab_layer, workload_layer, to_json

router = APIRouter()
VALID_LAYERS = {"stress", "collab", "workload"}

@router.get("/graph")
def get_graph(layer: str = "stress"):
    if layer not in VALID_LAYERS:
        raise BadLayer(f"Invalid layer: {layer}. Use: {VALID_LAYERS}")
    from app.db import get_connection
    conn = get_connection()
    G = build_graph(conn)
    layer_fns = {"stress": stress_layer, "collab": collab_layer, "workload": workload_layer}
    sub = layer_fns[layer](G)
    return to_json(sub, layer)

@router.get("/person/{person_id}")
def get_person(person_id: str):
    from app.db import get_connection
    conn = get_connection()
    row = conn.execute("SELECT id, name, role, avatar_url, overload_score, baseline_sentiment, metadata_json FROM people WHERE id=?", (person_id,)).fetchone()
    if not row:
        raise PersonNotFound(person_id)
    score = row[4] or 0.0
    status = "red" if score > 0.7 else "yellow" if score > 0.4 else "green"
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
    import json
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
    count = conn.execute("SELECT COUNT(*) FROM events WHERE person_id=?", (person_id,)).fetchone()[0]
    G = build_graph(conn)
    neighbors = list(G.neighbors(person_id))
    return {"id": row[0], "name": row[1], "role": row[2], "avatar_url": row[3],
            "status": status, "overload_score": score,
            "signals": signals, "mock_signals": mock_signals,
            "neighbors": neighbors, "recent_events_count": count}
