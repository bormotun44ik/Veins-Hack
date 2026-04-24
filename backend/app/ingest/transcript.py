import json, os, logging, sqlite3
logger = logging.getLogger(__name__)

def load_transcript(conn: sqlite3.Connection) -> int:
    from app.config import settings

    transcript_path = os.path.join(settings.data_dir, "transcript.json")
    mp3_path = os.path.join(settings.data_dir, "meeting.mp3")

    if not os.path.exists(transcript_path) and os.path.exists(mp3_path):
        logger.info("transcript.json not found, running Groq Whisper...")
        try:
            client = settings.groq_client()
            with open(mp3_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=f,
                    response_format="verbose_json"
                )
            transcript = {
                "meeting_id": "M-2026-04-22-standup",
                "duration_sec": 900,
                "raw_text": result.text,
                "segments": [{"speaker": "unknown", "text": result.text, "start": 0, "end": 900}]
            }
            with open(transcript_path, "w") as f:
                json.dump(transcript, f)
        except Exception as e:
            logger.error(f"Whisper failed: {e}")
            return 0

    if not os.path.exists(transcript_path):
        return 0

    with open(transcript_path) as f:
        t = json.load(f)

    mid = t.get("meeting_id", "M-standup")
    total_words = sum(len(s.get("text","").split()) for s in t.get("segments",[]))

    for seg in t.get("segments", []):
        pid = seg.get("speaker")
        if not pid or pid == "unknown":
            continue
        words = len(seg.get("text","").split())
        ratio = words / total_words if total_words > 0 else 0
        conn.execute(
            "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
            (pid, "meeting_attended", "2026-04-22T09:00:00Z", json.dumps({
                "meeting_id": mid, "talk_ratio": ratio,
                "words_spoken": words, "sentiment": 0.0,
                "interruptions_given": 0, "interruptions_received": 0
            }))
        )
    conn.commit()
    return len(t.get("segments", []))
