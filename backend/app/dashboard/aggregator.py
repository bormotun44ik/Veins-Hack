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
    "You output ONE short phrase of 3-4 words describing a person's burnout pattern.\n"
    "\n"
    "CRITICAL RULES:\n"
    "- Output exactly one line with 3-4 words, lowercase.\n"
    "- No markdown, no headings, no tables, no emojis, no bullets.\n"
    "- No quotes around the phrase. No explanation. No analysis.\n"
    "- Maximum 40 characters total.\n"
    "\n"
    "Examples of CORRECT output:\n"
    "  isolated night-firefighter\n"
    "  overwhelmed tech lead\n"
    "  collaborative steady builder\n"
    "  weekend solo crusher\n"
    "\n"
    "Any output longer than one line is wrong."
)


def _sanitize_primary_reason(raw: str) -> str:
    """Trim Sonnet's verbose output to first short line. Defends against markdown/lists.

    Rules:
      - Strip whitespace, quotes, backticks
      - Take only the first non-empty line
      - Drop markdown prefixes (#, *, -, >, |)
      - Cap to 60 chars
      - If result is empty or contains markdown chars after cleanup → return ""
    """
    if not raw:
        return ""
    for raw_line in raw.splitlines():
        line = raw_line.strip().strip("\"'`*_# >|").strip()
        if not line:
            continue
        # Drop common LLM preamble patterns
        if any(line.lower().startswith(p) for p in ("the ", "this ", "here", "person:", "summary", "analysis", "based on")):
            continue
        # Drop lines with table separators or markdown
        if "|" in line or "---" in line or line.startswith(("#", "*", "-")):
            continue
        # Looks like a sensible 3-4 word phrase?
        if 3 <= len(line) <= 60:
            return line[:60]
    return ""


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


def _heuristic_reason(sigs: dict) -> str:
    """Deterministic 3-4 word phrase from signal pattern.

    Sonnet/Opus reliably ignore 'short phrase' instructions and dump markdown
    analysis (verified empirically). Heuristic over signals is faster, free,
    and predictable for the demo.
    """
    night = sigs.get("night_commits_ratio", 0)
    fix = sigs.get("fix_revert_ratio", 0)
    isolation = sigs.get("co_author_isolation", 0)
    bus = sigs.get("bus_factor", 0)
    weekend = sigs.get("weekend_activity", 0)
    pr_lag = sigs.get("pr_review_lag_hours", 0)

    # High-priority composite patterns first
    if night > 0.5 and fix > 0.5 and isolation > 0.5:
        return "isolated night-firefighter"
    if bus > 0.7 and isolation > 0.5:
        return "bus-factor critical"
    if night > 0.5 and weekend > 0.3:
        return "always-on burnout"
    if fix > 0.5 and pr_lag > 0.5:
        return "blocked firefighter"
    if isolation > 0.7:
        return "fully isolated worker"
    if night > 0.5:
        return "night-shift coder"
    if fix > 0.5:
        return "stuck in firefighting"
    if weekend > 0.4:
        return "weekend grinder"
    if pr_lag > 0.5:
        return "review bottleneck"
    return "elevated load"


async def _compute_primary_reason(person: dict, top_insight: str, conn: sqlite3.Connection) -> str:
    """3-4 word burnout pattern. Uses deterministic heuristic over signals.

    Was: LLM call to Sonnet. Sonnet ignored 'short phrase' instruction and
    returned 2KB markdown analysis. Heuristic is more reliable.
    """
    if not top_insight:
        return ""
    try:
        from app.rag.context import build_person_context
        ctx = build_person_context(person["person_id"], conn)
        return _heuristic_reason(ctx.get("signals", {}))
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
