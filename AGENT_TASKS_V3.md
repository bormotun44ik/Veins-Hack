# Veins — Agent Tasks (Phase 3)

> 5 промптов для третьей волны субагентов. Лилит копирует prompt целиком → запускает агента.
> Все 5 могут стартовать **одновременно** — зависимости развязаны через готовый main + sample fixtures.

**Контекст:** Phase 1 (A-F) и Phase 2 (H-K) завершены и смержены. Live ingest работает,
Dashboard работает, Ivan = RED через ShadoClaw + Opus 4.7. Цель Phase 3:

1. **L** — расширенный mock dataset (7 людей + 3 месяца истории + новые роли Manager/Junior)
2. **M** — Trickle generator (фоновый поток событий 1/10 сек на демо)
3. **N** — Trend & peer-aware insights (Opus получает "3 мес назад vs сейчас" + peer comparison)
4. **O** — Fallback templates когда Anthropic 5xx + Smart cache (partial invalidation)
5. **P** — Embeddings + RAG pipeline (Qwen3-Embedding-8B через OpenRouter)

---

## Общая преамбула (вставлять в КАЖДЫЙ prompt первой секцией)

```
Ты субагент проекта Veins-Hack — Phase 3.
Работаешь в git worktree, пушишь только в свою ветку.

Репо: https://github.com/bormotun44ik/Veins-Hack
Worktree path: /home/bormotun/Code/veins-agent-<X>  (или твой эквивалент на сервере Лилит)
Твоя ветка: agent/<X>-<name>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRE-FLIGHT (делай В ЭТОМ ПОРЯДКЕ, до любого кода)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. cd <repo>/Veins-Hack && git pull origin main
2. git worktree add ../veins-agent-<X> -b agent/<X>-<name>
3. cd ../veins-agent-<X>
4. cp ../Veins-Hack/.env ./.env
5. Прочитай целиком:
     ARCHITECTURE.md       — структура, твоя зона ответственности
     CONTRACTS.md          — секции Phase 3 (Team roster, Trend dataset,
                              Trickle, Trend & peer insights, Fallback, Smart cache, Embeddings)
     KARPATHY.md           — как работать (ОБЯЗАТЕЛЬНО)
     AGENT_TASKS_V3.md     — этот файл, твой промпт
     PLAN.md               — общий контекст (readonly)
     MORNING_REPORT.md     — что было пофикшено этой ночью

Применяй KARPATHY.md:
  • не молчи в блокере >15 мин
  • пиши МИНИМУМ кода
  • не выходи из своей зоны
  • не меняй CONTRACTS.md (orchestrator уже расширил его под Phase 3)
  • отчитайся по шаблону DONE/BLOCKED/CHANGED/NEXT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ФАКТЫ ОБ ИНФРАСТРУКТУРЕ (актуально на старт Phase 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• main стабилен, smoke 12/12, /insights/ivan возвращает живой Claude Opus 4.7.
• Phase 1 закрыла: ingest, signals, graph, llm, frontend.
• Phase 2 закрыла: Dashboard view (GET /dashboard), Live ingest (POST /ingest/event),
  push_event CLI, GraphPage с polling 5s.
• docker compose up ставит 3 сервиса: shadoclaw (8317), backend (8000), frontend (5173).
• 5 людей: ivan/maria/tom/anna/peter (overload 0.78/0.34/0.37/0.26/0.20).
• ShadoClaw: 127.0.0.1:8317 (docker: shadoclaw:8317), Anthropic-compatible.
• OpenRouter: ключ в .env (OPENROUTER_API_KEY), модель qwen/qwen3-embedding-8b.
• tone_delta cached в people.metadata_json (поле "tone_delta_cached").
• llm_cache прогрет на 5 insights + 5 recognition.

ВАЖНО ПО АРХИТЕКТУРЕ:
  • backend FastAPI app в backend/app/main.py — там include_router для всех routers.
    Если делаешь новый endpoint — создаёшь свой APIRouter и регистрируешь в main.py через
    try/except ImportError (как уже сделано для llm.api, graph.api, dashboard.api, ingest.api).
  • Anthropic SDK: anthropic.AsyncAnthropic(api_key=os.environ.get("SHADOCLAW_API_KEY","sk-dummy"),
    base_url=os.environ.get("SHADOCLAW_BASE_URL","http://shadoclaw:8317"))
    base_url БЕЗ /v1.
  • SQLite: singleton _conn в db.py с check_same_thread=False. Не открывай свои connections.
  • После твоего merge в main: orchestrator делает rebuild контейнеров.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
СТАНДАРТЫ КОДА (как в Phase 1+2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PYTHON:
  • Type hints, parameterized SQL queries, pydantic-settings,
  • async/await для I/O (FastAPI, anthropic, httpx),
  • try/except на внешние вызовы (LLM, OpenRouter) с graceful fallback,
  • logging вместо print,
  • conditional imports через try/except ImportError для межагентных зависимостей,
  • НЕ дёргай LLM в hot path без cache_key.

GIT:
  • Коммиты каждые 30-45 мин, message "<agent-letter>: <short>".
  • Push в свою ветку, НИКОГДА в main. Orchestrator мержит через PR.
```

---

## 🅻 AGENT L — Mock data expansion + Trend dataset

### Branch & worktree
```
branch: agent/l-mock-expansion
worktree: ../veins-agent-l
```

### Prompt (copy-paste целиком)

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent L — Mock data + Trend dataset
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ (пишешь ТОЛЬКО в эти файлы):
  data/fake_team_v2.json                     ← 7 людей вместо 5
  data/mock_slack_v2.json                    ← расширенный slack
  data/mock_jira_v2.json                     ← с history переназначений
  data/mock_calendar_v2.json                 ← back-to-back stats
  data/mock_code_coupling.json               ← Ivan owns auth.py + session.py
  data/transcripts/meeting_2026_w14.json     ← последний митинг (current)
  data/transcripts/meeting_2026_w08.json     ← 6 недель назад (mid)
  data/transcripts/meeting_2026_w02.json     ← 12 недель назад (baseline)
  data/historical_signals.json               ← weekly summary 12 недель × 7 людей
  data/samples/sample_events_v2.jsonl        ← 200 events (28/person × 7 people)
  data/samples/sample_historical_signals.json ← пример формата для других агентов
  scripts/seed_demo_v2.py                    ← новая версия, использует _v2 файлы

И обновишь:
  scripts/seed_demo.py — пометить deprecated, переадресовать на seed_demo_v2.py

ЗАДАЧА:
  Создать богатый mock-dataset с 7 людьми и 3-месячной историей trend-данных.

КОНТРАКТ — Team roster (см. CONTRACTS §Phase 3 / Team roster):

  ivan    — Senior Backend Engineer    — burnout (firefighter)     — overload 0.78 RED
  marina  — Engineering Manager        — overwhelmed-leader        — overload 0.62 YELLOW
  maria   — Tech Lead                  — healthy-leader            — overload 0.34 GREEN
  tom     — Backend Engineer           — moderate-load             — overload 0.37 GREEN
  anna    — Frontend Engineer          — healthy                   — overload 0.26 GREEN
  nikita  — Junior Frontend Engineer   — learning                  — overload 0.22 GREEN
  peter   — QA Engineer                — healthy                   — overload 0.20 GREEN

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. data/fake_team_v2.json — массив из 7 объектов:
   {
     "id": "ivan",
     "name": "Ivan Petrov",
     "role": "Senior Backend Engineer",
     "github_email": "ivan.petrov@veins.dev",
     "avatar_url": "https://i.pravatar.cc/150?u=ivan",
     "baseline_sentiment": 0.6,
     "current_sentiment": -0.7,
     "archetype": "burnout-firefighter",
     "tenure_months": 18,
     "manager_id": "marina"  // optional, для team graph
   }
   Marina archetype: "overwhelmed-leader", manager_id: null
   Nikita archetype: "learning", manager_id: "anna"  // junior reports to senior FE

   ВАЖНО: backend/app/ingest/github.py содержит EMAIL_TO_ID маппинг.
   Чтобы live GitHub нашёл новых людей (marina, nikita) — обнови маппинг ТАМ ЖЕ
   (нарушение зоны допустимо для этой 1 правки, явно укажи в CHANGED отчёте):
       EMAIL_TO_ID = {
           "ivan.petrov@veins.dev":    "ivan",
           "marina.sokolova@veins.dev": "marina",  # NEW
           "maria.ivanova@veins.dev":  "maria",
           "tom.nielsen@veins.dev":    "tom",
           "anna.kowalska@veins.dev":  "anna",
           "nikita.volkov@veins.dev":  "nikita",   # NEW
           "peter.dimitrov@veins.dev": "peter",
       }

2. data/mock_slack_v2.json — ~150 сообщений, паттерны:
   • Ivan: 30+ сообщений, поздние (22:00+), фрустрированный тон, замолкания 3-4 дня
     Примеры:
       - "опять прод упал" (23:47)
       - "не успею к утру"
       - "я устал" (после 3 дней молчания)
       - "[silent for 4 days]"
   • Marina: 25+, дневные, координация, иногда стресс ("@here кто может посмотреть p1?")
   • Maria: 30+, активная днём, позитивная: "отличный код", "👍"
   • Tom: 20+, blocked на Ivan: "@ivan PR-42 застрял", "ждём ревью"
   • Anna: 15+, дневные, спрашивает Maria для guidance
   • Nikita: 10+, учится, задаёт вопросы Anna
   • Peter: 10+, тихий, технические репорты

3. data/mock_jira_v2.json — ~25 задач + history:
   {
     "id": "TASK-15",
     "title": "Fix prod auth race condition",
     "priority": "critical",
     "status": "in_progress",
     "assignee_id": "ivan",
     "deadline": "2026-04-22T18:00:00Z",
     "created_at": "2026-04-19T10:00:00Z",
     "overdue": true,
     "story_points": 8,
     "assignee_history": [
       {"from": "tom", "to": "ivan", "at": "2026-04-20T14:00:00Z",
        "reason": "tom blocked, ivan owns auth"}
     ],
     "blocks": ["TASK-22", "TASK-23"]  // что блокирует
   }
   Распределение:
   • Ivan: 4 critical (3 overdue), 2 in_progress, 1 в blocks других
   • Marina: 3 (high priority, координация)
   • Maria: 5 (mix priority)
   • Tom: 4 (2 blocked by Ivan)
   • Anna: 4
   • Nikita: 2 (low priority, learning tasks)
   • Peter: 3

4. data/mock_calendar_v2.json — ~30 митингов с реалистичными паттернами:
   • Ivan: 6 митингов вт+чт, 4 of them back-to-back (back_to_back: true)
   • Marina: 8 митингов в день (manager pattern), фокус-time только утром
   • Maria: 3 в день, равномерно
   • Anna: 2 в день, в основном с designer (mock'аем)
   • Nikita: 1 в день, weekly 1:1 с Anna
   • Tom: 2-3 в день
   • Peter: 1-2 в день

5. data/mock_code_coupling.json — bus factor data:
   {
     "files_owned": {
       "ivan": ["src/auth.py", "src/session.py", "src/token.py", "src/permissions.py"],
       "maria": ["src/api/users.py", "src/db/migrations.py"],
       "tom": ["src/validators.py"],
       ...
     },
     "incidents_last_30d": [
       {"date": "2026-04-22", "module": "auth", "responder": "ivan", "duration_h": 4.5},
       {"date": "2026-04-18", "module": "auth", "responder": "ivan", "duration_h": 2.0},
       ...
     ]
   }

6. data/transcripts/meeting_2026_w14.json (current week):
   Standup 15 min, 6 человек (ivan молчит почти весь митинг — 34 слова из 1102),
   Marina с трудом ведёт, Maria помогает.
   Использовать формат из data/transcript.json (existing) — те же поля segments, utterances.

   data/transcripts/meeting_2026_w08.json (6 недель назад):
   Тот же team но Ivan активный — задаёт вопросы, говорит много (talk_ratio 0.18).
   Marina нет (была в отпуске). Maria и Ivan координируют.

   data/transcripts/meeting_2026_w02.json (12 недель назад, baseline):
   Healthy команда, Ivan позитивный, Marina ещё не выгорает.
   Ivan talk_ratio 0.22, sentiment +0.5.

7. data/historical_signals.json (см. CONTRACTS §Trend dataset):
   Per person, 12 weekly summaries, narrative_baseline + narrative_current.

   Для Ivan: тренд от 0.10 night → 0.95, tone от +0.6 → -0.7, co-authors 4 → 0.
   Для Marina: тренд от 0.30 → 0.58 overload, manager-overwhelm.
   Для Maria/Tom/Anna/Nikita/Peter: стабильно низкие сигналы.

8. data/samples/sample_events_v2.jsonl — 200 events (28/person):
   Реалистичные timestamps за последние 14 дней.
   Ivan: 60% night (22:00-04:00), 80% сообщения с fix/revert/hotfix.
   Marina: meetings + slack, мало commits.
   Maria: feat/refactor commits, code reviews для других.
   Tom: blocked-by-Ivan PR + 5 коммитов.
   Anna: дневные frontend commits + mentor feedback к Nikita.
   Nikita: 12 коммитов, мелкие, с learning notes в commit message.
   Peter: 4 коммитов + meeting_attended events.

9. data/samples/sample_historical_signals.json — копия одного "ivan" блока из historical_signals.json
   (для других агентов как reference).

10. scripts/seed_demo_v2.py:
    • Использует _v2 файлы и historical_signals.json
    • Заполняет таблицу events (200 events за 14 дней)
    • Заполняет таблицу people (7 людей вместо 5)
    • Создаёт новую таблицу IF NOT EXISTS:
        CREATE TABLE IF NOT EXISTS historical_signals (
          person_id TEXT NOT NULL,
          week_start TEXT NOT NULL,
          night_commits REAL,
          fix_revert REAL,
          tone_score REAL,
          co_authors_count INTEGER,
          events_count INTEGER,
          PRIMARY KEY (person_id, week_start)
        );
    • Заполняет historical_signals из data/historical_signals.json
    • Идемпотентен (DELETE + INSERT, как seed_demo)

PYTHON BEST PRACTICES:
  • subprocess не нужен — это pure data preparation script
  • argparse для --fresh, --skip-historical
  • json.load с try/except для defensive чтения файлов
  • print с emoji для read статуса (как в seed_demo.py)
  • --fresh означает: DELETE FROM events, people, historical_signals — полная очистка данных
    (не drop таблиц, не пересоздание схемы — только данные)

ОГРАНИЧЕНИЯ:
  • Не трогай backend/, frontend/, scripts/ кроме seed_demo_v2.py и seed_demo.py (shim).
  • mock-данные должны быть НА АНГЛИЙСКОМ для Slack/Jira (Claude генерит insights на eng).
    Исключение: Ivan slack_msgs могут быть на русском (демо-нарратив "не успею к утру").

SEED_DEMO.PY — SHIM (обязательно):
  После создания seed_demo_v2.py — перепиши seed_demo.py как shim:
  ```python
  # scripts/seed_demo.py
  """DEPRECATED: используется только для backward-compat с docker-compose.
  Реальная логика в seed_demo_v2.py.
  """
  import sys
  from seed_demo_v2 import main as v2_main

  if __name__ == "__main__":
      print("⚠️  seed_demo.py is deprecated, delegating to seed_demo_v2.py")
      sys.exit(v2_main())
  ```
  Это критично — docker-compose вызывает seed_demo.py, без shim при --build запустится
  старый seed (5 людей вместо 7).

EMAIL_TO_ID ПРАВКА — ОТДЕЛЬНЫЙ КОММИТ:
  Изменение в backend/app/ingest/github.py (EMAIL_TO_ID маппинг) — оформить отдельным
  коммитом с сообщением: "l: update EMAIL_TO_ID mapping (add marina, nikita)"
  Это нарушение зоны, изолируй от остального кода — иначе merge будет грязный.

DATA VALIDATION в seed_demo_v2.py:
  После загрузки каждого JSON файла — добавь assertions:
  ```python
  team = json.load(f)
  assert len(team) == 7, f"Expected 7 people, got {len(team)}"

  hist = json.load(f)
  people_ids = {p["id"] for p in team}
  hist_ids = {entry["person_id"] for entry in hist}
  assert hist_ids == people_ids, f"historical_signals missing people: {people_ids - hist_ids}"
  ```
  Без этого Agent N получит пустой context и упадёт молча.

HISTORICAL_SIGNALS — ЯВНАЯ ОЧИСТКА:
  В seed_demo_v2.py перед INSERT в historical_signals — всегда делай:
  ```python
  conn.execute("DELETE FROM historical_signals WHERE 1=1")
  ```
  (даже если --fresh не передан). Таблица могла остаться со старой схемой после Phase 2,
  и INSERT OR REPLACE не поможет если PRIMARY KEY поменялся.

DoD:
  1. python scripts/seed_demo_v2.py --fresh → "Seeded ~200 events, 7 people, 84 historical_signals"
  2. sqlite3 db/veins.db "SELECT COUNT(*) FROM people" → 7
  3. sqlite3 db/veins.db "SELECT COUNT(*) FROM historical_signals" → 84 (12 weeks × 7 people)
  4. cat data/transcripts/*.json | jq . → 3 валидных транскрипта
  5. Ivan overload >= 0.75 после полного seed (проверь composite.compute_overload('ivan'))
  6. Marina overload >= 0.55 после полного seed
  7. python -c "import json; d=json.load(open('data/historical_signals.json')); assert len(d)==7" → OK
  8. python scripts/seed_demo.py --fresh → "⚠️ seed_demo.py is deprecated..." затем выполняет v2

ОТЧЁТ:
  DONE:     ...
  BLOCKED:  ...
  CHANGED:  только указанные файлы + backend/app/ingest/github.py (EMAIL_TO_ID, отдельный коммит)
  NEXT:     передай orchestrator'у — нужен seed на новых данных + rebuild
```

---

## 🅼 AGENT M — Trickle generator (live demo data)

### Branch & worktree
```
branch: agent/m-trickle
worktree: ../veins-agent-m
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent M — Trickle generator
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  scripts/trickle.py                          ← основной скрипт
  scripts/demo_scenarios/                     ← новая папка
  scripts/demo_scenarios/ivan-burns-out.yaml
  scripts/demo_scenarios/maria-promoted.yaml
  scripts/demo_scenarios/tom-saves-day.yaml
  scripts/demo_scenarios/team-recovery.yaml
  scripts/demo_scenarios/random-day.yaml

ЗАДАЧА:
  Скрипт который эмулирует поток событий через POST /ingest/event для демо.
  По умолчанию: 1 событие каждые 10 секунд.
  Сценарии: scripted последовательность событий с задержками.

КОНТРАКТ INPUT:
  python scripts/trickle.py [--rate SEC] [--duration SEC] [--scenario NAME] [--burst N] [--dry-run]

  --rate SEC          интервал между событиями (default 10)
  --duration SEC      сколько работать (default 600 = 10 мин)
  --scenario NAME     запустить готовый YAML вместо random
  --burst N           N событий за 30 сек (для драматичного момента)
  --dry-run           печатать что будет, не пушить

КОНТРАКТ OUTPUT:
  STDOUT: pretty log как push_event.py — caller видит что происходит:
    [00:00:00] 🚀 ivan      commit       fix: prod broke
    [00:00:00] ✅ ivan      0.78 → 0.81  (RED → RED)  diff +0.03
    [00:00:10] 🚀 tom       slack_msg    @ivan нужно ревью
    [00:00:10] ✅ tom       0.37 → 0.38  (GREEN → GREEN)  diff +0.01
    ...

  Exit code: 0 если done, 1 если backend недоступен.

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. scripts/trickle.py:

   import argparse, json, random, time, os, sys
   from datetime import datetime, timezone, timedelta
   from urllib.request import Request, urlopen
   from urllib.error import URLError, HTTPError
   from pathlib import Path

   BASE = os.environ.get("BASE", "http://127.0.0.1:8000")
   ROOT = Path(__file__).parent.parent
   SCENARIOS_DIR = Path(__file__).parent / "demo_scenarios"

   # Реалистичные шаблоны для random mode (без YAML)
   RANDOM_TEMPLATES = {
       "ivan": {
           "commit": [
               "fix: revert auth race condition", "hotfix: token expiry checked",
               "fix: null pointer in session", "revert: broke worse",
           ],
           "slack_msg": [
               "не успею к утру", "опять баг в auth",
               "почему это падает только в проде", "разбираюсь со вчерашним",
           ],
       },
       "marina": {
           "slack_msg": [
               "@here кто может посмотреть p1?", "стэндап в 10",
               "1:1 с CEO в 14, после смогу", "напоминаю про OKR review",
           ],
       },
       "maria": {
           "commit": [
               "feat: add user pagination", "refactor: extract validator helper",
               "improve: cleaner error messages",
           ],
           "slack_msg": [
               "👍 отличный код", "ревью готово, мерджи",
               "@anna молодец, апруваю",
           ],
       },
       "tom": {
           "commit": ["fix: edge case in filter", "feat: rate limiting v1"],
           "slack_msg": ["@ivan PR-42 ещё актуально?", "блокирует TASK-22"],
       },
       "anna": {
           "commit": ["feat: dashboard widget", "fix: button alignment", "improve: loading state"],
           "slack_msg": ["@maria посмотри дизайн", "готово, можно ревью"],
       },
       "nikita": {
           "commit": ["learn: refactored per Anna feedback", "fix: my first PR feedback"],
           "slack_msg": ["@anna правильно ли я понял?", "спасибо за фидбек!"],
       },
       "peter": {
           "commit": ["test: add regression for TASK-15"],
           "slack_msg": ["прогон тестов чисто", "regression на staging без падений"],
       },
   }

   def push_event(person_id, etype, message, night=False, weekend=False, dry_run=False):
       """POST /ingest/event с pretty output."""
       # timestamp
       now = datetime.now(timezone.utc)
       if night:
           ts = now.replace(hour=3, minute=random.randint(0,59), second=0, microsecond=0)
           if now < ts:
               ts -= timedelta(days=1)
       elif weekend:
           # closest Saturday 14:00
           days_back = (now.weekday() - 5) % 7 or 7
           ts = (now - timedelta(days=days_back)).replace(hour=14, minute=0, second=0, microsecond=0)
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
               "reply_to": None, "thread_root": None,
               "mentions": [], "sentiment": None,
           }

       body = {
           "person_id": person_id, "type": etype,
           "timestamp": ts.isoformat(), "payload": payload,
       }

       prefix = datetime.now().strftime("%H:%M:%S")
       short = message[:50] + ("..." if len(message) > 50 else "")
       print(f"[{prefix}] 🚀 {person_id:8s} {etype:12s} {short}")

       if dry_run:
           print(f"[{prefix}]    (dry-run, not pushing)")
           return None

       try:
           req = Request(f"{BASE}/ingest/event",
                         data=json.dumps(body).encode(),
                         headers={"Content-Type": "application/json"},
                         method="POST")
           with urlopen(req, timeout=10) as r:
               result = json.loads(r.read())
               diff = result["new_overload_score"] - result["old_overload_score"]
               sign = "+" if diff >= 0 else ""
               print(f"[{prefix}] ✅ {person_id:8s} "
                     f"{result['old_overload_score']:.2f} → {result['new_overload_score']:.2f}  "
                     f"({result['old_status'].upper()} → {result['new_status'].upper()})  "
                     f"diff {sign}{diff:.2f}")
               return result
       except (HTTPError, URLError) as e:
           print(f"[{prefix}] ❌ {person_id:8s} backend error: {e}")
           return None


   def random_event():
       """Pick weighted random person + event type from RANDOM_TEMPLATES."""
       weights = {
           # Чаще выбираем людей с активными паттернами
           "ivan": 4, "marina": 2, "maria": 3, "tom": 2,
           "anna": 2, "nikita": 1, "peter": 1,
       }
       person_id = random.choices(list(weights), weights=list(weights.values()))[0]
       templates = RANDOM_TEMPLATES.get(person_id, {})
       if not templates:
           return None
       etype = random.choice(list(templates))
       message = random.choice(templates[etype])
       night = (person_id == "ivan" and etype == "commit" and random.random() < 0.7)
       return person_id, etype, message, night


   def run_scenario(scenario_path, dry_run=False):
       import yaml  # PyYAML
       data = yaml.safe_load(scenario_path.read_text())
       print(f"📋 Scenario: {data.get('name', scenario_path.stem)}")
       print(f"   Description: {data.get('description', '')}")
       print(f"   Events: {len(data['events'])}")
       print()

       start = time.time()
       for ev in data["events"]:
           target = ev.get("delay_sec", 0)
           wait = max(0, target - (time.time() - start))
           if wait > 0:
               time.sleep(wait)
           push_event(
               person_id=ev["person"], etype=ev["type"],
               message=ev.get("message", ""),
               night=ev.get("night", False), weekend=ev.get("weekend", False),
               dry_run=dry_run,
           )


   def run_random(rate, duration, dry_run=False):
       deadline = time.time() + duration
       count = 0
       while time.time() < deadline:
           ev = random_event()
           if ev:
               push_event(*ev, dry_run=dry_run)
               count += 1
           # Wait until next tick
           time.sleep(rate)
       print(f"\n✅ Done. Pushed {count} events over {duration}s.")


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
       p = argparse.ArgumentParser()
       p.add_argument("--rate", type=int, default=10)
       p.add_argument("--duration", type=int, default=600)
       p.add_argument("--scenario", type=str)
       p.add_argument("--burst", type=int)
       p.add_argument("--dry-run", action="store_true")
       args = p.parse_args()

       # Health check
       try:
           with urlopen(f"{BASE}/health", timeout=3) as r:
               if r.status != 200:
                   print(f"❌ Backend health check failed (HTTP {r.status})")
                   return 1
       except Exception as e:
           print(f"❌ Backend unavailable at {BASE}: {e}")
           print(f"   Is 'docker compose up' running?")
           return 1

       random.seed()

       if args.scenario:
           path = SCENARIOS_DIR / f"{args.scenario}.yaml"
           if not path.exists():
               print(f"❌ Scenario not found: {path}")
               return 1
           run_scenario(path, dry_run=args.dry_run)
       elif args.burst:
           run_burst(args.burst, dry_run=args.dry_run)
       else:
           run_random(args.rate, args.duration, dry_run=args.dry_run)
       return 0


   if __name__ == "__main__":
       sys.exit(main())

2. scripts/demo_scenarios/ivan-burns-out.yaml:
   name: "Ivan burns out over evening"
   description: "Demonstrates how burnout signals escalate live"
   events:
     - person: ivan
       type: commit
       message: "hotfix: prod auth crash again"
       delay_sec: 0
       night: true
     - person: tom
       type: slack_msg
       message: "@ivan PR-42 нужен срочно, блокер"
       delay_sec: 8
     - person: ivan
       type: slack_msg
       message: "опять баг в auth, разбираюсь"
       delay_sec: 16
       night: true
     - person: ivan
       type: commit
       message: "revert: rolled back, broke worse"
       delay_sec: 24
       night: true
     - person: marina
       type: slack_msg
       message: "@ivan ты ок? давай 1:1 завтра"
       delay_sec: 32
     - person: ivan
       type: slack_msg
       message: "не успею к утру"
       delay_sec: 40
       night: true

3. scripts/demo_scenarios/maria-promoted.yaml:
   Maria получает повышение → её события показывают здоровый growth.
   3-4 события: feat commit, mentor message в Anna, recognition от Marina.

4. scripts/demo_scenarios/tom-saves-day.yaml:
   Tom закрывает Ivan'овый блокер.
   3-4 события: tom commits fix-for-auth, tom slack '@ivan unblocked', maria reaction.

5. scripts/demo_scenarios/team-recovery.yaml:
   Команда восстанавливается: Ivan коммитит дневной refactor, Marina '@ivan well-done',
   Tom unblocks. 5-6 событий, длительность 60 сек.

6. scripts/demo_scenarios/random-day.yaml:
   10-15 событий за 5 минут — обычный день, mix всех людей.

ЗАВИСИМОСТЬ:
  • Для YAML — нужен PyYAML локально (не в backend/requirements.txt!).
    Создай scripts/requirements.txt:
      pyyaml==6.0.2
    Установка: pip install -r scripts/requirements.txt
    Backend контейнер trickle.py не запускает — этот файл только для хостовой машины.
  • Backend должен быть запущен на BASE (по умолчанию http://127.0.0.1:8000).

ОГРАНИЧЕНИЯ:
  • Не трогай backend/, frontend/.
  • Не пиши свой ingest endpoint — используй существующий POST /ingest/event.
  • Не вызывай LLM напрямую.
  • Сценарии — pure YAML, никакой динамической логики (только sequence событий + delays).

ROBUSTNESS ПРАВКИ (обязательно, trickle — единственный CLI на сцене):

1. Graceful Ctrl+C в run_random():
   ```python
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
   ```

2. --scenario и --burst взаимоисключающие:
   ```python
   if args.scenario and args.burst:
       print("❌ --scenario и --burst нельзя комбинировать", flush=True)
       return 1
   ```

3. --scenario strip расширения (защита от дурака):
   ```python
   name = args.scenario.removesuffix(".yaml").removesuffix(".yml")
   path = SCENARIOS_DIR / f"{name}.yaml"
   ```
   Без этого --scenario ivan-burns-out.yaml → ivan-burns-out.yaml.yaml → файл не найден.

4. flush=True на ВСЕХ print() в trickle.py:
   Или в начале main():
   ```python
   sys.stdout.reconfigure(line_buffering=True)
   ```
   Без этого python trickle.py | tee log.txt буферизирует output — на сцене будет казаться
   что скрипт завис.

DoD:
  1. python scripts/trickle.py --dry-run --burst 3 → 3 события напечатаны без push
  2. python scripts/trickle.py --rate 10 --duration 30 → 3 события реально запушены
  3. python scripts/trickle.py --scenario ivan-burns-out → 6 событий за ~40 сек
  4. python scripts/trickle.py --scenario ivan-burns-out.yaml → то же самое (strip суффикса)
  5. python scripts/trickle.py --scenario ivan-burns-out --burst 3 → ❌ ошибка (взаимоисключение)
  6. После запуска scenario: ivan overload вырос (+0.05 минимум)
  7. Все 5 YAML сценариев валидируются: yaml.safe_load() не падает
  8. random-day.yaml — последний event с delay_sec >= 240 (5 минут, не 30 сек)

ОТЧЁТ.
```

---

## 🅽 AGENT N — Trend & peer-aware insights

### Branch & worktree
```
branch: agent/n-trend-insights
worktree: ../veins-agent-n
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent N — Trend & peer-aware insights
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/rag/context_v2.py              ← новый extended context
  backend/app/rag/role_focus.py              ← role → concerns mapping
  backend/app/rag/historical.py              ← читает historical_signals table
  backend/app/llm/prompts_v2.py              ← переписанный INSIGHT_SYSTEM
  backend/app/llm/api.py                     ← патч /insights endpoint
  backend/tests/test_rag/test_context_v2.py  (опционально)

ЗАДАЧА:
  Дать Opus гораздо больше контекста: trend (3 мес назад → сейчас), peer comparison,
  role focus. Insights станут менее generic, более action-oriented.

КОНТРАКТЫ (см. CONTRACTS.md §Phase 3):
  §Trend & peer-aware insights — extended context shape
  §Role focus mapping — table

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. backend/app/rag/historical.py:
   import sqlite3, json
   from typing import Any

   def get_historical_signals(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
       """Возвращает агрегированный snapshot 3-месячной давности.

       Читает таблицу historical_signals (заполняется seed_demo_v2.py из
       data/historical_signals.json).
       """
       row = conn.execute("""
           SELECT night_commits, fix_revert, tone_score,
                  co_authors_count, events_count, week_start
             FROM historical_signals
            WHERE person_id = ?
            ORDER BY week_start ASC
            LIMIT 1
       """, (person_id,)).fetchone()
       if not row:
           return {}
       return {
           "night_commits_ratio": row[0] or 0.0,
           "fix_revert_ratio": row[1] or 0.0,
           "tone_score": row[2] or 0.0,
           "co_authors_avg": row[3] or 0,
           "week_start": row[5],
       }

   def build_trend_narrative(person_id: str, historical: dict, current: dict,
                              name: str, role: str) -> dict:
       """Простой текстовый rendering для Opus prompt."""
       # baseline: что было 3 месяца назад
       night_h = historical.get("night_commits_ratio", 0)
       fix_h = historical.get("fix_revert_ratio", 0)
       tone_h = historical.get("tone_score", 0)
       co_h = historical.get("co_authors_avg", 0)

       # current
       night_c = current.get("night_commits_ratio", 0)
       fix_c = current.get("fix_revert_ratio", 0)

       baseline = (
           f"{name} 3 months ago: "
           f"{int(night_h*100)}% night commits, "
           f"{int(fix_h*100)}% fix-revert, "
           f"{co_h:.1f} co-authors avg, tone {tone_h:+.1f}"
       )
       current_n = (
           f"{name} now: "
           f"{int(night_c*100)}% night commits, "
           f"{int(fix_c*100)}% fix-revert"
       )
       delta = (
           f"Tone {tone_h:+.1f} → ?, "
           f"night {int(night_h*100)}%→{int(night_c*100)}%, "
           f"fix {int(fix_h*100)}%→{int(fix_c*100)}%"
       )
       return {
           "baseline": baseline,
           "current": current_n,
           "delta_summary": delta,
       }


2. backend/app/rag/role_focus.py:
   ROLE_FOCUS = {
       "Senior Backend Engineer": {
           "primary_concerns": [
               "technical debt", "system reliability", "knowledge transfer", "on-call load"
           ],
           "manager_questions": [
               "Is there an active incident driving night work?",
               "Who else can pair on critical modules to reduce bus factor?",
               "Is 1:1 cadence appropriate (weekly vs bi-weekly)?",
               "Are deadlines realistic given current technical state?",
           ],
       },
       "Engineering Manager": {
           "primary_concerns": [
               "team velocity", "context switching", "1:1 quality",
               "stakeholder management", "OKR alignment"
           ],
           "manager_questions": [
               "How many direct reports? Is span of control sustainable?",
               "What % of time is in meetings vs deep work?",
               "Are 1:1 conversations going deeper than status updates?",
               "Who is helping with stakeholder pressure?",
           ],
       },
       "Tech Lead": {
           "primary_concerns": [
               "bandwidth", "mentorship vs IC work", "review load",
               "architectural decisions"
           ],
           "manager_questions": [
               "Is review queue clearing in <24h?",
               "Time split: code vs reviews vs mentorship?",
               "Anyone groomed to take over Tech Lead duties?",
           ],
       },
       "Backend Engineer": {
           "primary_concerns": [
               "technical execution", "code quality", "ownership clarity"
           ],
           "manager_questions": [
               "Are tasks clearly scoped?",
               "Has access to senior review on tough problems?",
               "What's blocking unblocking velocity?",
           ],
       },
       "Frontend Engineer": {
           "primary_concerns": [
               "UX quality", "design alignment", "performance"
           ],
           "manager_questions": [
               "Coordination with design — smooth or friction?",
               "Performance budget enforced?",
           ],
       },
       "Junior Frontend Engineer": {
           "primary_concerns": [
               "growth", "safety net", "feedback loops",
               "imposter syndrome risk", "learning curve"
           ],
           "manager_questions": [
               "Has dedicated mentor checking in weekly?",
               "Tasks in sweet spot — challenging but achievable?",
               "Psychological safety to ask 'dumb' questions?",
           ],
       },
       "QA Engineer": {
           "primary_concerns": [
               "coverage", "regression detection", "release confidence"
           ],
           "manager_questions": [
               "Test coverage trending up?",
               "Time between report and fix?",
               "QA included in design review?",
           ],
       },
   }

   def get_role_focus(role: str) -> dict:
       return ROLE_FOCUS.get(role, ROLE_FOCUS["Backend Engineer"])  # fallback

3. backend/app/rag/context_v2.py:
   import sqlite3, json, logging
   from typing import Any
   logger = logging.getLogger(__name__)

   def build_person_context_v2(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
       """Extended context builder:
         - все поля из старого build_person_context() (импортируем)
         - + historical_signals_3m_ago
         - + trend_narrative
         - + peer_comparison
         - + role_focus
         - + retrieved_chunks (если Agent P готов; иначе пустой массив)
       """
       try:
           from app.rag.context import build_person_context
           ctx = build_person_context(person_id, conn)
       except ImportError:
           ctx = {}

       if not ctx:
           return ctx  # PersonNotFound — caller бросит exception

       try:
           from app.rag.historical import get_historical_signals, build_trend_narrative
           historical = get_historical_signals(person_id, conn)
           ctx["historical_signals_3m_ago"] = historical
           ctx["trend_narrative"] = build_trend_narrative(
               person_id, historical, ctx.get("signals", {}),
               ctx.get("name", ""), ctx.get("role", "")
           )
       except Exception as e:
           logger.error(f"trend build failed: {e}")
           ctx["historical_signals_3m_ago"] = {}
           ctx["trend_narrative"] = {}

       try:
           ctx["peer_comparison"] = _build_peer_comparison(person_id, conn)
       except Exception as e:
           logger.error(f"peer comp failed: {e}")
           ctx["peer_comparison"] = {}

       try:
           from app.rag.role_focus import get_role_focus
           ctx["role_focus"] = get_role_focus(ctx.get("role", ""))
       except Exception as e:
           logger.error(f"role focus failed: {e}")
           ctx["role_focus"] = {}

       try:
           from app.rag.retrieval import get_relevant_chunks
           ctx["retrieved_chunks"] = get_relevant_chunks(person_id, conn, top_k=8)
       except (ImportError, Exception) as e:
           # Agent P может ещё не быть готов
           ctx["retrieved_chunks"] = []

       return ctx

   def _build_peer_comparison(person_id: str, conn) -> dict:
       rows = conn.execute(
           "SELECT id, role, overload_score FROM people"
       ).fetchall()
       overloads = [r[2] for r in rows if r[2] is not None]
       if not overloads:
           return {}

       team_avg = sum(overloads) / len(overloads)
       sorted_o = sorted(rows, key=lambda r: -(r[2] or 0))
       median = sorted_o[len(sorted_o)//2][2] if sorted_o else 0

       me = next((r for r in rows if r[0] == person_id), None)
       if not me:
           return {}

       my_overload = me[2] or 0
       rank = next((i+1 for i, r in enumerate(sorted_o) if r[0] == person_id), len(sorted_o))

       # best peer = nижний overload в той же роли (или вообще если same-role нет)
       same_role = [r for r in rows if r[1] == me[1] and r[0] != person_id]
       candidates = same_role or [r for r in rows if r[0] != person_id]
       best = min(candidates, key=lambda r: r[2] or 1.0) if candidates else None

       result = {
           "team_avg_overload": round(team_avg, 2),
           "team_median_overload": round(median, 2),
           "person_overload": round(my_overload, 2),
           "rank_in_team": rank,
       }
       if best:
           result["best_peer"] = {
               "id": best[0], "role": best[1],
               "overload": round(best[2] or 0, 2),
           }
       return result

4. backend/app/llm/prompts_v2.py:
   INSIGHT_SYSTEM_V2 = """You are a senior engineering manager with deep empathy
and 15 years of experience. You analyze team member health signals to provide
actionable, role-specific insights.

You have access to:
- Current behavioral signals (last 14 days)
- Historical signals (3 months ago, baseline)
- Peer comparison within the team
- Role-specific concerns and manager questions

Always respond in valid JSON format exactly as specified.
Be specific, direct, human. Cite numbers. Avoid corporate speak.

When you reference signals, mention the comparison:
  "fix-revert ratio jumped from 15% (3 months ago) to 100% (now)"
  "Ivan ranks #1 most overloaded in team — peer Peter at same tenure is 0.20"

When you suggest actions, address the specific role:
  - For Engineering Managers: focus on team velocity, 1:1 quality, OKR alignment
  - For Senior Engineers: focus on technical debt, knowledge transfer, on-call load
  - For Juniors: focus on growth, safety net, learning loops

NEVER make up data. NEVER hallucinate co-workers. Use ONLY data given."""


   def insight_user_prompt_v2(ctx: dict) -> str:
       name = ctx.get("name", "Unknown")
       role = ctx.get("role", "")
       sigs = ctx.get("signals", {})
       hist = ctx.get("historical_signals_3m_ago", {})
       trend = ctx.get("trend_narrative", {})
       peer = ctx.get("peer_comparison", {})
       role_focus = ctx.get("role_focus", {})
       chunks = ctx.get("retrieved_chunks", [])
       events = ctx.get("recent_events", [])

       # Build trend section
       trend_section = ""
       if trend:
           trend_section = f"""
TREND (3 months ago → now):
  baseline: {trend.get('baseline','')}
  current:  {trend.get('current','')}
  delta:    {trend.get('delta_summary','')}
"""

       # Peer comparison section
       peer_section = ""
       if peer:
           peer_section = f"""
PEER COMPARISON:
  Team avg overload: {peer.get('team_avg_overload',0):.2f}
  Team median:       {peer.get('team_median_overload',0):.2f}
  This person:       {peer.get('person_overload',0):.2f}
  Rank in team:      #{peer.get('rank_in_team','?')} (of {7})
  Best peer (same/similar role): {peer.get('best_peer',{}).get('id','none')}
                       overload {peer.get('best_peer',{}).get('overload',0):.2f}
"""

       # Role focus
       role_section = ""
       if role_focus:
           concerns = ", ".join(role_focus.get("primary_concerns", []))
           questions = role_focus.get("manager_questions", [])
           role_section = f"""
ROLE FOCUS — {role}:
  Primary concerns: {concerns}
  Key manager questions:
{chr(10).join(f'    - {q}' for q in questions)}
"""

       # Retrieved chunks
       chunks_section = ""
       if chunks:
           chunks_section = "\nRELEVANT HISTORY (top events):\n"
           for c in chunks[:8]:
               chunks_section += f"  [{c.get('type','?')}] {c.get('text','')[:100]}\n"

       return f"""Team member: {name} ({role})
Overload score: {ctx.get('overload_score',0):.2f} (0=healthy, 1=critical)

CURRENT SIGNALS (last 14 days):
- Night commits ratio: {sigs.get('night_commits_ratio',0):.2f} (>0.5 concerning)
- Fix/revert ratio: {sigs.get('fix_revert_ratio',0):.2f} (>0.4 firefighting)
- Commit tone delta: {sigs.get('commit_tone_delta',0):.2f}
- PR review lag hours: {sigs.get('pr_review_lag_hours',0):.1f}
- Bus factor: {sigs.get('bus_factor',0):.2f} (>0.7 dangerous)
- Co-author isolation: {sigs.get('co_author_isolation',0):.2f} (1=fully isolated)
- Weekend activity: {sigs.get('weekend_activity',0):.2f}

{trend_section}{peer_section}{role_section}{chunks_section}

Recent activity ({len(events)} events):
{chr(10).join(f"- [{e['type']}] {e['timestamp'][:10]}: {e['short_text']}" for e in events[:10])}

Team connections: {', '.join(ctx.get('neighbors', [])) or 'none (isolated)'}

Respond ONLY with this JSON (no markdown):
{{
  "insights": [
    "specific observation grounded in numbers and trend",
    "another observation comparing peer or historical baseline",
    "third observation tying signals to {role} role concerns"
  ],
  "actions": [
    "concrete action addressing role-specific concern",
    "another concrete action with who/what/when",
    "third concrete action"
  ]
}}"""

5. backend/app/llm/api.py — патч /insights:
   Замени:
       from app.rag.context import build_person_context
       ctx = build_person_context(person_id, conn)
   На:
       try:
           from app.rag.context_v2 import build_person_context_v2
           ctx = build_person_context_v2(person_id, conn)
       except ImportError:
           # Fallback на старый context если v2 не подключился
           from app.rag.context import build_person_context
           ctx = build_person_context(person_id, conn)

   И:
       from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt
   Замени на:
       try:
           from app.llm.prompts_v2 import INSIGHT_SYSTEM_V2 as INSIGHT_SYSTEM, \
                                          insight_user_prompt_v2 as insight_user_prompt
       except ImportError:
           from app.llm.prompts import INSIGHT_SYSTEM, insight_user_prompt

ЗАВИСИМОСТЬ:
  • Agent L должен заполнить historical_signals table через seed_demo_v2.py
  • Без historical_signals — context_v2 graceful fallback (пустой dict, без trend секции)
  • Agent P опционален — если retrieval.py готов, chunks подтянутся

ОГРАНИЧЕНИЯ:
  • Не трогай signals/, graph/, ingest/, dashboard/.
  • Не меняй CONTRACTS.md.
  • НЕ ломай совместимость со старым endpoint — fallback на старый context если v2 не доступен.
  • Build_person_context_v2 НЕ должен делать LLM calls сам по себе (только prompt builder
    использует context).

DoD:
  1. python -c "from app.rag.context_v2 import build_person_context_v2; ..." → возвращает dict
     с полями historical_signals_3m_ago, trend_narrative, peer_comparison, role_focus
  2. curl /insights/ivan → response содержит insights ссылающиеся на trend ("3 months ago")
     или peer ("ranks #1") в тексте
  3. curl /insights/marina → insights с фокусом Engineering Manager (1:1 quality, team velocity)
  4. curl /insights/nikita → insights с фокусом Junior (growth, safety net)
  5. context_v2 graceful — если historical_signals пустая, не падает

ОТЧЁТ.
```

---

## 🅞 AGENT O — Fallback templates + Smart cache

### Branch & worktree
```
branch: agent/o-fallback-cache
worktree: ../veins-agent-o
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent O — Fallback templates + Smart cache
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/llm/fallback.py                ← template-based insight без LLM
  backend/app/llm/smart_cache.py             ← cache с partial invalidation
  backend/app/llm/client.py                  ← патч ask() с fallback на 5xx
  backend/app/llm/api.py                     ← /insights endpoint использует smart_cache
  backend/tests/test_llm/test_fallback.py    (опционально)

ЗАДАЧА:
  1. Если ShadoClaw/Anthropic 5xx (503/529 overloaded) — backend возвращает
     template-based insight вместо raise LLMUnavailable.
  2. Smart cache: если signals не сильно изменились — переиспользуем существующий insight,
     не дёргаем LLM повторно.

КОНТРАКТЫ (см. CONTRACTS.md §Phase 3):
  §Fallback insight format
  §Smart cache (partial invalidation)

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. backend/app/llm/fallback.py:

   from typing import Any

   def generate_fallback_insight(ctx: dict[str, Any]) -> dict[str, Any]:
       """Template-based insight когда LLM недоступен.

       Возвращает same shape как нормальный insight response, но с fallback=true.
       Использует heuristics над сигналами.
       """
       sigs = ctx.get("signals", {})
       name = ctx.get("name", "This person")
       role = ctx.get("role", "engineer")

       insights = []
       actions = []

       # Insight 1: топ-3 самых высоких сигнала
       sorted_sigs = sorted(sigs.items(), key=lambda x: -x[1])[:3]
       if sorted_sigs and sorted_sigs[0][1] > 0.5:
           top_three = ", ".join(f"{k.replace('_',' ')} {int(v*100)}%"
                                  for k, v in sorted_sigs[:3] if v > 0.3)
           insights.append(f"{name}: {top_three} — composite overload {ctx.get('overload_score',0):.2f}.")

       # Insight 2: trend if available
       trend = ctx.get("trend_narrative", {})
       if trend.get("delta_summary"):
           insights.append(f"Trend (3mo→now): {trend['delta_summary']}")

       # Insight 3: peer comparison if available
       peer = ctx.get("peer_comparison", {})
       if peer.get("rank_in_team"):
           insights.append(
               f"Ranks #{peer['rank_in_team']} most overloaded in team "
               f"(team avg {peer.get('team_avg_overload',0):.2f})."
           )

       # If <3 insights, fill with general
       while len(insights) < 3:
           insights.append("Insufficient data for additional patterns.")

       # Actions — role-aware fallback
       role_focus = ctx.get("role_focus", {})
       questions = role_focus.get("manager_questions", [])
       if questions:
           actions.extend(f"Discuss: {q}" for q in questions[:3])

       # If <3 actions, generic
       while len(actions) < 3:
           actions.append("Schedule a 1:1 to discuss workload.")

       return {
           "insights": insights[:3],
           "actions": actions[:3],
       }

2. backend/app/llm/smart_cache.py:

   import hashlib
   import json
   import sqlite3
   from datetime import datetime, timezone
   from typing import Any

   SIGNALS_TO_TRACK = [
       "night_commits_ratio", "fix_revert_ratio", "pr_review_lag_hours",
       "bus_factor", "co_author_isolation", "weekend_activity",
       # commit_tone_delta — не учитываем (cached static value)
   ]

   def init_smart_cache(conn: sqlite3.Connection) -> None:
       conn.executescript("""
           CREATE TABLE IF NOT EXISTS signal_snapshots (
               person_id TEXT NOT NULL,
               signals_hash TEXT NOT NULL,
               signals_json TEXT NOT NULL,
               insight_response TEXT NOT NULL,
               model TEXT,
               created_at TEXT NOT NULL,
               PRIMARY KEY (person_id, signals_hash)
           );
           CREATE INDEX IF NOT EXISTS idx_snapshot_person
                                  ON signal_snapshots(person_id);
       """)
       conn.commit()


   # Status thresholds — критичные границы. Если сигнал пересёк 0.4 или 0.7,
   # status (green/yellow/red) меняется → cache MUST invalidate.
   STATUS_BOUNDARIES = (0.4, 0.7)


   def _bucketize(v: float, threshold: float) -> int:
       """Spec-aware bucketing.

       Внутри одной зоны (green/yellow/red) — корзины по threshold.
       На границе зон — отдельная корзина даже если значение близкое.
       Это предотвращает invalid cache hit когда signal=0.39 → 0.41 (status flip).
       """
       # Determine status zone first
       if v < STATUS_BOUNDARIES[0]:
           zone = 0  # green
           local = v / threshold
       elif v < STATUS_BOUNDARIES[1]:
           zone = 1  # yellow
           local = (v - STATUS_BOUNDARIES[0]) / threshold
       else:
           zone = 2  # red
           local = (v - STATUS_BOUNDARIES[1]) / threshold
       return zone * 100 + int(local)


   def signals_hash(signals: dict, threshold: float = 0.10) -> str:
       """Хэш bucketized signals — изменения менее threshold не меняют hash.

       BUT: пересечение status boundary (0.4 или 0.7) ВСЕГДА меняет hash,
       даже если delta < threshold — иначе cache отдаст RED insight для YELLOW персоны.

       Examples:
         0.04 → 0,    0.13 → 1,   0.39 → 3      (green zone)
         0.41 → 100,  0.55 → 101  (yellow zone)
         0.78 → 200,  0.85 → 200  (red zone, same bucket within zone)
       """
       buckets = []
       for k in SIGNALS_TO_TRACK:
           v = signals.get(k, 0.0)
           bucket = _bucketize(v, threshold)
           buckets.append((k, bucket))
       payload = json.dumps(buckets, sort_keys=True)
       return hashlib.sha256(payload.encode()).hexdigest()[:16]


   def get_cached_insight(person_id: str, current_signals: dict,
                           conn: sqlite3.Connection) -> dict | None:
       """Возвращает cached insight если signals не изменились существенно."""
       sig_hash = signals_hash(current_signals)
       row = conn.execute("""
           SELECT insight_response, model, created_at
             FROM signal_snapshots
            WHERE person_id = ? AND signals_hash = ?
            ORDER BY created_at DESC LIMIT 1
       """, (person_id, sig_hash)).fetchone()
       if not row:
           return None
       try:
           return {
               "response": json.loads(row[0]),
               "model": row[1],
               "created_at": row[2],
           }
       except Exception:
           return None


   def save_insight_snapshot(person_id: str, current_signals: dict,
                              insight_data: dict, model: str,
                              conn: sqlite3.Connection) -> None:
       sig_hash = signals_hash(current_signals)
       conn.execute("""
           INSERT OR REPLACE INTO signal_snapshots
                  (person_id, signals_hash, signals_json,
                   insight_response, model, created_at)
                  VALUES (?, ?, ?, ?, ?, ?)
       """, (
           person_id, sig_hash, json.dumps(current_signals),
           json.dumps(insight_data), model,
           datetime.now(timezone.utc).isoformat(),
       ))
       conn.commit()

3. backend/app/llm/client.py — патч ask():
   Найди функцию ask() и оберни LLM call в try/except для 5xx fallback:

   import anthropic
   ...

   async def ask(model, system, user, cache_key=None, max_tokens=2048,
                 temperature=0.3, fallback_ctx: dict | None = None):
       # ... existing cache lookup ...

       client = _get_client()
       try:
           # ... existing call ...
           response = await client.messages.create(...)
           # ... existing cache save ...
           return result
       except anthropic.APIStatusError as e:
           # 5xx — Anthropic overloaded / временная проблема
           if 500 <= e.status_code < 600:
               logger.warning(f"LLM 5xx ({e.status_code}), falling back to template")
               if fallback_ctx is not None:
                   try:
                       from app.llm.fallback import generate_fallback_insight
                       fb = generate_fallback_insight(fallback_ctx)
                       # Возвращаем как JSON-string чтобы caller распарсил как обычный response
                       return json.dumps(fb)
                   except Exception as fe:
                       logger.error(f"fallback also failed: {fe}")
               # без fallback_ctx — выбрасываем как раньше
           # 4xx или другие — выбрасываем
           raise LLMUnavailable(f"LLM call failed: {e}")
       except Exception as e:
           logger.error(f"LLM ask error: {e}")
           raise LLMUnavailable(f"LLM call failed: {e}")

4. backend/app/llm/api.py — патч /insights endpoint:
   В get_insights():
       from app.llm.smart_cache import init_smart_cache, get_cached_insight, save_insight_snapshot

       conn = get_connection()
       init_smart_cache(conn)  # idempotent

       ctx = build_person_context_v2(person_id, conn) or build_person_context(person_id, conn)
       if not ctx:
           raise PersonNotFound(person_id)

       current_signals = ctx.get("signals", {})

       # Smart cache check
       smart_cached = get_cached_insight(person_id, current_signals, conn)
       if smart_cached:
           data = smart_cached["response"]
           return {
               "person_id": person_id,
               "generated_at": smart_cached["created_at"],
               "model": smart_cached["model"],
               "cached": True,
               "smart_cached": True,
               "insights": data.get("insights", []),
               "actions": data.get("actions", []),
           }

       # Normal flow with fallback
       user = insight_user_prompt(ctx)
       prompt_hash = make_prompt_hash(INSIGHT_SYSTEM, user, "opus")
       try:
           raw = await ask("opus", INSIGHT_SYSTEM, user,
                            cache_key=prompt_hash, fallback_ctx=ctx)
       except LLMUnavailable as e:
           # Если ask() сам не сделал fallback — ловим тут и делаем
           from app.llm.fallback import generate_fallback_insight
           fb = generate_fallback_insight(ctx)
           save_insight_snapshot(person_id, current_signals, fb, "fallback-template", conn)
           return {
               "person_id": person_id,
               "generated_at": datetime.utcnow().isoformat() + "Z",
               "model": "fallback-template",
               "cached": False,
               "fallback": True,
               "insights": fb["insights"],
               "actions": fb["actions"],
           }

       # Parse + save snapshot
       try:
           parsed = json.loads(raw)
           insights = parsed.get("insights", [])[:3]
           actions = parsed.get("actions", [])[:3]
       except Exception:
           insights, actions = [], []

       fallback_used = False
       try:
           # Detect fallback by checking if response was originally JSON we generated
           if "fallback-template" in raw or len(raw) < 100:
               fallback_used = True
       except Exception:
           pass

       result = {
           "insights": insights, "actions": actions,
       }
       save_insight_snapshot(person_id, current_signals, result,
                              "fallback-template" if fallback_used else "opus", conn)

       return {
           "person_id": person_id,
           "generated_at": datetime.utcnow().isoformat() + "Z",
           "model": "fallback-template" if fallback_used else "opus",
           "cached": False,
           "fallback": fallback_used,
           "insights": insights, "actions": actions,
       }

ОГРАНИЧЕНИЯ:
  • Не трогай signals/, graph/, ingest/, dashboard/, rag/.
  • smart_cache.py НЕ зовёт LLM, только SQLite.
  • fallback.py НЕ зовёт LLM, только heuristics.
  • smart_cache snapshot — создавай таблицу если её нет (idempotent init_smart_cache).

DoD:
  1. python -c "from app.llm.fallback import generate_fallback_insight; ..." → 3 insights + 3 actions
  2. curl /insights/ivan → когда ShadoClaw остановлен (test) → response.fallback=true
  3. После first /insights/ivan + cache miss snapshot saved → 2-й запрос (signals не изменились)
     возвращает smart_cached=true мгновенно
  4. После POST /ingest/event с big change (signals jumped >10%) → 3-й запрос → smart_cache miss → новый LLM call

ОТЧЁТ.
```

---

## 🅟 AGENT P — Embeddings + RAG pipeline

### Branch & worktree
```
branch: agent/p-embeddings
worktree: ../veins-agent-p
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent P — Embeddings + RAG pipeline (Qwen3-Embedding-8B)
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/rag/embedder.py            ← OpenRouter embedding client
  backend/app/rag/summarizer.py          ← Sonnet chunk summarizer
  backend/app/rag/retrieval.py           ← numpy cosine similarity
  backend/app/rag/index.py               ← orchestration: read events → summarize → embed → store
  scripts/build_embeddings.py            ← CLI: pre-compute on cold start
  backend/tests/test_rag/test_retrieval.py  (опционально)

ЗАДАЧА:
  RAG pipeline: 200+ events за 14 дней + 3 месяца историй (если Agent L готов)
  → группируем по неделям per person (~12 chunks per person × 7 = 84)
  → Sonnet суммирует каждый chunk в 50 tokens
  → Qwen3-Embedding-8B (через OpenRouter) → 4096-dim вектор
  → SQLite blob storage
  → retrieval по cosine similarity

КОНТРАКТЫ (см. CONTRACTS.md §Phase 3):
  §Embeddings + RAG pipeline
  §SQL schema для embeddings table

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. backend/app/rag/embedder.py:

   import os
   import httpx
   import logging
   import numpy as np
   from typing import List

   logger = logging.getLogger(__name__)

   OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
   OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE_URL",
                                     "https://openrouter.ai/api/v1")
   EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")


   async def embed_text(text: str, timeout: int = 30) -> np.ndarray:
       """Single text → 4096-d numpy array. Returns zeros on failure."""
       if not OPENROUTER_KEY or not text:
           return np.zeros(4096, dtype=np.float32)

       try:
           async with httpx.AsyncClient(timeout=timeout) as client:
               r = await client.post(
                   f"{OPENROUTER_BASE}/embeddings",
                   headers={
                       "Authorization": f"Bearer {OPENROUTER_KEY}",
                       "HTTP-Referer": "https://github.com/bormotun44ik/Veins-Hack",
                       "X-Title": "Veins-Hack",
                       "Content-Type": "application/json",
                   },
                   json={"model": EMBED_MODEL, "input": text},
               )
               r.raise_for_status()
               data = r.json()
               vec = np.array(data["data"][0]["embedding"], dtype=np.float32)
               return vec
       except Exception as e:
           logger.error(f"embed_text failed: {e}")
           return np.zeros(4096, dtype=np.float32)


   async def embed_texts(texts: list[str]) -> list[np.ndarray]:
       """Batch — Qwen via OpenRouter не поддерживает batch input,
       поэтому просто sequential calls с rate-limiting."""
       import asyncio
       results = []
       for i, t in enumerate(texts):
           v = await embed_text(t)
           results.append(v)
           # Rate limit OpenRouter — не больше 60 RPM на free tier
           if i < len(texts) - 1:
               await asyncio.sleep(1.1)
       return results

2. backend/app/rag/summarizer.py:

   import logging
   from typing import Any
   logger = logging.getLogger(__name__)

   SUMMARY_SYSTEM = """You are a data compactor.
Summarize the given week of work events into ONE concise paragraph (max 50 words).
Preserve: timestamps, sentiment, key actions, blockers, who-with-whom.
Do NOT add interpretation. Just compress facts.
Return ONLY the summary text, no JSON, no headers."""


   async def summarize_chunk(person_id: str, week_start: str,
                              events: list[dict]) -> str:
       """Sonnet → 50-word week summary."""
       if not events:
           return ""
       try:
           from app.llm.client import ask
           from app.llm.cache import make_prompt_hash

           # Compress events list to a single string (cap each event short_text)
           event_lines = "\n".join(
               f"- [{e.get('type','?')}] {e.get('timestamp','')[:10]}: "
               f"{(e.get('payload') or {}).get('message','') or (e.get('payload') or {}).get('text','')[:80]}"
               for e in events[:30]  # safety cap
           )

           user = (
               f"Person: {person_id}\n"
               f"Week of: {week_start}\n"
               f"Events ({len(events)}):\n{event_lines}\n\n"
               f"Summarize in <= 50 words."
           )
           cache_key = make_prompt_hash(SUMMARY_SYSTEM, user, "sonnet")
           summary = await ask("sonnet", SUMMARY_SYSTEM, user, cache_key=cache_key)
           return summary.strip()[:500]  # safety cap
       except Exception as e:
           logger.error(f"summarize_chunk failed for {person_id}/{week_start}: {e}")
           return ""

3. backend/app/rag/index.py:

   import asyncio
   import json
   import logging
   import numpy as np
   import sqlite3
   from collections import defaultdict
   from datetime import datetime
   from typing import Any

   from app.rag.embedder import embed_text
   from app.rag.summarizer import summarize_chunk

   logger = logging.getLogger(__name__)


   def init_embeddings_schema(conn: sqlite3.Connection) -> None:
       conn.executescript("""
           CREATE TABLE IF NOT EXISTS embeddings (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               person_id TEXT NOT NULL,
               chunk_kind TEXT NOT NULL,
               chunk_period TEXT,
               text TEXT NOT NULL,
               embedding BLOB NOT NULL,
               source_event_ids TEXT,
               created_at TEXT NOT NULL
           );
           CREATE INDEX IF NOT EXISTS idx_emb_person ON embeddings(person_id);
       """)
       conn.commit()


   def _week_iso(ts: str) -> str:
       """ISO 8601 timestamp → '2026-W14' format."""
       try:
           dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
           y, w, _ = dt.isocalendar()
           return f"{y}-W{w:02d}"
       except Exception:
           return "unknown"


   async def build_index(conn: sqlite3.Connection) -> int:
       """Group events by person × week → summarize → embed → store. Returns count."""
       init_embeddings_schema(conn)

       # Skip if already populated (idempotent)
       existing = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
       if existing > 0:
           logger.info(f"Embeddings index already has {existing} chunks, skipping rebuild")
           return existing

       rows = conn.execute("""
           SELECT id, person_id, type, timestamp, payload_json
             FROM events
            ORDER BY person_id, timestamp ASC
       """).fetchall()

       chunks: dict[tuple[str, str], list[dict]] = defaultdict(list)
       for eid, pid, etype, ts, payload in rows:
           week = _week_iso(ts)
           try:
               p = json.loads(payload) if payload else {}
           except Exception:
               p = {}
           chunks[(pid, week)].append({
               "id": eid, "type": etype, "timestamp": ts, "payload": p,
           })

       count = 0
       for (pid, week), evs in chunks.items():
           if len(evs) < 2:
               continue  # тривиальные chunks не embed-им

           summary = await summarize_chunk(pid, week, evs)
           if not summary:
               continue

           vec = await embed_text(summary)
           if vec.sum() == 0:
               logger.warning(f"empty embedding for {pid}/{week}")
               continue

           conn.execute("""
               INSERT INTO embeddings
                      (person_id, chunk_kind, chunk_period, text, embedding,
                       source_event_ids, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?)
           """, (
               pid, "weekly_summary", week, summary,
               vec.tobytes(),
               json.dumps([e["id"] for e in evs]),
               datetime.utcnow().isoformat(),
           ))
           count += 1
       conn.commit()
       logger.info(f"Built {count} embedding chunks")
       return count

4. backend/app/rag/retrieval.py:

   import asyncio
   import json
   import logging
   import numpy as np
   import sqlite3
   from typing import Any

   from app.rag.embedder import embed_text
   logger = logging.getLogger(__name__)


   def _cosine(a: np.ndarray, b: np.ndarray) -> float:
       na = np.linalg.norm(a)
       nb = np.linalg.norm(b)
       if na == 0 or nb == 0:
           return 0.0
       return float(np.dot(a, b) / (na * nb))


   def get_relevant_chunks(person_id: str, conn: sqlite3.Connection,
                            top_k: int = 8,
                            query: str = "burnout signals firefighting isolation") -> list[dict]:
       """Sync wrapper — для совместимости с context_v2.py.

       Internal: считает embedding query (sync via asyncio.run в отдельном loop),
       делает linear scan через cosine similarity, возвращает top_k.
       """
       try:
           rows = conn.execute("""
               SELECT chunk_period, text, embedding, source_event_ids
                 FROM embeddings WHERE person_id = ?
           """, (person_id,)).fetchall()
           if not rows:
               return []

           # Compute query embedding
           import concurrent.futures
           try:
               loop = asyncio.get_running_loop()
               with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                   query_vec = ex.submit(asyncio.run, embed_text(query)).result()
           except RuntimeError:
               query_vec = asyncio.run(embed_text(query))

           if query_vec.sum() == 0:
               return []

           # Linear scan
           scored = []
           for period, text, blob, src_ids in rows:
               vec = np.frombuffer(blob, dtype=np.float32)
               score = _cosine(query_vec, vec)
               scored.append({
                   "period": period, "text": text,
                   "type": "weekly_summary",
                   "relevance": round(score, 3),
                   "source_event_ids": src_ids,
               })

           scored.sort(key=lambda x: -x["relevance"])
           return scored[:top_k]
       except Exception as e:
           logger.error(f"get_relevant_chunks failed: {e}")
           return []

5. scripts/build_embeddings.py:
   #!/usr/bin/env python3
   """Pre-compute embeddings index on cold start.

   Usage:  BASE=http://localhost:8000 python scripts/build_embeddings.py
           или прямо в backend container:  docker exec ... python -m app.rag.index
   """
   import asyncio
   import os
   import sqlite3
   import sys
   from pathlib import Path

   ROOT = Path(__file__).parent.parent
   DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "db" / "veins.db"))


   async def main():
       sys.path.insert(0, str(ROOT / "backend"))
       from app.rag.index import build_index

       conn = sqlite3.connect(DB_PATH)
       count = await build_index(conn)
       print(f"✅ Built {count} embedding chunks. DB: {DB_PATH}")
       conn.close()


   if __name__ == "__main__":
       asyncio.run(main())

ЗАВИСИМОСТИ:
  • httpx (уже в requirements.txt) — используем для OpenRouter
  • numpy — добавь в requirements.txt: numpy==2.1.2
  • OPENROUTER_API_KEY должен быть в .env (orchestrator уже добавил)

ОГРАНИЧЕНИЯ:
  • Не трогай существующие embedder/retrieval (их и нет, начинаешь с нуля).
  • Не вызывай build_index при каждом запросе — это разовое прогревание (idempotent).
  • Если OPENROUTER_API_KEY пуст или OpenRouter не отвечает → embed_text возвращает
    нулевой вектор → retrieval возвращает [] → context_v2 graceful (chunks: []).
  • Не зови LLM на каждом /insights запросе — retrieval только cosine, embed query 1 раз.
  • build_index БЛОКИРУЮЩИЙ (1.5 минуты на 84 chunks из-за rate limit OpenRouter).
    НЕ запускай его в startup() backend — это zавалит /health на 1.5 мин.
    Вместо этого: scripts/build_embeddings.py запускается ВНЕ контейнера через
    `docker exec ... python -m app.rag.index` ПОСЛЕ docker compose up.
    Orchestrator делает это в integration step 8.

DoD:
  1. python scripts/build_embeddings.py → "Built ~84 chunks" (12 weeks × 7 people)
  2. SELECT COUNT(*) FROM embeddings → > 50
  3. python -c "from app.rag.retrieval import get_relevant_chunks; ..." → top 8 chunks
  4. curl /insights/ivan → response в hot path < 10 sec (retrieval быстрый, embed query 1 sec)
  5. /insights response содержит retrieved_chunks (если context_v2 от Agent N мерджнут)

ОТЧЁТ.
```

---

## Порядок запуска (Лилит)

### Параллельно — стартуют все 5 сразу

```
Agent L — Mock data + trend dataset      (~1.5ч, blocker для M/N/P через данные)
Agent M — Trickle generator              (~1ч, может писать против существующего /ingest/event)
Agent N — Trend & peer-aware insights    (~1.5ч, использует historical_signals если L готов)
Agent O — Fallback + Smart cache         (~1ч, независим)
Agent P — Embeddings RAG pipeline        (~2ч, использует events из Agent L)
```

L и P зависят друг от друга через данные. M/N/O могут начать с моков из CONTRACTS.md
и потом подцепить реальные.

### Integration (orchestrator руками после DONE от всех 5)

1. git fetch --all
2. merge agent/l-mock-expansion → main (data + seed_demo_v2 + new historical_signals table)
3. merge agent/o-fallback-cache → main (smart_cache + fallback)
4. merge agent/n-trend-insights → main (context_v2 + prompts_v2)
5. merge agent/p-embeddings → main (RAG pipeline)
6. merge agent/m-trickle → main (CLI scripts only)
7. python scripts/seed_demo_v2.py --fresh
8. python scripts/build_embeddings.py — прогрев RAG
9. docker compose up --build
10. python scripts/prewarm_cache.py — прогрев Opus insights с новым context_v2
11. Smoke test — все insights имеют trend/peer/role mentions
12. Демо-проверка: python scripts/trickle.py --scenario ivan-burns-out

### После integration

- /insights/{id} возвращает insights с упоминанием "3 months ago" / "ranks #1" / role-specific
- Smart cache: повторный запрос мгновенный, ingest event → инвалидация работает
- Fallback: если ShadoClaw остановить — response.fallback=true вместо 503
- RAG: retrieved_chunks в context, Opus имеет 8 топ-релевантных weekly summaries
- Trickle: фоновый поток событий, граф меняется live

---

## Чеклист orchestrator'а

- [x] CONTRACTS.md обновлён под Phase 3
- [x] AGENT_TASKS_V3.md написан
- [x] .env / .env.example: OPENROUTER_API_KEY + EMBEDDING_MODEL
- [ ] Push в main
- [ ] Передать Лилит этот файл
- [ ] Лилит запускает L, M, N, O, P параллельно
- [ ] git fetch каждые 15-20 мин
- [ ] Merge ветки в порядке L → O → N → P → M
- [ ] seed_demo_v2 + build_embeddings + prewarm
- [ ] docker compose up --build → smoke
- [ ] Demo-проверка с trickle scenario

## Известные нюансы (после self-review при подготовке)

- **L блокирует P через данные**: если L не запушил historical_signals.json, P не сможет
  построить полный index. Mitigation: P graceful — index по любому количеству events.
- **OpenRouter rate limit**: free tier ~60 RPM. 84 chunks × 1 embed = 84 calls = 1.5 минуты на
  build_index. На демо это разовое прогревание, не realtime.
- **smart_cache + fallback взаимодействие**: если ShadoClaw 503 → fallback используется →
  smart_cache сохраняет fallback insight под "fallback-template" model. Следующий запрос с теми
  же signals → smart hit, возвращает fallback. Это OK для демо (стабильность важнее свежести).
- **context_v2 → retrieved_chunks**: если P не готов, поле = [] (graceful), Opus просто не
  получит RAG секцию в prompt. N сначала, P потом.
