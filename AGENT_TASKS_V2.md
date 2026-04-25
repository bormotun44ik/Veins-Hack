# Veins — Agent Tasks (Phase 2)

> 4 промпта для второй волны субагентов. Лилит копирует prompt целиком → запускает агента.
> Все 4 могут стартовать **одновременно** — зависимости развязаны через готовый main + sample fixtures.

**Контекст:** Phase 1 (агенты A–F) завершена и смержена в main, end-to-end работает,
ShadoClaw настроен, /insights/ivan живой. Цель Phase 2 — добавить **Manager Dashboard**
(новый view) и **Live ingest** (POST event → live recompute → frontend увидит изменение).

---

## Общая преамбула (вставлять в КАЖДЫЙ prompt первой секцией)

```
Ты субагент проекта Veins-Hack — Phase 2.
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
4. cp ../Veins-Hack/.env ./.env (если файла нет — говори orchestrator'у)
5. Прочитай целиком:
     ARCHITECTURE.md       — структура, твоя зона ответственности
     CONTRACTS.md          — расширенные эндпоинты §GET /dashboard, §POST /ingest/event
     KARPATHY.md           — как работать (ОБЯЗАТЕЛЬНО)
     AGENT_TASKS_V2.md     — этот файл, твой промпт
     PLAN.md               — общий контекст (readonly)
6. Если зона затрагивает frontend → прочитай DESIGN.md

Применяй KARPATHY.md:
  • не молчи в блокере >15 мин
  • пиши МИНИМУМ кода
  • не выходи из своей зоны
  • не меняй CONTRACTS.md (orchestrator уже расширил его под Phase 2)
  • отчитайся по шаблону DONE/BLOCKED/CHANGED/NEXT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ФАКТЫ ОБ ИНФРАСТРУКТУРЕ (актуально на старт Phase 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• main стабилен, smoke 12/12, /insights/ivan возвращает живой Claude Opus.
• Phase 1 уже сделала: backend/app/{db,config,ingest,signals,graph,llm,rag},
  frontend/src/* (Vite+React+TS+Tailwind+react-force-graph-3d), ShadoClaw в docker.
• docker compose up уже ставит 3 сервиса: shadoclaw, backend, frontend.
• overload_score у Ivan = 0.78 (RED), Maria 0.34 (green), Tom 0.37 (green),
  Anna 0.26 (green), Peter 0.20 (green).
• llm_cache прогрет: 10 entries (5 insights + 5 recognition).

ВАЖНО ПО АРХИТЕКТУРЕ:
  • backend FastAPI app в backend/app/main.py — там include_router для всех routers.
    Если делаешь новый endpoint — создаёшь свой APIRouter и регистрируешь в main.py через
    try/except ImportError (как уже сделано для llm/api.py и graph/api.py).
  • Anthropic SDK вызывает: anthropic.AsyncAnthropic(api_key=os.environ.get("SHADOCLAW_API_KEY","sk-dummy"),
    base_url=os.environ.get("SHADOCLAW_BASE_URL","http://shadoclaw:8317"))
    base_url БЕЗ /v1.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
СТАНДАРТЫ КОДА (как в Phase 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PYTHON:
  • Type hints, parameterized SQL queries, pydantic-settings, async/await,
    try/except на внешние вызовы, logging вместо print, conditional imports
    через try/except ImportError для межагентных зависимостей.

TYPESCRIPT:
  • Строгий TS, типы из src/types.ts (зеркало CONTRACTS), AbortController
    в useEffect-ах с fetch, Tailwind через CSS-переменные.

GIT:
  • Коммиты каждые 30-45 мин, message "<agent-letter>: <short>".
  • Push в свою ветку, НИКОГДА в main. Orchestrator мержит через PR.
```

---

## 🅷 AGENT H — Dashboard backend

### Branch & worktree
```
branch: agent/h-dashboard-backend
worktree: ../veins-agent-h
```

### Prompt (copy-paste целиком)

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent H — Dashboard backend
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ (пишешь ТОЛЬКО в эти файлы):
  backend/app/dashboard/__init__.py        ← новая папка
  backend/app/dashboard/aggregator.py
  backend/app/dashboard/api.py
  backend/tests/test_dashboard/test_api.py (опционально)

