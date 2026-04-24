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
import re
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


def _parse_sentiment(text: str | None) -> float | None:
    """Вытащить число sentiment из LLM-ответа.

    Opus/Sonnet часто игнорируют инструкцию 'only JSON' и возвращают
    markdown-анализ с упоминанием значения. Стратегия:
      1. Попробовать json.loads всей строки.
      2. Попробовать найти JSON-блок через regex.
      3. Последний шанс: явное упоминание "sentiment: -0.8" словом.
      4. Fallback по ключевым словам (negative/frustrated = -0.6).
    """
    if not text:
        return None

    # 1. Pure JSON
    try:
        obj = json.loads(text)
        v = obj.get("sentiment")
        if isinstance(v, (int, float)):
            return max(-1.0, min(1.0, float(v)))
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. JSON-block inside markdown: {"sentiment": -0.8}
    m = re.search(r'\{[^{}]*"sentiment"\s*:\s*(-?\d+(?:\.\d+)?)[^{}]*\}', text)
    if m:
        return max(-1.0, min(1.0, float(m.group(1))))

    # 3. "sentiment: -0.8" / "sentiment = -0.8" / "Sentiment: -0.8"
    m = re.search(r'sentiment["\s:=]+\s*(-?\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if m:
        return max(-1.0, min(1.0, float(m.group(1))))

    # 4. Keyword fallback (rough estimate from wording)
    lowered = text.lower()
    if any(k in lowered for k in ("very negative", "very frustrated", "burnout", "exhaust")):
        return -0.8
    if any(k in lowered for k in ("negative", "frustrated", "stressed")):
        return -0.6
    if any(k in lowered for k in ("positive", "energetic", "healthy")):
        return 0.6
    if any(k in lowered for k in ("neutral", "normal")):
        return 0.0

    return None


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

        recent_sentiment = _parse_sentiment(recent_resp)
        baseline_sentiment = _parse_sentiment(baseline_resp)
        if recent_sentiment is None or baseline_sentiment is None:
            logger.warning("tone_delta: LLM returned unparseable sentiment")
            return 0.0

        delta = baseline_sentiment - recent_sentiment
        return 1.0 / (1.0 + math.exp(-delta * 3))
    except Exception as e:
        logger.error(f"tone_delta error: {e}")
        return 0.0
