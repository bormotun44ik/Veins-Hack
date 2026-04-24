import sqlite3, json, pytest
from app.signals import night_commits, fix_revert, co_isolation

def make_db():
    conn = sqlite3.connect(':memory:')
    conn.execute("""CREATE TABLE events (
        id INTEGER PRIMARY KEY, person_id TEXT, type TEXT,
        timestamp TEXT, payload_json TEXT)""")
    conn.execute("""CREATE TABLE people (
        id TEXT PRIMARY KEY, name TEXT, role TEXT,
        overload_score REAL DEFAULT 0.0, baseline_sentiment REAL DEFAULT 0.0)""")
    return conn

def test_night_commits_high():
    conn = make_db()
    for i in range(10):
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)",
            (i, 'ivan', 'commit', f'2026-04-10T23:00:00Z',
             json.dumps({'message': 'fix: bug', 'files_touched': [], 'co_authors': []})))
    score = night_commits.compute('ivan', conn)
    assert score > 0.5

def test_fix_revert_high():
    conn = make_db()
    for i in range(10):
        conn.execute("INSERT INTO events VALUES (?,?,?,?,?)",
            (i, 'ivan', 'commit', '2026-04-10T10:00:00Z',
             json.dumps({'message': 'fix: another bug', 'files_touched': [], 'co_authors': []})))
    score = fix_revert.compute('ivan', conn)
    assert score > 0.0

def test_co_isolation_full():
    conn = make_db()
    conn.execute("INSERT INTO events VALUES (1,'ivan','commit','2026-04-10T10:00:00Z',?)",
        (json.dumps({'message': 'feat', 'files_touched': [], 'co_authors': []}),))
    score = co_isolation.compute('ivan', conn)
    assert score == 1.0
