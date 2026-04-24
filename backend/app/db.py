import sqlite3, os, logging
logger = logging.getLogger(__name__)
_conn: sqlite3.Connection | None = None

def init_db() -> None:
    from app.config import settings
    os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS people (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT,
        avatar_url TEXT, overload_score REAL DEFAULT 0.0,
        baseline_sentiment REAL DEFAULT 0.0, metadata_json TEXT
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL,
        type TEXT NOT NULL, timestamp TEXT NOT NULL, payload_json TEXT NOT NULL,
        FOREIGN KEY (person_id) REFERENCES people(id)
    );
    CREATE INDEX IF NOT EXISTS idx_events_person_type ON events(person_id, type);
    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
    CREATE TABLE IF NOT EXISTS repos (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, priority TEXT,
        status TEXT, deadline TEXT, assignee_id TEXT,
        FOREIGN KEY (assignee_id) REFERENCES people(id)
    );
    CREATE TABLE IF NOT EXISTS meetings (
        id TEXT PRIMARY KEY, title TEXT, datetime TEXT, duration_minutes INTEGER
    );
    CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, dst TEXT NOT NULL,
        type TEXT NOT NULL, weight REAL DEFAULT 1.0, metadata_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
    CREATE TABLE IF NOT EXISTS llm_cache (
        prompt_hash TEXT PRIMARY KEY, model TEXT NOT NULL,
        response TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    logger.info("DB initialized")

def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        from app.config import settings
        _conn = sqlite3.connect(settings.database_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn
