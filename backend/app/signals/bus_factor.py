"""Bus factor — доля файлов где person единственный committer."""
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        # Берём person_id из КОЛОНКИ events, не из payload (там его нет).
        rows = conn.execute(
            "SELECT person_id, payload_json FROM events WHERE type='commit'"
        ).fetchall()

        file_owners: dict[str, set[str]] = {}  # file -> set of committer ids
        touched_by_person: set[str] = set()

        for pid, pj in rows:
            try:
                payload = json.loads(pj)
            except (json.JSONDecodeError, TypeError):
                continue
            for f in payload.get("files_touched", []):
                file_owners.setdefault(f, set()).add(pid)
                if pid == person_id:
                    touched_by_person.add(f)

        if not touched_by_person:
            return 0.0

        owned = sum(
            1 for f in touched_by_person if len(file_owners.get(f, set())) == 1
        )
        return owned / len(touched_by_person)
    except Exception as e:
        logger.error(f"bus_factor error: {e}")
        return 0.0