И добавляешь ОДНУ строку в backend/app/main.py:
  try: from app.dashboard.api import router as dashboard_router
       app.include_router(dashboard_router)
  except ImportError: pass
(в main.py уже есть похожий блок для llm.api — поставь рядом)

ЗАДАЧА:
  Реализовать GET /dashboard endpoint точно по контракту CONTRACTS.md §GET /dashboard.

КОНТРАКТ ВЫХОДА — точно как в CONTRACTS.md:
  {
    "summary": { red_count, yellow_count, green_count, avg_overload, peak },
    "attention": [{ person_id, name, role, avatar_url, status, overload_score,
                    top_insight, top_action, primary_reason }],
    "shoutouts": [{ person_id, name, role, avatar_url, overload_score }],
    "heatmap": { <person_id>: { 7 signal values 0..1 } },
    "generated_at": ISO8601
  }

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. dashboard/aggregator.py — pure functions, без FastAPI:

   def get_summary(conn) -> dict
     SELECT id, overload_score FROM people
     red = score>0.7, yellow = 0.4-0.7, green = <0.4
     peak = person с max overload_score
     avg = mean(overload_score)

   def get_attention(conn) -> list[dict]
     SELECT * FROM people WHERE overload_score >= 0.4 ORDER BY overload_score DESC
     Для каждого:
       - cached_insight = читать llm_cache по prompt_hash insight для person_id
         (smoke: cache_key для insight = make_cache_key("insight", id, ...) — см. existing /insights/{id} код)
         НО: в llm_cache хранится по SHA256(system+user+model), а не по cache_key.
         Простой путь: дёрнуть локально build_person_context() + insight_user_prompt() →
         посчитать prompt_hash → SELECT response WHERE prompt_hash=?
         Если нет → top_insight = "Run scripts/prewarm_cache.py to generate insights"
         Если есть → распарсить JSON response, взять insights[0] и actions[0]
       - primary_reason = короткая фраза 3-4 слова, генерим через Sonnet:
         system = "Summarize a person's burnout pattern in 3-4 words. Examples:
                   'isolated night-firefighter', 'overwhelmed tech lead',
                   'collaborative steady builder'. Return ONLY the phrase, no quotes."
         user = "Person: {name}. Signals: night={n}, fix_revert={f}, isolation={i}, ..."
         Cache в llm_cache как обычно (используй существующий llm.client.ask).

   def get_shoutouts(conn) -> list[dict]
     SELECT id, name, role, avatar_url, overload_score FROM people
       WHERE overload_score < 0.4 ORDER BY overload_score ASC LIMIT 3

   def get_heatmap(conn) -> dict
     Для каждого person — values 7 сигналов.
     ВАЖНО: НЕ зови tone_delta заново (slow LLM). Возьми кэшированное значение
     из people.metadata_json если оно там есть, иначе 0.5.
     Остальные 6 сигналов — call signals.<name>.compute(pid, conn) (cheap, no LLM).

2. dashboard/api.py:
   from fastapi import APIRouter
   router = APIRouter()

   @router.get("/dashboard")
   def get_dashboard():
     from app.db import get_connection
     from datetime import datetime, timezone
     conn = get_connection()
     return {
       "summary":   get_summary(conn),
       "attention": get_attention(conn),
       "shoutouts": get_shoutouts(conn),
       "heatmap":   get_heatmap(conn),
       "generated_at": datetime.now(timezone.utc).isoformat(),
     }

ОГРАНИЧЕНИЯ:
  • НЕ меняй signals/, llm/, rag/, graph/, ingest/.
  • НЕ зови дорогие LLM операции из get_heatmap (только signals).
  • Endpoint должен отвечать <500ms когда кэш прогрет.

DoD:
  1. curl http://127.0.0.1:8000/dashboard → JSON по контракту
  2. attention содержит ivan c top_insight + top_action (если кэш прогрет)
  3. shoutouts содержит peter, anna, maria
  4. heatmap имеет 5 ключей × 7 значений
  5. summary.peak.person_id == "ivan"

