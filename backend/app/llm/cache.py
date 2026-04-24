import hashlib, json, sqlite3, logging
from datetime import datetime
logger = logging.getLogger(__name__)

def make_prompt_hash(system: str, user: str, model: str) -> str:
    payload = json.dumps({"s": system, "u": user, "m": model}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def get_cached(prompt_hash: str, conn: sqlite3.Connection) -> str | None:
    try:
        row = conn.execute(
            "SELECT response FROM llm_cache WHERE prompt_hash=?", (prompt_hash,)
        ).fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

def set_cached(prompt_hash: str, model: str, response: str, conn: sqlite3.Connection) -> None:
    try:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (prompt_hash, model, response, created_at) VALUES (?,?,?,?)",
            (prompt_hash, model, response, datetime.utcnow().isoformat())
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Cache set error: {e}")
