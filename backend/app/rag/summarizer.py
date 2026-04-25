import logging
from typing import Any

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM = """You are a data compactor.
Summarize the given week of work events into ONE concise paragraph (max 50 words).
Preserve: timestamps, sentiment, key actions, blockers, who-with-whom.
Do NOT add interpretation. Just compress facts.
Return ONLY the summary text, no JSON, no headers."""


async def summarize_chunk(person_id: str, week_start: str, events: list[dict]) -> str:
    """Sonnet → 50-word week summary."""
    if not events:
        return ""
    try:
        from app.llm.client import ask
        from app.llm.cache import make_prompt_hash

        event_lines = "\n".join(
            f"- [{e.get('type','?')}] {e.get('timestamp','')[:10]}: "
            f"{(e.get('payload') or {}).get('message','') or (e.get('payload') or {}).get('text','')[:80]}"
            for e in events[:30]
        )

        user = (
            f"Person: {person_id}\n"
            f"Week of: {week_start}\n"
            f"Events ({len(events)}):\n{event_lines}\n\n"
            f"Summarize in <= 50 words."
        )
        cache_key = make_prompt_hash(SUMMARY_SYSTEM, user, "sonnet")
        summary = await ask("sonnet", SUMMARY_SYSTEM, user, cache_key=cache_key)
        return summary.strip()[:500]
    except Exception as e:
        logger.error(f"summarize_chunk failed for {person_id}/{week_start}: {e}")
        return ""
