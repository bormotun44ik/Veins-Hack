#!/usr/bin/env bash
# Smoke test — прогон всех основных endpoints и фронта.
# Использование:
#   ./scripts/smoke_test.sh              # smoke против локального native-запуска
#   BASE=http://localhost:8000 FRONT=http://localhost:5173 ./scripts/smoke_test.sh
#
# Exit codes:
#   0 — всё ОК
#   1 — найдены падения (детали в выводе)

set -u

BASE=${BASE:-http://127.0.0.1:8000}
FRONT=${FRONT:-http://localhost:5173}

pass=0
fail=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ $name"
    pass=$((pass+1))
  else
    echo "  ❌ $name"
    echo "     cmd: $cmd"
    fail=$((fail+1))
  fi
}

jqcheck() {
  local name="$1"
  local url="$2"
  local expr="$3"
  local expected="$4"
  local got
  # Без -f, чтобы body на 4xx/5xx тоже распарсился (PERSON_NOT_FOUND, BAD_LAYER и т.п.)
  got=$(curl -s "$url" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print($expr)" 2>/dev/null)
  if [ "$got" = "$expected" ]; then
    echo "  ✅ $name ($expr=$got)"
    pass=$((pass+1))
  else
    echo "  ❌ $name (expected $expected, got $got)"
    fail=$((fail+1))
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Veins smoke test"
echo "Backend: $BASE"
echo "Frontend: $FRONT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "[Backend]"
check "GET /health → 200"              "curl -sf $BASE/health"
jqcheck "/health.status == ok"         "$BASE/health" "d['status']" "ok"

jqcheck "/graph?layer=stress — 5 nodes" "$BASE/graph?layer=stress" "len(d['nodes'])" "5"
jqcheck "/graph?layer=collab — >=4 links" "$BASE/graph?layer=collab" "1 if len(d['links'])>=4 else 0" "1"
jqcheck "/graph?layer=workload — >=15 nodes" "$BASE/graph?layer=workload" "1 if len(d['nodes'])>=15 else 0" "1"

jqcheck "/person/ivan.status (RED)"     "$BASE/person/ivan" "d['status']" "red"
jqcheck "/person/ivan has signals"      "$BASE/person/ivan" "1 if d['signals']['night_commits_ratio']>0 else 0" "1"
jqcheck "/person/notexist → PERSON_NOT_FOUND" "$BASE/person/does-not-exist" "d['error']['code']" "PERSON_NOT_FOUND"
jqcheck "/graph?layer=bad → BAD_LAYER"  "$BASE/graph?layer=bad" "d['error']['code']" "BAD_LAYER"

# Phase 2 endpoints
jqcheck "/dashboard summary structure" "$BASE/dashboard" "1 if 'red_count' in d.get('summary',{}) else 0" "1"
jqcheck "/dashboard attention has Ivan" "$BASE/dashboard" "d['attention'][0]['person_id'] if d.get('attention') else ''" "ivan"
jqcheck "/dashboard primary_reason set" "$BASE/dashboard" "1 if d['attention'] and d['attention'][0]['primary_reason'] else 0" "1"

echo ""
echo "[Frontend]"
check "GET / → 200 HTML"                "curl -sf $FRONT/ -o /dev/null"

echo ""
echo "[LLM (optional — нужен ShadoClaw на 127.0.0.1:8317)]"
if curl -sf http://127.0.0.1:8317/health > /dev/null 2>&1; then
  check "ShadoClaw health"              "curl -sf http://127.0.0.1:8317/health"
  jqcheck "/insights/ivan returns insights" "$BASE/insights/ivan" "1 if len(d.get('insights',[]))==3 else 0" "1"
else
  echo "  ⏭ ShadoClaw не запущен на 127.0.0.1:8317 — /insights пропущен"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Passed: $pass | Failed: $fail"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$fail" -gt 0 ]; then
  exit 1
fi
exit 0