ОТЧЁТ:
  DONE:     ...
  BLOCKED:  ...
  CHANGED:  должно быть пусто (всё в своей зоне) кроме main.py (одна строка)
  NEXT:     что нужно от orchestrator перед мержем в main
```

---

## 🅸 AGENT I — Dashboard frontend

### Branch & worktree
```
branch: agent/i-dashboard-frontend
worktree: ../veins-agent-i
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent I — Dashboard frontend
═══════════════════════════════════════════

ОБЯЗАТЕЛЬНО прочитай DESIGN.md (void-black + emerald, terminal-dark feel).

ЗОНА ОТВЕТСТВЕННОСТИ (пишешь ТОЛЬКО в эти файлы):
  frontend/src/components/Dashboard.tsx          ← новый
  frontend/src/components/HeatmapMatrix.tsx      ← новый
  frontend/src/components/AttentionCard.tsx      ← новый
  frontend/src/components/ShoutoutCard.tsx       ← новый
  frontend/src/components/ViewToggle.tsx         ← новый (Dashboard | Graph)
  frontend/public/samples/sample_dashboard.json  ← скопировать из data/samples/

И ИЗМЕНЕНИЯ (минимум) в существующих:
  frontend/src/types.ts            — добавить DashboardResponse + типы
  frontend/src/api.ts              — добавить fetchDashboard()
  frontend/src/App.tsx             — добавить view-switch (Dashboard / Graph)

ЗАДАЧА:
  Manager Dashboard — первый экран что видит пользователь. Click на attention card
  → переключает view на Graph + selectedId = person_id (используй существующее App state).

КОНТРАКТ ВХОДА: GET /dashboard — см. CONTRACTS.md §GET /dashboard
                Mock fallback: VITE_MOCK=true → fetch /samples/sample_dashboard.json

LAYOUT (см. DESIGN.md за цветами/типографикой):

┌────────────────────────────────────────────────────────────────┐
│ ◈ veins        [Dashboard] [Graph]                       v0.1  │ ← header (ViewToggle)
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  TEAM HEALTH                                  WEEK SUMMARY     │
│  ┌────────────────┐                          ┌──────────────┐ │
│  │ 🔴 1 ⚠         │                          │ Avg: 0.39    │ │
│  │ 🟡 0           │                          │ Peak: ivan   │ │
│  │ 🟢 4           │                          │       0.78   │ │
│  └────────────────┘                          └──────────────┘ │
│                                                                │
│  ATTENTION (1)                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ [avatar] Ivan Petrov · Senior Backend     🔴 RED  78%    │ │
│  │ "isolated night-firefighter"                              │ │
│  │ › 100% night commits + 100% fix/revert...                │ │
│  │ → Schedule 1:1 this week, pair second engineer...        │ │
│  │ [View details]   [Recognition]                           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  SHOUTOUTS                                                     │
│  ┌────────┐ ┌────────┐ ┌────────┐                              │
│  │ Peter  │ │ Anna   │ │ Maria  │                              │
│  │  20%   │ │  26%   │ │  34%   │                              │
│  │ [Send] │ │ [Send] │ │ [Send] │                              │
│  └────────┘ └────────┘ └────────┘                              │
│                                                                │
│  SIGNAL HEATMAP                                                │
│        night  fix   tone  lag   bus   iso   wkend             │
│  ivan  ███    ███   ░░    ░     ░░    ███   ░                 │
│  maria ░      ░     ░░    ░     ░     ░░    ░                 │
│  ...                                                           │
└────────────────────────────────────────────────────────────────┘

КОМПОНЕНТЫ:

1. Dashboard.tsx
   - useEffect: fetchDashboard() при mount + setInterval(10000) для polling
   - useState<DashboardResponse | null>
   - Loading: skeleton (не lorem, просто пульсирующие placeholder-ы)
   - props: onSelectPerson(id) — для перехода в graph view

