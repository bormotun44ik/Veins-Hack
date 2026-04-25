import json, re, hashlib, logging
from fastapi import APIRouter
from app.errors import PersonNotFound, LLMUnavailable
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/insights/{person_id}")
async def get_insights(person_id: str):
    from app.db import get_connection
    from app.rag.context import build_person_context
    from app.llm.client import ask
    from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt
    from app.llm.cache import make_prompt_hash
    from datetime import datetime

    conn = get_connection()
    ctx = build_person_context(person_id, conn)
    if not ctx:
        raise PersonNotFound(person_id)

    user = insight_user_prompt(ctx)
    prompt_hash = make_prompt_hash(INSIGHT_SYSTEM, user, "opus")

    # Check cache first
    from app.llm.cache import get_cached
    cached_raw = get_cached(prompt_hash, conn)
    cached_flag = bool(cached_raw)

    if cached_raw:
        raw = cached_raw
    else:
        raw = await ask("opus", INSIGHT_SYSTEM, user, cache_key=prompt_hash)

    # Parse JSON with fallback
    insights, actions = [], []
    try:
        parsed = json.loads(raw)
        insights = parsed.get("insights", [])[:3]
        actions = parsed.get("actions", [])[:3]
    except (json.JSONDecodeError, KeyError):
        found = re.findall(r'"([^"]{20,})"', raw)[:6]
        insights = found[:3]
        actions = found[3:] or found[:3]

    while len(insights) < 3: insights.append("No additional insights available")
    while len(actions) < 3: actions.append("Schedule a 1:1 to discuss workload")

    return {
        "person_id": person_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": "opus",
        "cached": cached_flag,
        "insights": insights,
        "actions": actions,
    }

@router.post("/action/recognition/{person_id}")
async def post_recognition(person_id: str):
    from app.db import get_connection
    from app.rag.context import build_person_context
    from app.llm.client import ask
    from app.llm.prompts import RECOGNITION_SYSTEM, recognition_user_prompt
    from app.llm.cache import make_prompt_hash

    conn = get_connection()
    ctx = build_person_context(person_id, conn)
    if not ctx:
        raise PersonNotFound(person_id)

    user = recognition_user_prompt(ctx)
    # cache_key = prompt_hash чтобы повторные клики на демо были мгновенные
    cache_key = make_prompt_hash(RECOGNITION_SYSTEM, user, "sonnet")
    text = await ask("sonnet", RECOGNITION_SYSTEM, user, cache_key=cache_key)
    return {"person_id": person_id, "text": text}
