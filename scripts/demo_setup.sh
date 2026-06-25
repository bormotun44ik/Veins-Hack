#!/usr/bin/env bash
#
# demo_setup.sh — приводит систему в "demo-ready" state ПЕРЕД презентацией.
#
# 1. Backend up (если не поднят)
# 2. Ivan в YELLOW (~0.55) — middle ground для драматичного цикла:
#       демо начинается → push'ишь → Ivan red → recovery → ivan green → ...
# 3. llm_cache прогрет на текущие сигналы (insights мгновенные при кликах)
#
# Usage:  ./scripts/demo_setup.sh

set -e
cd "$(dirname "$0")/.."

BASE="${BASE:-http://127.0.0.1:8000}"

echo "🎬 demo_setup — preparing system for live demo"
echo

# ─── 1. Backend health ────────────────────────────────────────────────
echo "[1/4] Backend health..."
if ! curl -sf "$BASE/health" > /dev/null 2>&1; then
    echo "  Backend not running — starting docker compose..."
    sg docker -c 'docker compose up -d 2>&1' > /dev/null
    until curl -sf "$BASE/health" > /dev/null 2>&1; do sleep 2; done
fi
echo "  ✅ backend up"
echo

# ─── 2. Reset Ivan to YELLOW middle-state ─────────────────────────────
echo "[2/4] Resetting Ivan to YELLOW (~0.55)..."
sg docker -c 'docker exec veins-backend python -c "
import json, sqlite3, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, \"/app\")

c = sqlite3.connect(\"/app/db/veins.db\")
now = datetime.now(timezone.utc)

# Delete recent ivan commits (last 14d)
c.execute(\"DELETE FROM events WHERE person_id=? AND type=? AND timestamp > datetime(?, ?)\",
          (\"ivan\", \"commit\", \"now\", \"-14 days\"))
c.commit()

# Seed: 5 day-feat + 2 night-fix → mid-load state
events = [
    (now - timedelta(days=6, hours=10), \"feat: user pagination\"),
    (now - timedelta(days=5, hours=11), \"improve: error messages\"),
    (now - timedelta(days=4, hours=14), \"feat: rate limiting v1\"),
    (now - timedelta(days=3, hours=15), \"refactor: extract validator\"),
    (now - timedelta(days=2, hours=11), \"feat: caching layer\"),
    (now - timedelta(days=1, hours=2), \"fix: auth race condition\"),
    (now - timedelta(hours=20), \"hotfix: token expiry\"),
]

for ts, msg in events:
    payload = {
        \"sha\": f\"sha{abs(hash(msg))%10000000:07x}\",
        \"message\": msg,
        \"repo_id\": \"veins-core\",
        \"branch\": \"main\",
        \"co_authors\": [],
        \"files_touched\": [\"src/auth.py\"],
    }
    c.execute(
        \"INSERT INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)\",
        (\"ivan\", \"commit\", ts.isoformat(), json.dumps(payload)),
    )
c.commit()

from app.signals import composite
score = composite.compute_overload(\"ivan\", c)
c.execute(\"UPDATE people SET overload_score=? WHERE id=?\", (score, \"ivan\"))
c.commit()

# Clear cached insights for ivan (старые stale)
c.execute(\"DELETE FROM signal_snapshots WHERE person_id=?\", (\"ivan\",))
c.commit()

print(f\"  ivan overload: {score:.3f}\")
"' 2>&1 | tail -2
echo

# ─── 3. Recompute everyone (быстро, no LLM) ───────────────────────────
echo "[3/4] Recomputing all overloads..."
sg docker -c 'docker exec veins-backend python -c "
import sqlite3, sys
sys.path.insert(0, \"/app\")
c = sqlite3.connect(\"/app/db/veins.db\")
from app.signals.composite import update_all_people
update_all_people(c)
print(\"  ✅ all people recomputed\")
"' 2>&1 | tail -1
echo

# ─── 4. Prewarm cache ─────────────────────────────────────────────────
echo "[4/4] Prewarming LLM cache (5 insights + 5 recognition)..."
echo "  this takes ~1.5 min via Anthropic..."
.venv/bin/python scripts/prewarm_cache.py 2>&1 | grep -E "✅|❌" | tail -12

# ─── Summary ──────────────────────────────────────────────────────────
echo
echo "═══════════════════════════════════════════════"
echo "🎬  DEMO READY"
echo "═══════════════════════════════════════════════"
sg docker -c 'docker exec veins-backend python -c "
import sqlite3
c = sqlite3.connect(\"/app/db/veins.db\")
for r in c.execute(\"SELECT id, role, overload_score FROM people ORDER BY overload_score DESC\").fetchall():
    pid, role, sc = r
    status = \"🔴 RED   \" if sc > 0.7 else \"🟡 YELLOW\" if sc > 0.4 else \"🟢 GREEN \"
    print(f\"  {status}  {pid:8s}  {role:32s}  {sc:.2f}\")
"'
echo
echo "Open browser:  http://localhost:5173"
echo
echo "Run demo cycle in another terminal:"
echo "  .venv/bin/python scripts/demo_cycle.py --rate 8"
echo
echo "Or manual single push:"
echo "  .venv/bin/python scripts/push_event.py ivan commit 'fix: prod fire' --night"
echo
