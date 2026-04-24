"""Tone delta signal — sentiment change vs baseline (main wow-fact).

Вызывается как sync из composite/startup (вне event loop),
так и из async context. Использует дочерний поток с отдельным loop
чтобы не конфликтовать с FastAPI event loop.
"""
import asyncio
import concurrent.futures
import hashlib
import json
import logging
import math
import sqlite3

logger = logging.getLogger(__name__)

LLM_AVAILABLE = False
try:
    from app.llm.client import ask
    LLM_AVAILABLE = True
except ImportError:
    pass


def _run_async(coro):
    """Безопасный запуск coroutine из sync-кода независимо от состояния event loop.

    Если нет running loop — использует asyncio.run().
    Если есть — кидает coroutine в отдельный поток с новым loop.
    """
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def compute(person_id: str, conn: sqlite3.Connection) -> float:
    if not LLM_AVAILABLE:
        return 0.0
    try:
        rows = conn.execute(
            "SELECT payload_json FROM events "
            "WHERE person_id=? AND type='commit' "
            "ORDER BY timestamp DESC LIMIT 40",
            (person_id,),
        ).fetchall()
        if len(rows) < 5:
            return 0.0

        recent_msgs = [json.loads(r[0]).get("message", "") for r in rows[:20]]
        baseline_msgs = [json.loads(r[0]).get("message", "") for r in rows[20:]]
        if not baseline_msgs:
            return 0.0

        from app.llm.prompts import COMMIT_TONE_SYSTEM, commit_tone_user_prompt

        recent_key = (
            f"commit_tone:{person_id}:"
            f"{hashlib.md5(str(recent_msgs).encode()).hexdigest()[:8]}"
        )
        baseline_key = (
            f"commit_tone_base:{person_id}:"
            f"{hashlib.md5(str(baseline_msgs).encode()).hexdigest()[:8]}"
        )

        recent_resp = _run_async(
            ask("sonnet", COMMIT_TONE_SYSTEM, commit_tone_user_prompt(recent_msgs), recent_key)
        )
        baseline_resp = _run_async(
            ask("sonnet", COMMIT_TONE_SYSTEM, commit_tone_user_prompt(baseline_msgs), baseline_key)
        )

        try:
            recent_sentiment = json.loads(recent_resp).get("sentiment", 0.0)
            baseline_sentiment = json.loads(baseline_resp).get("sentiment", 0.0)
        except (json.JSONDecodeError, TypeError):
            logger.warning("tone_delta: LLM returned non-JSON response")
            return 0.0

        delta = baseline_sentiment - recent_sentiment
        return 1.0 / (1.0 + math.exp(-delta * 3))
    except Exception as e:
        logger.error(f"tone_delta error: {e}")
        return 0.0
