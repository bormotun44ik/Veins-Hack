"""Dashboard aggregator — pure functions, no FastAPI."""
import asyncio
import hashlib
import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

SIGNAL_KEYS = [
    "night_commits_ratio",
    "fix_revert_ratio",
    "commit_tone_delta",
    "pr_review_lag_hours",
    "bus_factor",
    "co_author_isolation",
    "weekend_activity",
]

PRIMARY_REASON_SYSTEM = (
    "Summarize a person's burnout pattern in 3-4 words. "
    "Examples: 'isolated night-firefighter', 'overwhelmed tech lead', "
    "'collaborative steady builder'. Return ONLY the phrase, no quotes."
)


def _status(score: float) -> str:
    if score > 0.7:
        return "red"
    if score > 0.4:
        return "yellow"
    return "green"


def get_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT id, overload_score FROM people").fetchall()
    if not rows:
        return {"red_count": 0, "yellow_count": 0, "green_count": 0, "avg_overload": 0.0, "peak": None}

    red, yellow, green = 0, 0, 0
    total = 0.0
    peak_pid, peak_score = None, -1.0
    for pid, score in rows:
        total += score
        if score > peak_score:
            peak_score = score
            peak_pid = pid
        if score > 0.7:
            red += 1
        elif score > 0.4:
            yellow += 1
        else:
            green += 1

    return {
        "red_count": red,
        "yellow_count": yellow,
        "green_count": green,
        "avg_overload": round(total / len(rows), 4),
        "peak": {"person_id": peak_pid, "overload_score": round(peak_score, 4)},
    }


def _get_cached_insight(person_id: str, conn: sqlite3.Connection) -> tuple[str, str]:
    """Return (top_insight, top_action) from llm_cache if available."""
    try:
        from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt
        from app.llm.cache import make_prompt_hash, get_cached
        from app.rag.context import build_person_context

        ctx = build_person_context(person_id, conn)
        if not ctx:
            return "", ""
        user = insight_user_prompt(ctx)
        prompt_hash = make_prompt_hash(INSIGHT_SYSTEM, user, "opus")
        raw = get_cached(prompt_hash, conn)
        if not raw:
            return "", ""

        parsed = json.loads(raw)
        insights = parsed.get("insights", [])
        actions = parsed.get("actions", [])
        top_insight = insights[0] if insights else ""
        top_action = actions[0] if actions else ""
        return top_insight, top_action
    except Exception as e:
        logger.error(f"get_cached_insight for {person_id}: {e}")
        return "", ""


async def _compute_primary_reason(person: dict, top_insight: str, conn: sqlite3.Connection) -> str:
    """Generate/cache 3-4 word burnout pattern for person."""
    if not top_insight:
        return ""
    try:
        from app.llm.client import ask
        from app.llm.prompts import insight_user_prompt
        from app.rag.context import build_person_context

        insight_hash = hashlib.sha256(top_insight.encode()).hexdigest()[:16]
        cache_key = f"primary_reason:{person['person_id']}:{insight_hash}"

        ctx = build_person_context(person["person_id"], conn)
        sigs = ctx.get("signals", {})

        user_msg = (
            f"Person: {person['name']}. "
            f"Signals: night={sigs.get('night_commits_ratio', 0):.2f}, "
            f"fix_revert={sigs.get('fix_revert_ratio', 0):.2f}, "
            f"isolation={sigs.get('co_author_isolation', 0):.2f}, "
            f"bus_factor={sigs.get('bus_factor', 0):.2f}, "
            f"weekend={sigs.get('weekend_activity', 0):.2f}"
        )

        reason = await ask("sonnet", PRIMARY_REASON_SYSTEM, user_msg, cache_key=cache_key)
        return reason.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"compute_primary_reason for {person.get('person_id')}: {e}")
        return ""


async def get_attention(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """All red + yellow people, sorted by overload desc, with cached insight + primary_reason."""
    rows = conn.execute(
        "SELECT id, name, role, avatar_url, overload_score FROM people "
        "WHERE overload_score >= 0.4 ORDER BY overload_score DESC"
    ).fetchall()

    people = []
    for pid, name, role, avatar_url, score in rows:
        top_insight, top_action = _get_cached_insight(pid, conn)
        if not top_insight:
            top_insight = "Cache warm-up needed — run scripts/prewarm_cache.py"
            top_action = ""
        people.append({
            "person_id": pid,
            "name": name,
            "role": role,
            "avatar_url": avatar_url or f"https://i.pravatar.cc/150?u={pid}",
            "status": _status(score),
            "overload_score": round(score, 4),
            "top_insight": top_insight,
            "top_action": top_action,
            "primary_reason": "",  # filled below
        })

    # Parallel primary_reason computation
    if people:
        tasks = [
            _compute_primary_reason(p, p["top_insight"], conn)
            for p in people
        ]
        reasons = await asyncio.gather(*tasks)
        for p, r in zip(people, reasons):
            p["primary_reason"] = r

    return people


def get_shoutouts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, name, role, avatar_url, overload_score FROM people "
        "WHERE overload_score < 0.4 ORDER BY overload_score ASC LIMIT 3"
    ).fetchall()
    return [
        {
            "person_id": pid,
            "name": name,
            "role": role,
            "avatar_url": avatar_url or f"https://i.pravatar.cc/150?u={pid}",
            "overload_score": round(score, 4),
        }
        for pid, name, role, avatar_url, score in rows
    ]


def get_heatmap(conn: sqlite3.Connection) -> dict[str, dict[str, float]]:
    rows = conn.execute("SELECT id, metadata_json FROM people").fetchall()

    try:
        from app.signals import night_commits, fix_revert, pr_lag, bus_factor, co_isolation, weekend_activity
        signal_modules = {
            "night_commits_ratio": night_commits,
            "fix_revert_ratio": fix_revert,
            "pr_review_lag_hours": pr_lag,
            "bus_factor": bus_factor,
            "co_author_isolation": co_isolation,
            "weekend_activity": weekend_activity,
        }
    except ImportError:
        signal_modules = {}

    heatmap = {}
    for pid, meta_json in rows:
        meta = {}
        try:
            meta = json.loads(meta_json or "{}")
        except Exception:
            pass

        # tone_delta from cache (0.0 = no data, not misleading 0.5)
        tone = meta.get("tone_delta_cached", 0.0)

        entry: dict[str, float] = {"commit_tone_delta": float(tone)}
        for key, mod in signal_modules.items():
            try:
                entry[key] = float(mod.compute(pid, conn))
            except Exception as e:
                logger.error(f"heatmap signal {key} for {pid}: {e}")
                entry[key] = 0.0

        heatmap[pid] = entry

    return heatmap
