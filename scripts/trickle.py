#!/usr/bin/env python3
"""Trickle generator — эмулирует поток событий через POST /ingest/event для демо.

Usage:
  python scripts/trickle.py --rate 10 --duration 600
  python scripts/trickle.py --scenario ivan-burns-out
  python scripts/trickle.py --burst 5
  python scripts/trickle.py --dry-run --burst 3
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = os.environ.get("BASE", "http://127.0.0.1:8000")
SCENARIOS_DIR = Path(__file__).parent / "demo_scenarios"

# Реалистичные шаблоны для random mode
RANDOM_TEMPLATES = {
    "ivan": {
        "commit": [
            "fix: revert auth race condition",
            "hotfix: token expiry checked",
            "fix: null pointer in session",
            "revert: broke worse",
            "fix: prod auth crash",
            "hotfix: session cache invalid",
        ],
        "slack_msg": [
            "не успею к утру",
            "опять баг в auth",
            "почему это падает только в проде",
            "разбираюсь со вчерашним",
            "ещё один p1 на auth",
        ],
    },
    "marina": {
        "slack_msg": [
            "@here кто может посмотреть p1?",
            "стэндап в 10",
            "1:1 с CEO в 14, после смогу",
            "напоминаю про OKR review",
            "@team статус по спринту?",
        ],
    },
    "maria": {
        "commit": [
            "feat: add user pagination",
            "refactor: extract validator helper",
            "improve: cleaner error messages",
            "feat: improve API response format",
        ],
        "slack_msg": [
            "👍 отличный код",
            "ревью готово, мерджи",
            "@anna молодец, апруваю",
            "PR approved, ship it",
        ],
    },
    "tom": {
        "commit": [
            "fix: edge case in filter",
            "feat: rate limiting v1",
        ],
        "slack_msg": [
            "@ivan PR-42 ещё актуально?",
            "блокирует TASK-22",
            "@ivan нужно ревью срочно",
        ],
    },
    "anna": {
        "commit": [
            "feat: dashboard widget",
            "fix: button alignment",
            "improve: loading state",
            "feat: mobile responsive layout",
        ],
        "slack_msg": [
            "@maria посмотри дизайн",
            "готово, можно ревью",
            "сделала по макету",
        ],
    },
    "nikita": {
        "commit": [
            "learn: refactored per Anna feedback",
            "fix: my first PR feedback",
            "feat: simple component draft",
        ],
        "slack_msg": [
            "@anna правильно ли я понял?",
            "спасибо за фидбек!",
            "@anna можешь глянуть?",
        ],
    },
    "peter": {
        "commit": [
            "test: add regression for TASK-15",
            "test: coverage for auth module",
        ],
        "slack_msg": [
            "прогон тестов чисто",
            "regression на staging без падений",
            "новый баг в TASK-15, логи приложил",
        ],
    },
}


def push_event(person_id, etype, message, night=False, weekend=False, dry_run=False):
    """POST /ingest/event с pretty output."""
    now = datetime.now(timezone.utc)
    if night:
        ts = now.replace(hour=3, minute=random.randint(0, 59), second=0, microsecond=0)
        if now < ts:
            ts -= timedelta(days=1)
    elif weekend:
        days_back = (now.weekday() - 5) % 7 or 7
        ts = (now - timedelta(days=days_back)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
    else:
        ts = now

    payload = {}
    if etype == "commit":
        payload = {
            "sha": f"{random.randint(0, 0xFFFFFFF):07x}",
            "message": message,
            "repo_id": "veins-core",
            "branch": "main",
            "co_authors": [],
            "files_touched": ["src/auth.py" if person_id == "ivan" else "src/api.py"],
        }
    elif etype == "slack_msg":
        payload = {
            "channel": "team-general",
            "text": message,
            "reply_to": None,
            "thread_root": None,
            "mentions": [],
            "sentiment": None,
        }

    body = {
        "person_id": person_id,
        "type": etype,
        "timestamp": ts.isoformat(),
        "payload": payload,
    }

    prefix = datetime.now().strftime("%H:%M:%S")
    short = message[:50] + ("..." if len(message) > 50 else "")
    print(f"[{prefix}] 🚀 {person_id:8s} {etype:12s} {short}", flush=True)

    if dry_run:
        print(f"[{prefix}]    (dry-run, not pushing)", flush=True)
        return None

    try:
        req = Request(
            f"{BASE}/ingest/event",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            diff = result["new_overload_score"] - result["old_overload_score"]
            sign = "+" if diff >= 0 else ""
            print(
                f"[{prefix}] ✅ {person_id:8s} "
                f"{result['old_overload_score']:.2f} → {result['new_overload_score']:.2f}  "
                f"({result['old_status'].upper()} → {result['new_status'].upper()})  "
                f"diff {sign}{diff:.2f}",
                flush=True,
            )
            return result
    except (HTTPError, URLError) as e:
        print(f"[{prefix}] ❌ {person_id:8s} backend error: {e}", flush=True)
        return None


def random_event():
    """Pick weighted random person + event type from RANDOM_TEMPLATES."""
    weights = {
        "ivan": 4, "marina": 2, "maria": 3, "tom": 2,
        "anna": 2, "nikita": 1, "peter": 1,
    }
    person_id = random.choices(list(weights), weights=list(weights.values()))[0]
    templates = RANDOM_TEMPLATES.get(person_id, {})
    if not templates:
        return None
    etype = random.choice(list(templates))
    message = random.choice(templates[etype])
    night = person_id == "ivan" and etype == "commit" and random.random() < 0.7
    return person_id, etype, message, night


def run_scenario(scenario_path, dry_run=False):
    try:
        import yaml
    except ImportError:
        print("❌ PyYAML not installed. Run: pip install pyyaml==6.0.2", flush=True)
        sys.exit(1)

    data = yaml.safe_load(scenario_path.read_text())
    print(f"📋 Scenario: {data.get('name', scenario_path.stem)}", flush=True)
    print(f"   Description: {data.get('description', '')}", flush=True)
    print(f"   Events: {len(data['events'])}", flush=True)
    print(flush=True)

    start = time.time()
    for ev in data["events"]:
        target = ev.get("delay_sec", 0)
        wait = max(0, target - (time.time() - start))
        if wait > 0:
            time.sleep(wait)
        push_event(
            person_id=ev["person"],
            etype=ev["type"],
            message=ev.get("message", ""),
            night=ev.get("night", False),
            weekend=ev.get("weekend", False),
            dry_run=dry_run,
        )


def run_random(rate, duration, dry_run=False):
    deadline = time.time() + duration
    count = 0
    try:
        while time.time() < deadline:
            ev = random_event()
            if ev:
                push_event(*ev, dry_run=dry_run)
                count += 1
            time.sleep(rate)
    except KeyboardInterrupt:
        pass
    print(f"\n✅ Done. Pushed {count} events over {duration}s.", flush=True)


def run_burst(n, dry_run=False):
    """N events over 30 sec for demo dramatic moment."""
    interval = 30.0 / max(1, n)
    for i in range(n):
        ev = random_event()
        if ev:
            push_event(*ev, dry_run=dry_run)
        if i < n - 1:
            time.sleep(interval)


def main():
    p = argparse.ArgumentParser(description="Trickle live event generator for Veins demo")
    p.add_argument("--rate", type=int, default=10, help="seconds between events (default 10)")
    p.add_argument("--duration", type=int, default=600, help="total duration in seconds (default 600)")
    p.add_argument("--scenario", type=str, help="run a YAML scenario from demo_scenarios/")
    p.add_argument("--burst", type=int, help="push N events over 30 seconds")
    p.add_argument("--dry-run", action="store_true", help="print events without pushing")
    args = p.parse_args()

    # Mutual exclusion
    if args.scenario and args.burst:
        print("❌ --scenario и --burst нельзя комбинировать", flush=True)
        return 1

    # Health check (skip in dry-run)
    if not args.dry_run:
        try:
            with urlopen(f"{BASE}/health", timeout=3) as r:
                if r.status != 200:
                    print(f"❌ Backend health check failed (HTTP {r.status})", flush=True)
                    return 1
        except Exception as e:
            print(f"❌ Backend unavailable at {BASE}: {e}", flush=True)
            print("   Is 'docker compose up' running?", flush=True)
            return 1

    random.seed()

    if args.scenario:
        name = args.scenario.removesuffix(".yaml").removesuffix(".yml")
        path = SCENARIOS_DIR / f"{name}.yaml"
        if not path.exists():
            print(f"❌ Scenario not found: {path}", flush=True)
            return 1
        run_scenario(path, dry_run=args.dry_run)
    elif args.burst:
        run_burst(args.burst, dry_run=args.dry_run)
    else:
        run_random(args.rate, args.duration, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
