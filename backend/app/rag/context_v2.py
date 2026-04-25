import sqlite3
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_person_context_v2(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    """Extended context builder:
      - все поля из старого build_person_context()
      - + historical_signals_3m_ago
      - + trend_narrative
      - + peer_comparison
      - + role_focus
      - + retrieved_chunks (если Agent P готов; иначе пустой массив)
    """
    try:
        from app.rag.context import build_person_context
        ctx = build_person_context(person_id, conn)
    except ImportError:
        ctx = {}

    if not ctx:
        return ctx  # PersonNotFound — caller бросит exception

    try:
        from app.rag.historical import get_historical_signals, build_trend_narrative
        historical = get_historical_signals(person_id, conn)
        ctx["historical_signals_3m_ago"] = historical
        ctx["trend_narrative"] = build_trend_narrative(
            person_id, historical, ctx.get("signals", {}),
            ctx.get("name", ""), ctx.get("role", "")
        )
    except Exception as e:
        logger.error(f"trend build failed: {e}")
        ctx["historical_signals_3m_ago"] = {}
        ctx["trend_narrative"] = {}

    try:
        ctx["peer_comparison"] = _build_peer_comparison(person_id, conn)
    except Exception as e:
        logger.error(f"peer comp failed: {e}")
        ctx["peer_comparison"] = {}

    try:
        from app.rag.role_focus import get_role_focus
        ctx["role_focus"] = get_role_focus(ctx.get("role", ""))
    except Exception as e:
        logger.error(f"role focus failed: {e}")
        ctx["role_focus"] = {}

    try:
        from app.rag.retrieval import get_relevant_chunks
        ctx["retrieved_chunks"] = get_relevant_chunks(person_id, conn, top_k=8)
    except (ImportError, Exception) as e:
        # Agent P может ещё не быть готов
        ctx["retrieved_chunks"] = []

    return ctx


def _build_peer_comparison(person_id: str, conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT id, role, overload_score FROM people"
    ).fetchall()
    overloads = [r[2] for r in rows if r[2] is not None]
    if not overloads:
        return {}

    team_avg = sum(overloads) / len(overloads)
    sorted_o = sorted(rows, key=lambda r: -(r[2] or 0))
    median = sorted_o[len(sorted_o) // 2][2] if sorted_o else 0

    me = next((r for r in rows if r[0] == person_id), None)
    if not me:
        return {}

    my_overload = me[2] or 0
    rank = next((i + 1 for i, r in enumerate(sorted_o) if r[0] == person_id), len(sorted_o))

    # best peer = наименьший overload в той же роли (или вообще если same-role нет)
    same_role = [r for r in rows if r[1] == me[1] and r[0] != person_id]
    candidates = same_role or [r for r in rows if r[0] != person_id]
    best = min(candidates, key=lambda r: r[2] or 1.0) if candidates else None

    result = {
        "team_avg_overload": round(team_avg, 2),
        "team_median_overload": round(median, 2),
        "person_overload": round(my_overload, 2),
        "rank_in_team": rank,
        "team_size": len(rows),
    }
    if best:
        result["best_peer"] = {
            "id": best[0], "role": best[1],
            "overload": round(best[2] or 0, 2),
        }
    return result
