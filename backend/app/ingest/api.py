"""
ingest/api.py — POST /ingest/event endpoint.
Live event append + cheap overload recompute + auto-regenerate insights
when person crosses status boundary (green↔yellow↔red).
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.errors import BadEvent, PersonNotFound

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestEventBody(BaseModel):
    person_id: str
    type: Literal["commit", "slack_msg", "meeting_attended", "task_update", "review", "pr"]
    timestamp: str | None = None
    payload: dict


class IngestEventResponse(BaseModel):
    person_id: str
    event_id: int
    old_overload_score: float
    new_overload_score: float
    old_status: str
    new_status: str
    recomputed_signals: list[str]


def _status(score: float) -> str:
    if score > 0.7:
        return "red"
    if score > 0.4:
        return "yellow"
    return "green"


async def _regenerate_insight_bg(person_id: str, old_status: str, new_status: str) -> None:
    """Background task: auto-refresh insight when status flips.

    Called only when green↔yellow↔red transition happens. Keeps the cached
    insight aligned with the current behavioral phase, so when manager clicks
    on the node next time — they see fresh AI analysis matching what just
    happened, not stale text from earlier state.

    NOT invoked on every push (would flood Anthropic + cost). Only on flips.
    """
    try:
        from app.db import get_connection
        from app.llm.client import ask
        from app.llm.cache import make_prompt_hash
        from app.llm.smart_cache import save_insight_snapshot
        from app.errors import LLMUnavailable

        conn = get_connection()

        # Build context — prefer v2 (trend/peer/role)
        ctx = None
        try:
            from app.rag.context_v2 import build_person_context_v2
            ctx = build_person_context_v2(person_id, conn)
        except Exception:
            pass
        if not ctx:
            try:
                from app.rag.context import build_person_context
                ctx = build_person_context(person_id, conn)
            except Exception:
                pass
        if not ctx:
            logger.warning(f"[bg-regen] no context for {person_id}, skipping")
            return

        # Prompts — prefer v2
        try:
            from app.llm.prompts_v2 import (
                INSIGHT_SYSTEM_V2 as INSIGHT_SYSTEM,
                insight_user_prompt_v2 as insight_user_prompt,
            )
        except Exception:
            from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt

        user = insight_user_prompt(ctx)
        prompt_hash = make_prompt_hash(INSIGHT_SYSTEM, user, "opus")

        logger.info(f"[bg-regen] {person_id} status flip {old_status} → {new_status}, regenerating insight")

        try:
            raw = await ask("opus", INSIGHT_SYSTEM, user, cache_key=prompt_hash, fallback_ctx=ctx)
        except LLMUnavailable:
            from app.llm.fallback import generate_fallback_insight
            fb = generate_fallback_insight(ctx)
            save_insight_snapshot(
                person_id, ctx.get("signals", {}),
                fb, "fallback-template", conn,
            )
            logger.info(f"[bg-regen] {person_id} fallback insight saved (LLM unavailable)")
            return

        # Parse and store snapshot
        try:
            parsed = json.loads(raw)
            insights = parsed.get("insights", [])[:3]
            actions = parsed.get("actions", [])[:3]
        except Exception:
            insights, actions = [], []

        # Pad to 3
        while len(insights) < 3:
            insights.append("No additional insights available")
        while len(actions) < 3:
            actions.append("Schedule a 1:1 to discuss workload")

        save_insight_snapshot(
            person_id,
            ctx.get("signals", {}),
            {"insights": insights, "actions": actions},
            "opus",
            conn,
        )
        logger.info(f"[bg-regen] {person_id} insight cached ({len(insights)} insights)")
    except Exception as e:
        logger.error(f"[bg-regen] {person_id} failed: {e}")


@router.post("/ingest/event", response_model=IngestEventResponse)
async def ingest_event(body: IngestEventBody, background: BackgroundTasks):
    from app.db import get_connection
    from app.ingest.recompute import recompute_cheap

    conn = get_connection()

    # Validate person exists
    row = conn.execute("SELECT id FROM people WHERE id=?", (body.person_id,)).fetchone()
    if not row:
        raise PersonNotFound(body.person_id)

    # Validate timestamp format BEFORE any DB writes
    if body.timestamp:
        try:
            datetime.fromisoformat(body.timestamp)
        except ValueError:
            raise BadEvent(f"Invalid timestamp format: '{body.timestamp}' (expected ISO8601)")

    # Validate payload size BEFORE INSERT
    payload_str = json.dumps(body.payload)
    if len(payload_str) > 50_000:
        raise BadEvent(f"Payload too large: {len(payload_str)} bytes (max 50000)")

    ts = body.timestamp or datetime.now(timezone.utc).isoformat()

    cur = conn.execute(
        "INSERT INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
        (body.person_id, body.type, ts, payload_str),
    )
    event_id = cur.lastrowid
    # Commit BEFORE recompute so signals can count the new event
    conn.commit()

    result = recompute_cheap(body.person_id, conn)
    old_status = _status(result["old_score"])
    new_status = _status(result["new_score"])

    # Schedule async insight regeneration ONLY on status flip (option B).
    # Avoids flooding Anthropic on every commit — only when phase actually changes.
    if old_status != new_status:
        background.add_task(_regenerate_insight_bg, body.person_id, old_status, new_status)

    return {
        "person_id": body.person_id,
        "event_id": event_id,
        "old_overload_score": result["old_score"],
        "new_overload_score": result["new_score"],
        "old_status": old_status,
        "new_status": new_status,
        "recomputed_signals": result["recomputed"],
    }