2. AttentionCard.tsx
   - props: person, onSelectPerson, onRecognition
   - Большая карточка, status badge справа, overload bar progress
   - 2 строки: › top_insight (text-secondary), → top_action (accent)
   - 2 кнопки: "View details" (primary, фокусит graph view), "Recognition" (subtle)

3. ShoutoutCard.tsx
   - Маленькая карточка-кубик, avatar + name + overload%, кнопка Recognition

4. HeatmapMatrix.tsx
   - props: heatmap data
   - Grid: 5 rows (people) × 7 cols (signals)
   - Cell: коробочка ~24x24px, фон по value (0=transparent, 1=accent или red)
     Формула: `background: value > 0.7 ? var(--status-red)
                          : value > 0.4 ? var(--status-yellow)
                          : value > 0.1 ? var(--accent-dim)
                          : transparent`
   - Заголовки колонок: моноширинный xs

5. ViewToggle.tsx
   - Segmented control в header: [Dashboard] [Graph]
   - props: view: "dashboard"|"graph", onChange

6. App.tsx (минимальные правки):
   const [view, setView] = useState<"dashboard"|"graph">("dashboard")
   const [selectedId, setSelectedId] = useState<string|null>(null)

   <ViewToggle view={view} onChange={setView} />

   {view === "dashboard" && (
     <Dashboard onSelectPerson={(id) => { setSelectedId(id); setView("graph") }} />
   )}
   {view === "graph" && (
     <>{existing graph + sidebar layout}</>
   )}

ОГРАНИЧЕНИЯ:
  • Не трогай GraphView.tsx, InsightPanel.tsx, LayerToggle.tsx (сохрани как есть)
  • Никаких новых dependencies — только existing react/three/tailwind
  • Polling INTERVAL = 10 сек (не чаще — нагрузка)

DoD:
  1. cd frontend && npm run dev → localhost:5173 — открывается Dashboard
  2. На экране: summary, 1 attention card (Ivan), 3 shoutout cards, heatmap
  3. Click "View details" на Ivan → переход в Graph view с подсвеченным Иваном
  4. Тёмная тема, emerald accent — соответствует DESIGN.md

ОТЧЁТ.
```

---

## 🅹 AGENT J — Live ingest backend

### Branch & worktree
```
branch: agent/j-live-ingest
worktree: ../veins-agent-j
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent J — Live ingest backend
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/ingest/api.py             ← новый router
  backend/app/ingest/recompute.py       ← новый — cheap recompute без LLM
  backend/tests/test_ingest/test_live_event.py  (опционально)

И добавляешь ОДНУ строку в backend/app/main.py:
  try: from app.ingest.api import router as ingest_api_router
       app.include_router(ingest_api_router)
  except ImportError: pass

ЗАДАЧА:
  POST /ingest/event endpoint точно по CONTRACTS.md §POST /ingest/event.

КОНТРАКТ ВХОДА:
  Body: {
    "person_id": str,
    "type": "commit"|"slack_msg"|"meeting_attended"|"task_update"|"review"|"pr",
    "timestamp": str (optional, default = now UTC ISO8601),
    "payload": dict
  }

КОНТРАКТ ВЫХОДА:
  {
    "person_id": str,
    "event_id": int,
    "old_overload_score": float,
    "new_overload_score": float,
    "old_status": "red"|"yellow"|"green",
    "new_status": "red"|"yellow"|"green",
    "recomputed_signals": list[str]
  }

ДЕТАЛИ РЕАЛИЗАЦИИ:

