"""
ingest/api.py — POST /ingest/event endpoint.
Live event append + cheap overload recompute.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
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


@router.post("/ingest/event", response_model=IngestEventResponse)
async def ingest_event(body: IngestEventBody):
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

    return {
        "person_id": body.person_id,
        "event_id": event_id,
        "old_overload_score": result["old_score"],
        "new_overload_score": result["new_score"],
        "old_status": _status(result["old_score"]),
        "new_status": _status(result["new_score"]),
        "recomputed_signals": result["recomputed"],
    }
