import sqlite3
from app.llm.cache import make_prompt_hash, get_cached, set_cached

def make_db():
    conn = sqlite3.connect(':memory:')
    conn.execute("""CREATE TABLE llm_cache (
        prompt_hash TEXT PRIMARY KEY, model TEXT, response TEXT, created_at TEXT)""")
    return conn

def test_cache_roundtrip():
    conn = make_db()
    h = make_prompt_hash("sys", "user", "opus")
    assert get_cached(h, conn) is None
    set_cached(h, "opus", '{"insights": []}', conn)
    assert get_cached(h, conn) == '{"insights": []}'
