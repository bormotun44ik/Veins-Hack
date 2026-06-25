#!/usr/bin/env python3
"""
demo_cycle.py — endless burnout/recovery cycle для живой демо.

Логика:
  Ivan начинает в YELLOW/lower-RED. Скрипт детектит его текущий status и
  гонит подходящие события:

    if ivan in RED   → recovery events (Maria pairs in, Tom unblocks, Ivan day-commit)
    if ivan in YELLOW→ либо stress либо recovery (50/50, drift по weight'ам)
    if ivan in GREEN → stress events (night commits, slack frustration)

  Параллельно — фоновый шум от других людей (Maria/Tom/Anna/Nikita/Peter)
  чтобы граф выглядел живым.

Recovery механика (понижающие сигналы):
  • Day-commit feat — снижает night_commits_ratio
  • Co-authored commit (Maria + Ivan) — снижает co_author_isolation
  • Review event Ivan'а на чужой PR — снижает isolation
  • Любой не-fix commit — снижает fix_revert_ratio

Usage:
  python scripts/demo_cycle.py                  # default 8s rate, infinite
  python scripts/demo_cycle.py --rate 5         # быстрее (5 сек интервал)
  python scripts/demo_cycle.py --duration 600   # ограничить 10 минут
  python scripts/demo_cycle.py --reset          # сбросить ivan в clean baseline
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("BASE", "http://127.0.0.1:8000")

# ─── Ivan stress events (push him toward RED) ─────────────────────────
STRESS_EVENTS = [
    {"type": "commit", "msg": "fix: revert auth race condition", "night": True},
    {"type": "commit", "msg": "hotfix: token expiry not checked", "night": True},
    {"type": "commit", "msg": "fix: null pointer in session", "night": True},
    {"type": "commit", "msg": "revert: rolled back, broke worse", "night": True},
    {"type": "commit", "msg": "fix: race condition in cache", "night": True},
    {"type": "slack_msg", "msg": "опять баг в auth, разбираюсь", "night": True},
    {"type": "slack_msg", "msg": "не успею к утру, всё ломается", "night": True},
    {"type": "slack_msg", "msg": "почему это падает только в проде", "night": True},
]

# ─── Ivan recovery events (push him toward GREEN) ─────────────────────
# Logic: day-time commits, with co-authors, feature-style messages.
# Each one diluites night_commits_ratio + fix_revert_ratio + co_author_isolation.
RECOVERY_EVENTS = [
    {"type": "commit", "msg": "feat: pagination after Maria refactor", "night": False, "co_authors": ["maria"]},
    {"type": "commit", "msg": "improve: cleaner error messages", "night": False, "co_authors": ["maria"]},
    {"type": "commit", "msg": "refactor: extract auth helper with Tom", "night": False, "co_authors": ["tom"]},
    {"type": "commit", "msg": "feat: rate limiting (paired with Anna)", "night": False, "co_authors": ["anna"]},
    {"type": "commit", "msg": "docs: auth module overview after pairing", "night": False, "co_authors": ["maria"]},
    {"type": "slack_msg", "msg": "спасибо команде, разобрались с auth", "night": False},
    {"type": "slack_msg", "msg": "сегодня нормальный день, чиню без revert'ов", "night": False},
]

# ─── Manager/peer recovery actions (helping Ivan) ─────────────────────
HELP_EVENTS = [
    # Marina (manager) приходит на помощь
    ("marina", "slack_msg", "@ivan переназначаю TASK-22 на Tom, освободи руки", False),
    ("marina", "slack_msg", "@ivan давай 1:1 завтра обсудим нагрузку", False),
    ("marina", "slack_msg", "@here я reassigned 2 critical tasks с Ivan на Tom и Maria", False),
    # Maria (Tech Lead) пары в auth-модуль (снижает Ivan's bus factor)
    ("maria", "commit", "feat: pairing with Ivan on session lifecycle", False, ["ivan"]),
    ("maria", "commit", "refactor: shared ownership of auth module with Ivan", False, ["ivan"]),
    ("maria", "slack_msg", "@ivan я подхвачу review на твоём PR-42 сейчас", False),
    # Tom unblocks
    ("tom", "commit", "fix: paired with Ivan, unblocked PR-42", False, ["ivan"]),
    ("tom", "slack_msg", "@ivan спасибо за knowledge sharing по auth", False),
    # Recognition — sometimes recovery looks like recognition
    ("maria", "slack_msg", "@ivan отличная работа на стабилизации prod в выходные 🙏", False),
]

# ─── Background noise (other team members healthy daily activity) ─────
NOISE_EVENTS = [
    ("anna", "commit", "feat: dashboard widget", False),
    ("anna", "commit", "fix: button alignment", False),
    ("anna", "slack_msg", "ревью готово, можно мерджить", False),
    ("nikita", "commit", "learn: refactored after Anna feedback", False),
    ("nikita", "slack_msg", "@anna а правильно ли я понял что...?", False),
    ("peter", "commit", "test: regression suite for auth", False),
    ("peter", "slack_msg", "прогон тестов чисто, релиз можно", False),
    ("tom", "commit", "feat: filter v2", False),
    ("maria", "slack_msg", "👍 отличный код, апруваю", False),
    ("marina", "slack_msg", "напоминаю про OKR review в пятницу", False),
]


# ─── HTTP helpers ─────────────────────────────────────────────────────


def http_get_status(person_id: str) -> tuple[float, str] | None:
    try:
        with urlopen(f"{BASE}/person/{person_id}", timeout=5) as r:
            d = json.loads(r.read())
            return d.get("overload_score", 0.0), d.get("status", "green")
    except Exception as e:
        print(f"❌ failed to get {person_id}: {e}", flush=True)
        return None


def push_event(person_id: str, etype: str, message: str, night: bool = False,
                co_authors: list[str] | None = None) -> tuple[float, float, str, str] | None:
    """Returns (old_score, new_score, old_status, new_status) or None on failure."""
    now = datetime.now(timezone.utc)

    if night:
        target_hour = random.choice([1, 2, 3])
        target_min = random.randint(0, 59)
        ts = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
        if now < ts:
            ts -= timedelta(days=1)
    else:
        # Random work-hour
        target_hour = random.choice([10, 11, 14, 15, 16])
        ts = now.replace(hour=target_hour, minute=random.randint(0, 59), second=0, microsecond=0)
        if ts > now:
            ts -= timedelta(days=1)

    if etype == "commit":
        payload = {
            "sha": f"{random.randint(0, 0xFFFFFFF):07x}",
            "message": message,
            "repo_id": "veins-core",
            "branch": "main",
            "co_authors": co_authors or [],
            "files_touched": ["src/auth.py" if "auth" in message.lower() else "src/api.py"],
        }
    elif etype == "slack_msg":
        payload = {
            "channel": "team-general",
            "text": message,
            "reply_to": None,
            "thread_root": None,
            "mentions": [m.strip("@") for m in message.split() if m.startswith("@")],
            "sentiment": None,
        }
    else:
        payload = {}

    body = {
        "person_id": person_id,
        "type": etype,
        "timestamp": ts.isoformat(),
        "payload": payload,
    }

    try:
        req = Request(
            f"{BASE}/ingest/event",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return (
                d["old_overload_score"],
                d["new_overload_score"],
                d["old_status"],
                d["new_status"],
            )
    except (HTTPError, URLError) as e:
        print(f"❌ push failed: {e}", flush=True)
        return None


# ─── Phase logic ──────────────────────────────────────────────────────


def pick_event_for_phase(ivan_status: str, ivan_score: float) -> tuple[str, str, str, bool, list[str]]:
    """Returns (person_id, etype, msg, night, co_authors).

    Probability matrix (ivan_status → event class):
        red    → recovery 60% / help 35% / noise 5%
        yellow → mix 35% stress / 35% recovery / 25% help / 5% noise
        green  → stress 60% / noise 30% / recovery 10%
    """
    r = random.random()

    if ivan_status == "red":
        # Recovery dominant — show "manager interventions working"
        if r < 0.6:
            ev = random.choice(RECOVERY_EVENTS)
            return ("ivan", ev["type"], ev["msg"], ev.get("night", False), ev.get("co_authors", []))
        elif r < 0.95:
            return _pick_help()
        else:
            return _pick_noise()

    if ivan_status == "yellow":
        # Drift — usually push toward extreme to keep dynamics
        # If score > 0.55 → bias toward recovery; if < 0.55 → bias toward stress
        bias_recovery = ivan_score > 0.55
        if bias_recovery:
            if r < 0.5:
                ev = random.choice(RECOVERY_EVENTS)
                return ("ivan", ev["type"], ev["msg"], ev.get("night", False), ev.get("co_authors", []))
            elif r < 0.75:
                return _pick_help()
            elif r < 0.95:
                ev = random.choice(STRESS_EVENTS)
                return ("ivan", ev["type"], ev["msg"], ev.get("night", False), [])
            else:
                return _pick_noise()
        else:
            if r < 0.55:
                ev = random.choice(STRESS_EVENTS)
                return ("ivan", ev["type"], ev["msg"], ev.get("night", False), [])
            elif r < 0.85:
                ev = random.choice(RECOVERY_EVENTS)
                return ("ivan", ev["type"], ev["msg"], ev.get("night", False), ev.get("co_authors", []))
            elif r < 0.95:
                return _pick_help()
            else:
                return _pick_noise()

    # green
    if r < 0.6:
        ev = random.choice(STRESS_EVENTS)
        return ("ivan", ev["type"], ev["msg"], ev.get("night", False), [])
    elif r < 0.9:
        return _pick_noise()
    else:
        ev = random.choice(RECOVERY_EVENTS)
        return ("ivan", ev["type"], ev["msg"], ev.get("night", False), ev.get("co_authors", []))


def _pick_help() -> tuple[str, str, str, bool, list[str]]:
    raw = random.choice(HELP_EVENTS)
    if len(raw) == 5:
        person, etype, msg, night, co = raw
    else:
        person, etype, msg, night = raw
        co = []
    return (person, etype, msg, night, co)


def _pick_noise() -> tuple[str, str, str, bool, list[str]]:
    raw = random.choice(NOISE_EVENTS)
    person, etype, msg, night = raw[:4]
    return (person, etype, msg, night, [])


# ─── Main loop ────────────────────────────────────────────────────────


def status_emoji(status: str) -> str:
    return {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(status, "⚪")


def fmt_diff(old: float, new: float) -> str:
    diff = new - old
    sign = "+" if diff >= 0 else ""
    color = "\033[31m" if diff > 0.005 else "\033[32m" if diff < -0.005 else "\033[90m"
    reset = "\033[0m"
    return f"{color}{sign}{diff:+.3f}{reset}"


def reset_ivan_baseline() -> None:
    """Сбросить Ivan'а в YELLOW (~0.55) — драматичная starting point для демо."""
    print("🔄 Resetting Ivan baseline to YELLOW (~0.55)...", flush=True)
    # Покажем начальный state и ничего не пушим — пусть скрипт сам наберёт через push
    info = http_get_status("ivan")
    if info:
        score, status = info
        print(f"   Current: {status_emoji(status)} {score:.2f} {status.upper()}", flush=True)


