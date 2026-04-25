"""Dashboard FastAPI router — GET /dashboard"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DashboardResponse(BaseModel):
    summary: dict[str, Any]
    attention: list[dict[str, Any]]
    shoutouts: list[dict[str, Any]]
    heatmap: dict[str, dict[str, float]]
    generated_at: str


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    from app.db import get_connection
    from app.dashboard.aggregator import get_summary, get_attention, get_shoutouts, get_heatmap

    conn = get_connection()
    return {
        "summary": get_summary(conn),
        "attention": await get_attention(conn),
        "shoutouts": get_shoutouts(conn),
        "heatmap": get_heatmap(conn),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
