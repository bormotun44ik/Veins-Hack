import json, hashlib, logging
logger = logging.getLogger(__name__)

LLM_AVAILABLE = False
try:
    from app.llm.client import ask
    import asyncio
    LLM_AVAILABLE = True
except ImportError:
    pass

def compute(person_id: str, conn) -> float:
    if not LLM_AVAILABLE:
        return 0.0
    try:
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE person_id=? AND type='commit' ORDER BY timestamp DESC LIMIT 40",
            (person_id,)
        ).fetchall()
        if len(rows) < 5:
            return 0.0
        recent_msgs = [json.loads(r[0]).get('message', '') for r in rows[:20]]
        baseline_msgs = [json.loads(r[0]).get('message', '') for r in rows[20:]]
        if not baseline_msgs:
            return 0.0

        from app.llm.prompts import commit_tone_user_prompt, COMMIT_TONE_SYSTEM
        cache_key = f"commit_tone:{person_id}:{hashlib.md5(str(recent_msgs).encode()).hexdigest()[:8]}"
        recent_resp = asyncio.get_event_loop().run_until_complete(
            ask("sonnet", COMMIT_TONE_SYSTEM, commit_tone_user_prompt(recent_msgs), cache_key)
        )
        recent_sentiment = json.loads(recent_resp).get('sentiment', 0.0)

        cache_key_b = f"commit_tone_base:{person_id}:{hashlib.md5(str(baseline_msgs).encode()).hexdigest()[:8]}"
        baseline_resp = asyncio.get_event_loop().run_until_complete(
            ask("sonnet", COMMIT_TONE_SYSTEM, commit_tone_user_prompt(baseline_msgs), cache_key_b)
        )
        baseline_sentiment = json.loads(baseline_resp).get('sentiment', 0.0)

        delta = baseline_sentiment - recent_sentiment
        import math
        return 1.0 / (1.0 + math.exp(-delta * 3))
    except Exception as e:
        logger.error(f"tone_delta error: {e}")
        return 0.0