def health_check() -> bool:
    try:
        with urlopen(f"{BASE}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="Endless burnout/recovery demo cycle")
    p.add_argument("--rate", type=int, default=4, help="seconds between events (default 8)")
    p.add_argument("--duration", type=int, default=0, help="stop after N seconds (0 = infinite)")
    p.add_argument("--reset", action="store_true", help="just print current Ivan state and exit")
    p.add_argument("--quiet", action="store_true", help="less verbose")
    args = p.parse_args()

    if not health_check():
        print(f"❌ Backend unavailable at {BASE}. Is docker compose up?", flush=True)
        return 1

    if args.reset:
        reset_ivan_baseline()
        return 0

    random.seed()
    print(f"🎬 Demo cycle started — {args.rate}s interval, "
          f"{'infinite' if args.duration == 0 else f'{args.duration}s duration'}", flush=True)
    print(f"   Ctrl+C to stop\n", flush=True)

    start = time.time()
    pushed = 0

    try:
        while True:
            if args.duration and time.time() - start > args.duration:
                break

            # Snapshot Ivan
            info = http_get_status("ivan")
            if not info:
                time.sleep(args.rate)
                continue
            score, status = info

            person, etype, msg, night, co = pick_event_for_phase(status, score)

            ts_str = datetime.now().strftime("%H:%M:%S")
            night_marker = "🌙" if night else "  "
            short_msg = msg[:42] + ("…" if len(msg) > 42 else "")
            print(f"[{ts_str}] {night_marker} {person:7s} {etype:10s} {short_msg}", flush=True)

            result = push_event(person, etype, msg, night=night, co_authors=co)
            if result:
                old_s, new_s, old_st, new_st = result
                if person == "ivan":
                    arrow = f"{status_emoji(old_st)} {old_s:.2f} → {status_emoji(new_st)} {new_s:.2f}"
                    print(f"           {arrow}  ({fmt_diff(old_s, new_s)})", flush=True)
                pushed += 1

            time.sleep(args.rate)
    except KeyboardInterrupt:
        print(f"\n⏹  Stopped. Pushed {pushed} events over {int(time.time() - start)}s.", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {e}", flush=True)
        return 1

    print(f"\n✅ Done. Pushed {pushed} events.", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