1. ingest/recompute.py:
   def recompute_cheap(person_id: str, conn) -> dict
     """
     Считает overload БЕЗ tone_delta (LLM call дорог в realtime).
     Использует existing signals.composite.WEIGHTS:
       - night_commits, fix_revert, pr_lag, bus_factor,
         co_isolation, weekend_activity (cheap, no LLM)
       - tone_delta — берёт КЭШИРОВАННОЕ значение из people.metadata_json
         (если есть — используется в weighted sum, иначе 0.5 как neutral)
     Возвращает {
       "old_score": текущий people.overload_score до пересчёта,
       "new_score": посчитанный score,
       "recomputed": list имён сигналов которые реально пересчитались
     }
     В конце UPDATE people SET overload_score = new_score WHERE id=?

2. ingest/api.py:
   from fastapi import APIRouter, Body
   from pydantic import BaseModel
   from app.errors import PersonNotFound, BadEvent

   class IngestEventBody(BaseModel):
     person_id: str
     type: str
     timestamp: str | None = None
     payload: dict

   VALID_TYPES = {"commit","slack_msg","meeting_attended","task_update","review","pr"}

   router = APIRouter()

   @router.post("/ingest/event")
   def ingest_event(body: IngestEventBody):
     from app.db import get_connection
     from app.ingest.recompute import recompute_cheap
     from datetime import datetime, timezone
     import json

     conn = get_connection()
     row = conn.execute("SELECT id FROM people WHERE id=?", (body.person_id,)).fetchone()
     if not row:
       raise PersonNotFound(body.person_id)

     if body.type not in VALID_TYPES:
       raise BadEvent(f"Invalid type: {body.type}")

     ts = body.timestamp or datetime.now(timezone.utc).isoformat()
     cur = conn.execute(
       "INSERT INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
       (body.person_id, body.type, ts, json.dumps(body.payload))
     )
     event_id = cur.lastrowid
     conn.commit()

     result = recompute_cheap(body.person_id, conn)
     return {
       "person_id": body.person_id,
       "event_id": event_id,
       "old_overload_score": result["old_score"],
       "new_overload_score": result["new_score"],
       "old_status": _status(result["old_score"]),
       "new_status": _status(result["new_score"]),
       "recomputed_signals": result["recomputed"],
     }

   def _status(score: float) -> str:
     if score > 0.7: return "red"
     if score > 0.4: return "yellow"
     return "green"

3. backend/app/errors.py — добавить класс BadEvent (если его нет):
   class BadEvent(VeinsError):
     code = "BAD_EVENT"
     http_status = 400

ОГРАНИЧЕНИЯ:
  • НЕ зови LLM из ingest path (slow). tone_delta только из cache.
  • НЕ меняй existing signals/, graph/, llm/.
  • Idempotency не требуется — каждый POST добавляет новый event.

DoD:
  1. curl -X POST http://127.0.0.1:8000/ingest/event \
       -H 'content-type: application/json' \
       -d '{"person_id":"ivan","type":"commit",
            "payload":{"sha":"deadbee","message":"fix: prod broke",
                       "repo_id":"veins-core","branch":"main",
                       "co_authors":[],"files_touched":["src/auth.py"]}}'
     → 200 со старым/новым overload_score
  2. SELECT COUNT(*) FROM events после POST → +1
  3. Score Ivan'а слегка вырос (+0.01..+0.05)
  4. Invalid type → 400 BAD_EVENT
  5. Несуществующий person → 404 PERSON_NOT_FOUND

ОТЧЁТ.
```

---

## 🅺 AGENT K — Push event script

### Branch & worktree
```
branch: agent/k-push-event
worktree: ../veins-agent-k
```

### Prompt

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent K — Demo push event CLI
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  scripts/push_event.py
  scripts/demo_replay.sh   (опционально)

ЗАДАЧА:
  CLI который пушит событие через POST /ingest/event и красиво печатает diff.
  Используется на демо: ты в одном терминале запускаешь команду, жюри видит
  как Frontend через polling (5-10 сек) обновляет граф.

КОНТРАКТ INPUT:
  python scripts/push_event.py <person_id> <type> [<message>] [--night] [--weekend]

ПРИМЕРЫ:
  python scripts/push_event.py ivan commit "fix: revert broke prod again" --night
  python scripts/push_event.py ivan slack "не успею к утру"
  python scripts/push_event.py maria commit "feat: new dashboard"

ОЖИДАЕМЫЙ OUTPUT:
  🚀 Pushing event to http://127.0.0.1:8000/ingest/event
     person:    ivan
     type:      commit
     timestamp: 2026-04-25T02:47:00Z (NIGHT)
     payload:   {"sha":"a7f9e2","message":"fix: revert broke prod again",...}

  ✅ ivan  overload  0.78 → 0.82  (RED → RED)
     event_id: 51
     recomputed: night_commits_ratio, fix_revert_ratio

ДЕТАЛИ:

1. scripts/push_event.py:
   - argparse: positional person_id, type, optional message
   - --night → timestamp = today at 02:47 UTC
   - --weekend → timestamp = ближайшая суббота 14:00 UTC
   - default → timestamp = now
   - Для type='commit' автоматически генерит payload:
       {"sha": <random 7hex>, "message": <message or "fix: untitled">,
        "repo_id":"veins-core", "branch":"main", "co_authors":[],
        "files_touched":["src/auth.py"]}
   - Для type='slack_msg' payload = {"channel":"team-general", "text": <message>,
                                       "reply_to": null, "thread_root": null,
                                       "mentions": [], "sentiment": null}
   - POST через urllib.request (без http клиентов, чтобы не тащить deps)
   - Pretty print результата с цветами (если sys.stdout.isatty()):
       🚀 ✅ → ANSI green/yellow/red по статусу

2. scripts/demo_replay.sh (опционально):
   #!/usr/bin/env bash
   # Прогоняет 3-4 события для демо с задержкой
   set -e
   echo "Press Enter to push event 1: Ivan night commit"
   read
   python scripts/push_event.py ivan commit "fix: revert broke prod again" --night
   sleep 3
   echo "Press Enter to push event 2: Ivan slack at 3am"
   read
   python scripts/push_event.py ivan slack_msg "не успею, всё ломается"
   ...

ОГРАНИЧЕНИЯ:
  • Чистый Python stdlib (argparse, urllib, json, datetime). Никаких pip deps.
  • Не трогай backend, frontend, signals, ingest/api.py — только scripts/.
  • API_BASE из env: BASE=http://localhost:8000 ./scripts/push_event.py ...
    default = http://127.0.0.1:8000

DoD:
  1. python scripts/push_event.py ivan commit "test" --night → 200 OK + diff
  2. python scripts/push_event.py nobody commit "x" → 404 PERSON_NOT_FOUND с ясным сообщением
  3. python scripts/push_event.py ivan invalid_type "x" → 400 BAD_EVENT
  4. На демо: ты вручную пушишь событие → frontend через polling видит обновление

ОТЧЁТ.
```

---

## Порядок запуска (Лилит)

### Параллельно — сейчас

```
4 агента в worktree:
  Agent H — Dashboard backend       (~1ч)
  Agent I — Dashboard frontend      (~1.5ч)
  Agent J — Live ingest backend     (~1ч)
  Agent K — Push event CLI          (~30 мин)
```

H/I/J/K независимы — стартуют одновременно. K можно начать с моков, потом подцепится к J.

### Integration (orchestrator руками, после DONE от всех 4)

1. git fetch --all
2. merge agent/h-dashboard-backend → main
3. merge agent/i-dashboard-frontend → main (resolve App.tsx если есть)
4. merge agent/j-live-ingest → main
5. merge agent/k-push-event → main
6. Frontend polling (orchestrator сам добавит, 15 строк в App.tsx)
7. docker compose up --build → smoke + manual test
8. prewarm_cache.py (включая новый dashboard primary_reason)

### После integration

- /dashboard → 200 с правильной структурой
- Кнопка View details → переход на graph
- POST /ingest/event → frontend через 5-10 сек обновляется
- Демо-сценарий: ты пушишь "ivan night commit" вручную, граф мерцает Ивану

---

## Чеклист orchestrator'а

- [ ] CONTRACTS.md обновлён под Phase 2 (sections /dashboard и /ingest/event)
- [ ] data/samples/sample_dashboard.json создан
- [ ] AGENT_TASKS_V2.md запушен в main
- [ ] Передать Лилит этот файл
- [ ] Лилит запускает H, I, J, K параллельно
- [ ] git fetch каждые 15-20 мин
- [ ] Merge ветки в порядке H → I → J → K
- [ ] Добавить frontend polling (orchestrator сам)
- [ ] Smoke test после integration
- [ ] Prewarm cache (с primary_reason)
