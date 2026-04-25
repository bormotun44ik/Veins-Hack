import json, re, logging
from datetime import datetime
from fastapi import APIRouter
from app.errors import PersonNotFound, LLMUnavailable

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/insights/{person_id}")
async def get_insights(person_id: str):
    from app.db import get_connection
    from app.llm.client import ask
    from app.llm.cache import make_prompt_hash
    from app.llm.smart_cache import get_cached_insight, save_insight_snapshot

    conn = get_connection()

    # Build context — prefer v2 (trend/peer/role), fallback to v1
    ctx = None
    try:
        from app.rag.context_v2 import build_person_context_v2
        ctx = build_person_context_v2(person_id, conn)
    except (ImportError, Exception):
        pass
    if not ctx:
        try:
            from app.rag.context import build_person_context
            ctx = build_person_context(person_id, conn)
        except (ImportError, Exception):
            pass
    if not ctx:
        raise PersonNotFound(person_id)

    # Prompts — prefer v2
    try:
        from app.llm.prompts_v2 import INSIGHT_SYSTEM_V2 as INSIGHT_SYSTEM, \
                                       insight_user_prompt_v2 as insight_user_prompt
    except (ImportError, Exception):
        from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt

    current_signals = ctx.get("signals", {})

    # Smart cache check
    smart_cached = get_cached_insight(person_id, current_signals, conn)
    if smart_cached:
        data = smart_cached["response"]
        return {
            "person_id": person_id,
            "generated_at": smart_cached["created_at"],
            "model": smart_cached["model"],
            "cached": True,
            "smart_cached": True,
            "insights": data.get("insights", []),
            "actions": data.get("actions", []),
        }

    # Build prompt
    user = insight_user_prompt(ctx)
    prompt_hash = make_prompt_hash(INSIGHT_SYSTEM, user, "opus")

    # Check llm_cache (prompt-hash based)
    from app.llm.cache import get_cached
    cached_raw = get_cached(prompt_hash, conn)
    cached_flag = bool(cached_raw)

    fallback_used = False

    if cached_raw:
        raw = cached_raw
    else:
        try:
            raw = await ask("opus", INSIGHT_SYSTEM, user,
                            cache_key=prompt_hash, fallback_ctx=ctx)
        except LLMUnavailable:
            # ask() didn't fallback itself (no fallback_ctx path or fallback also failed)
            from app.llm.fallback import generate_fallback_insight
            fb = generate_fallback_insight(ctx)
            save_insight_snapshot(person_id, current_signals, fb, "fallback-template", conn)
            return {
                "person_id": person_id,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "model": "fallback-template",
                "cached": False,
                "fallback": True,
                "insights": fb["insights"],
                "actions": fb["actions"],
            }

    # Detect if ask() returned fallback JSON (from 5xx handler)
    insights, actions = [], []
    try:
        parsed = json.loads(raw)
        insights = parsed.get("insights", [])[:3]
        actions = parsed.get("actions", [])[:3]
        # If ask() returned fallback template it won't have model field; detect via content
        # Actually we can't distinguish here — treat as normal
    except (json.JSONDecodeError, KeyError):
        found = re.findall(r'"([^"]{20,})"', raw)[:6]
        insights = found[:3]
        actions = found[3:] or found[:3]

    while len(insights) < 3:
        insights.append("No additional insights available")
    while len(actions) < 3:
        actions.append("Schedule a 1:1 to discuss workload")

    result = {"insights": insights, "actions": actions}
    save_insight_snapshot(
        person_id, current_signals, result,
        "opus",
        conn,
    )

    return {
        "person_id": person_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model": "opus",
        "cached": cached_flag,
        "fallback": fallback_used,
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
    cache_key = make_prompt_hash(RECOGNITION_SYSTEM, user, "sonnet")
    text = await ask("sonnet", RECOGNITION_SYSTEM, user, cache_key=cache_key)
    return {"person_id": person_id, "text": text}
