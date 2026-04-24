import sqlite3, logging
logger = logging.getLogger(__name__)

def ingest_all(conn: sqlite3.Connection) -> dict[str, int]:
    from app.ingest.github import pull_github
    from app.ingest.slack import load_slack
    from app.ingest.jira import load_jira
    from app.ingest.calendar import load_calendar
    from app.ingest.transcript import load_transcript
    results = {}
    for name, fn in [("github", pull_github), ("slack", load_slack),
                     ("jira", load_jira), ("calendar", load_calendar),
                     ("transcript", load_transcript)]:
        try:
            results[name] = fn(conn)
        except Exception as e:
            logger.error(f"Ingest {name} failed: {e}")
            results[name] = 0
    logger.info(f"Ingest complete: {results}")
    return results
