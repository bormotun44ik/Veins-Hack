import os, logging
from typing import Literal
import anthropic
logger = logging.getLogger(__name__)

Model = Literal["opus", "sonnet", "haiku"]
MODEL_MAP = {
    "opus": "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

def _get_client() -> anthropic.AsyncAnthropic:
    base_url = os.getenv("SHADOCLAW_BASE_URL", "http://host.docker.internal:8317/v1")
    api_key = os.getenv("SHADOCLAW_API_KEY", "sk-dummy")
    return anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)

async def ask(
    model: Model,
    system: str,
    user: str,
    cache_key: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    from app.db import get_connection
    conn = get_connection()

    prompt_hash = None
    if cache_key:
        from app.llm.cache import make_prompt_hash, get_cached, set_cached
        prompt_hash = make_prompt_hash(system, user, model)
        cached = get_cached(prompt_hash, conn)
        if cached:
            return cached

    client = _get_client()
    try:
        response = await client.messages.create(
            model=MODEL_MAP[model],
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        result = response.content[0].text
        if prompt_hash:
            from app.llm.cache import set_cached
            set_cached(prompt_hash, model, result, conn)
        return result
    except Exception as e:
        logger.error(f"LLM ask error: {e}")
        from app.errors import LLMUnavailable
        raise LLMUnavailable(f"LLM call failed: {e}")
