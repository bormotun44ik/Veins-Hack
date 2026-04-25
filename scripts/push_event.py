#!/usr/bin/env python3
"""
push_event.py — Demo push event CLI for Veins-Hack.

Usage:
  python scripts/push_event.py <person_id> <type> [<message>] [--night] [--weekend]

Examples:
  python scripts/push_event.py ivan commit "fix: revert broke prod again" --night
  python scripts/push_event.py ivan slack_msg "не успею к утру"
  python scripts/push_event.py maria commit "feat: new dashboard"
"""

import argparse
import json
import os
import random
import string
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = os.environ.get("BASE", "http://127.0.0.1:8000")

VALID_TYPES = ["commit", "slack_msg", "meeting_attended", "task_update", "review", "pr"]

KNOWN_PEOPLE = ["ivan", "maria", "tom", "anna", "peter"]

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def red(t):    return _c("31", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)


def status_color(s: str, text: str) -> str:
    if s == "red":    return red(text.upper())
    if s == "yellow": return yellow(text.upper())
    return green(text.upper())


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------
def night_timestamp() -> str:
    """Return today's 03:00 UTC (or yesterday's if we haven't passed 03:00 today)."""
    now = datetime.now(timezone.utc)
    night_ts = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now < night_ts:
        night_ts -= timedelta(days=1)
    return night_ts.isoformat()


def weekend_timestamp() -> str:
    """Return last Saturday 14:00 UTC."""
    now = datetime.now(timezone.utc)
    # weekday(): Monday=0, Saturday=5
    days_since_sat = (now.weekday() - 5) % 7
    last_sat = (now - timedelta(days=days_since_sat)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    return last_sat.isoformat()


def now_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------
def rand_sha() -> str:
    return "".join(random.choices("0123456789abcdef", k=7))


def build_payload(event_type: str, message: str | None) -> dict:
    msg = message or "fix: untitled"
    if event_type == "commit":
        return {
            "sha": rand_sha(),
            "message": msg,
            "repo_id": "veins-core",
            "branch": "main",
            "co_authors": [],
            "files_touched": ["src/auth.py"],
        }
    if event_type == "slack_msg":
        return {
            "channel": "team-general",
            "text": msg,
            "reply_to": None,
            "thread_root": None,
            "mentions": [],
            "sentiment": None,
        }
    # Generic fallback for other types
    return {"message": msg} if message else {}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def get_person(person_id: str) -> dict | None:
    url = f"{API_BASE}/person/{person_id}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except urllib.error.URLError as e:
        print(f"{red('❌')} Backend unavailable: {e.reason}")
        print(f"   Is 'docker compose up' running? ({API_BASE})")
        sys.exit(1)
    except TimeoutError:
        print(red("❌ Request timed out (5s). Backend may be overloaded."))
        sys.exit(1)


def post_event(body: dict) -> tuple[int, dict]:
    url = f"{API_BASE}/ingest/event"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"detail": raw}
        return e.code, detail
    except urllib.error.URLError as e:
        print(f"{red('❌')} Backend unavailable: {e.reason}")
        print(f"   Is 'docker compose up' running? ({API_BASE})")
        sys.exit(1)
    except TimeoutError:
        print(red("❌ Request timed out (5s). Backend may be overloaded."))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------
def _score_arrow(old: float, new: float) -> str:
    diff = new - old
    if diff > 0.001:
        return red(f"+{diff:.3f}")
    if diff < -0.001:
        return green(f"{diff:.3f}")
    return dim("±0.000")


def print_response(status_code: int, result: dict, person_id: str, ts_label: str, payload: dict) -> None:
    if status_code == 200:
        old_score = result["old_overload_score"]
        new_score = result["new_overload_score"]
        old_st    = result["old_status"]
        new_st    = result["new_status"]
        event_id  = result["event_id"]
        recomputed = result.get("recomputed_signals", [])

        print(green("✅") + f" {bold(person_id)}  overload  "
              f"{old_score:.2f} → {new_score:.2f}  "
              f"({status_color(old_st, old_st)} → {status_color(new_st, new_st)})")
        print(f"   event_id:   {event_id}")
        print(f"   recomputed: {', '.join(recomputed) or '—'}")
        print(f"   score_diff: {_score_arrow(old_score, new_score)}")
        return

    # Error path
    print(red(f"❌ Error {status_code}"), end="")
    if isinstance(result, dict):
        detail = result.get("detail", result.get("message", ""))
        if status_code == 404:
            print(f": person '{person_id}' not found.")
            print(f"   Available people: {', '.join(KNOWN_PEOPLE)}")
        elif status_code == 422:
            # Pydantic validation error — grab first message
            if isinstance(detail, list) and detail:
                print(f": {detail[0].get('msg', detail[0])}")
            else:
                print(f": {detail}")
            print(f"   Valid types: {', '.join(VALID_TYPES)}")
        else:
            if isinstance(detail, dict):
                print(f": [{detail.get('code','?')}] {detail.get('message', json.dumps(detail))}")
            else:
                print(f": {detail}")
    else:
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push a demo event to Veins backend and print the overload diff."
    )
    parser.add_argument("person_id", help="Person ID (e.g. ivan, maria)")
    parser.add_argument("type", choices=VALID_TYPES, help="Event type")
    parser.add_argument("message", nargs="?", default=None, help="Event message/text")
    parser.add_argument("--night",   action="store_true", help="Use 03:00 UTC timestamp (night commit)")
    parser.add_argument("--weekend", action="store_true", help="Use last Saturday 14:00 UTC timestamp")
    args = parser.parse_args()

    # --- Timestamp ---
    if args.night:
        ts = night_timestamp()
        ts_label = f"{ts} (NIGHT)"
    elif args.weekend:
        ts = weekend_timestamp()
        ts_label = f"{ts} (WEEKEND)"
    else:
        ts = now_timestamp()
        ts_label = ts

    payload = build_payload(args.type, args.message)

    # --- Pre-flight: show current context via GET /person/{id} ---
    print(f"\n{dim('Fetching current state...')}")
    person_data = get_person(args.person_id)
    if person_data:
        name  = person_data.get("name", args.person_id)
        role  = person_data.get("role", "")
        score = person_data.get("overload_score", 0.0)
        st    = ("red" if score > 0.7 else "yellow" if score > 0.4 else "green")
        print(f"{bold(name)} ({role}) — current overload: {score:.2f} {status_color(st, st)}")
    else:
        print(f"{red('⚠')} Could not fetch person data (backend may not have /person/{args.person_id})")

    # --- Show push intent ---
    print(f"\n{bold('🚀 Pushing event to')} {API_BASE}/ingest/event")
    print(f"   person:    {args.person_id}")
    print(f"   type:      {args.type}")
    print(f"   timestamp: {ts_label}")
    print(f"   payload:   {json.dumps(payload, ensure_ascii=False)[:120]}")
    print()

    # --- POST ---
    body = {
        "person_id": args.person_id,
        "type": args.type,
        "timestamp": ts,
        "payload": payload,
    }
    status_code, result = post_event(body)
    print_response(status_code, result, args.person_id, ts_label, payload)
    print()

    sys.exit(0 if status_code == 200 else 1)


if __name__ == "__main__":
    main()
