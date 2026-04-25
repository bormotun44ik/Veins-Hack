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

         ОБЯЗАТЕЛЬНО кэшируй (без кэша на каждый dashboard reload — N LLM calls).
         Используй существующий llm.client.ask(model="sonnet", ..., cache_key=...).
         cache_key должен зависеть от инсайта чтобы инвалидироваться при изменении:
           insight_hash = sha256(top_insight)[:16]
           cache_key = f"primary_reason:{person_id}:{insight_hash}"
         Если top_insight пуст (cache miss выше) — primary_reason тоже пропускаем,
         возвращаем "" (frontend скроет строку).

   ВАЖНО: если в attention несколько человек — compute primary_reason параллельно:
     Вынеси логику в отдельную:
       async def compute_primary_reason(person: dict, conn) -> str
     Затем в get_attention:
       tasks = [compute_primary_reason(p, conn) for p in attention_people]
       reasons = await asyncio.gather(*tasks)
     Последовательно = N×2s cold cache latency → с gather = 2s независимо от N.

   def get_shoutouts(conn) -> list[dict]
     SELECT id, name, role, avatar_url, overload_score FROM people
       WHERE overload_score < 0.4 ORDER BY overload_score ASC LIMIT 3

   def get_heatmap(conn) -> dict
     Для каждого person — values 7 сигналов.
     ВАЖНО: НЕ зови tone_delta заново (slow LLM). Возьми кэшированное значение
     из people.metadata_json если оно там есть, иначе **0.0** (НЕ 0.5).
     Объяснение: 0.5 = "neutral sentiment по сигмоиду" — информативное значение.
     Если данных нет — мы не знаем нейтрально или нет, показываем 0.0 ("нет данных")
     чтобы heatmap-ячейка была прозрачной (visual cue), а не вводила в заблуждение.
     Остальные 6 сигналов — call signals.<name>.compute(pid, conn) (cheap, no LLM).

2. dashboard/api.py:
   from fastapi import APIRouter
   from pydantic import BaseModel
   from typing import Any
   router = APIRouter()

   # Минимальный response_model — top-level структура, nested как dict/list[dict].
   # Цель: FastAPI генерит OpenAPI schema + валидирует top-level поля.
   # НЕ городи глубокую Pydantic иерархию — это MVP.
   class DashboardResponse(BaseModel):
       summary: dict[str, Any]
       attention: list[dict[str, Any]]
       shoutouts: list[dict[str, Any]]
       heatmap: dict[str, dict[str, float]]
       generated_at: str

   # ОБЯЗАТЕЛЬНО async — внутри get_attention есть await ask(...) для primary_reason.
   # НЕ ИСПОЛЬЗУЙ asyncio.get_event_loop().run_until_complete() — упадёт в FastAPI
   # event loop (это уже было в Phase 1 с tone_delta, чинили через ThreadPoolExecutor;
   # здесь правильно — просто async/await до самого верха).
   @router.get("/dashboard", response_model=DashboardResponse)
   async def get_dashboard():
     from app.db import get_connection
     from datetime import datetime, timezone
     conn = get_connection()
     # Aggregator-функции что используют await ask() — тоже async.
     # get_summary / get_shoutouts / get_heatmap — sync (нет LLM вызовов).
     # get_attention — async (зовёт Sonnet для primary_reason).
     return {
       "summary":   get_summary(conn),
       "attention": await get_attention(conn),
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
  frontend/src/components/GraphPage.tsx          ← новый (рефакторинг — см. App.tsx)
  frontend/public/samples/sample_dashboard.json  ← копируешь ОДИН РАЗ в первом коммите
                                                   из data/samples/. Дальше Vite раздаёт.

И ИЗМЕНЕНИЯ (минимум) в существующих:
  frontend/src/types.ts            — добавить DashboardResponse + типы
                                     ИСТОЧНИК ИСТИНЫ для типов — CONTRACTS.md §GET /dashboard.
                                     Типы в types.ts должны точно зеркалить контракт.
                                     Не выдумывай имена полей — бери из CONTRACTS дословно.
  frontend/src/api.ts              — добавить fetchDashboard():
                                     ```ts
                                     const IS_MOCK = import.meta.env.VITE_MOCK === "true"
                                     export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardResponse> {
                                       const url = IS_MOCK ? "/samples/sample_dashboard.json" : "/dashboard"
                                       const res = await fetch(url, { signal })
                                       if (!res.ok) throw new Error(`dashboard ${res.status}`)
                                       return res.json()
                                     }
                                     ```
                                     Используй тот же IS_MOCK pattern что в Phase 1 api.ts.
  frontend/src/App.tsx             — рефакторинг: вынести существующий graph-layout
                                     в GraphPage.tsx, App.tsx становится тонким switcher

ВАЖНО (рефакторинг App.tsx):
  Phase 1 имеет в App.tsx state (layer/selectedPersonId/graphData/insightData)
  и весь graph layout (header + GraphView + sidebar + InsightPanel).
  Чтобы не наплодить спагетти — выноси ВСЁ это в новый GraphPage.tsx (move,
  не copy — старый код удаляется из App.tsx). После рефакторинга App.tsx:

    export default function App() {
      const [view, setView] = useState<"dashboard"|"graph">("dashboard")
      const [selectedId, setSelectedId] = useState<string|null>(null)
      return (
        <div className="h-screen flex flex-col bg-[--bg-primary]">
          <header className="flex items-center justify-between px-4 h-12 border-b border-[--border]">
            <div className="flex items-center gap-4">
              <span className="font-mono text-sm text-[--accent]">◈ veins</span>
              <ViewToggle view={view} onChange={setView} />
            </div>
            <span className="font-mono text-xs text-[--text-tertiary]">v0.1.0</span>
          </header>
          {view === "dashboard"
            ? <Dashboard onSelectPerson={(id) => { setSelectedId(id); setView("graph") }} />
            : <GraphPage selectedId={selectedId} setSelectedId={setSelectedId} />}
        </div>
      )
    }

  GraphPage.tsx содержит layer-state, fetchGraph, существующий GraphView+InsightPanel layout.
  LayerToggle [Stress|Collab|Workload] остаётся ВНУТРИ GraphPage (не в App header).

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
   - useEffect с polling: КАЖДЫЕ 10 сек ТОЛЬКО для /dashboard endpoint
     (orchestrator отдельно добавит polling 5 сек для /graph и /person в GraphPage —
     не пересекаются, разные endpoints).
   - ОБЯЗАТЕЛЬНО cleanup в useEffect — без этого memory leak когда юзер
     переключился в Graph view:

       useEffect(() => {
         const ctrl = new AbortController()
         let timer: NodeJS.Timeout

         const tick = async () => {
           try {
             const data = await fetchDashboard(ctrl.signal)
             setDashboard(data)
           } catch (e) {
             if (!ctrl.signal.aborted) console.error("dashboard fetch:", e)
           }
         }

         tick()  // immediate
         timer = setInterval(() => {
           if (!document.hidden) tick()  // pause polling when tab hidden (Page Visibility API)
         }, 10000)

         return () => { clearInterval(timer); ctrl.abort() }
       }, [])

   - useState<DashboardResponse | null>
   - Loading: skeleton с animation pulse (см. DESIGN.md §CSS Animations).
     Используй `.animate-pulse` Tailwind class на placeholder-divах.
     Размеры skeleton должны приближённо соответствовать реальным компонентам:
       AttentionCard skeleton: h-24 w-full rounded
       ShoutoutCard skeleton: h-20 w-28 rounded
       HeatmapMatrix skeleton: h-32 w-full rounded
   - ОБЯЗАТЕЛЬНО key={item.person_id} на всех .map() в JSX — без этого React warnings
     в console (жюри видят DevTools).
   - props: onSelectPerson(id) — для перехода в graph view

2. AttentionCard.tsx
   - props: person, onSelectPerson, onRecognition
   - Большая карточка, status badge справа, overload bar progress
   - 2 строки: › top_insight (text-secondary), → top_action (accent)
   - Если top_insight === "" (cache miss на бэке) — показать "warm cache via prewarm"
     placeholder вместо строки.
   - 2 кнопки: "View details" (primary, фокусит graph view), "Recognition" (subtle)

3. ShoutoutCard.tsx
   - Маленькая карточка-кубик, avatar + name + overload%, кнопка Recognition
   - Recognition button вызывает api.postRecognition(id) НАПРЯМУЮ.
     НЕ переиспользуй ActionButtons.tsx (он остаётся в InsightPanel sidebar).
     Свой локальный обработчик — inline success state (не modal, не alert):
       const [sent, setSent] = useState(false)
       onClick: setSent(false) → await postRecognition(id) → setSent(true) → setTimeout(() => setSent(false), 2000)
       Кнопка рендерит: sent ? "✓ Sent" : "Recognition"
     Это чище и быстрее чем modal на демо.

4. HeatmapMatrix.tsx
   - props: heatmap data
   - Grid: 5 rows (people) × 7 cols (signals)
   - Cell: коробочка ~24x24px, фон по value (0=transparent, 1=accent или red)
     Формула: `background: value > 0.7 ? var(--status-red)
                          : value > 0.4 ? var(--status-yellow)
                          : value > 0.1 ? var(--accent-dim)
                          : transparent`
   - Заголовки колонок: моноширинный xs (сокращения: night, fix, tone, lag, bus, iso, wknd)
   - Заголовки строк: имена людей (person.name или person_id) слева от ячеек, моноширинный xs,
     фиксированная ширина ~64px чтобы сетка не плыла

5. ViewToggle.tsx
   - Segmented control. ВНИМАНИЕ: рендерится в App.tsx header **слева** (рядом с
     "◈ veins"), НЕ в центре. Центр header пуст — это для визуальной чистоты.
     LayerToggle [Stress|Collab|Workload] живёт ВНУТРИ GraphPage (не header App.tsx),
     потому что он имеет смысл только в graph view.
   - props: view: "dashboard"|"graph", onChange

6. App.tsx — см. секцию "ВАЖНО (рефакторинг App.tsx)" выше. Тонкий switcher.

7. GraphPage.tsx — move существующего graph-layout сюда:
   - useState<Layer>("stress"), useState<GraphResponse|null>, etc.
   - useEffect fetchGraph при смене layer
   - Header sub-bar: LayerToggle [Stress|Collab|Workload] прямо над графом
   - Layout: GraphView + InsightPanel sidebar (как было в App.tsx Phase 1)
   - props: selectedId, setSelectedId — поднято в App.tsx чтобы выживало переключение view

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

     ВАЖНО: WEIGHTS дублируются ЛОКАЛЬНО (не импортируем из signals.composite).
     Это сознательная изоляция — если signals меняет веса, ingest должен
     осознанно сменить тоже. Comment: "synced from signals.composite WEIGHTS".

         WEIGHTS = {
             "night_commits": 0.20,
             "fix_revert":    0.15,
             "tone_delta":    0.20,
             "pr_lag":        0.10,
             "bus_factor":    0.10,
             "co_isolation":  0.15,
             "weekend":       0.10,
         }

     Логика:
       - night_commits, fix_revert, pr_lag, bus_factor, co_isolation,
         weekend_activity — call signals.<name>.compute(pid, conn) (cheap, no LLM)
       - tone_delta — берёт КЭШИРОВАННОЕ значение из people.metadata_json:
           meta = json.loads(row['metadata_json'] or '{}')
           tone = meta.get('tone_delta_cached', 0.0)
         Fallback **0.0** (НЕ 0.5) — синхронизация с Agent H.
         0.0 = "no data" → ячейка прозрачная в heatmap.
         0.5 было бы misleading "neutral signal" значением.

     Возвращает {
       "old_score": текущий people.overload_score до пересчёта,
       "new_score": посчитанный score,
       "recomputed": list имён сигналов которые реально пересчитались
                     (всегда 6 cheap signals, tone_delta помечается "cached" если был)
     }
     В конце UPDATE people SET overload_score = new_score WHERE id=?

     SQLite concurrency: db.py использует singleton _conn с check_same_thread=False.
     Не открывай новые connections — INSERT events + UPDATE people в одной
     транзакции через один cur. SQLite сам сериализует writes.

2. ingest/api.py:
   from fastapi import APIRouter
   from pydantic import BaseModel
   from typing import Literal
   from app.errors import PersonNotFound, BadEvent

   class IngestEventBody(BaseModel):
     person_id: str
     # Literal → Pydantic сам вернёт 422 с понятным сообщением если type неверный.
     # BadEvent для type-mismatch не нужен — Pydantic перехватывает до кода.
     type: Literal["commit","slack_msg","meeting_attended","task_update","review","pr"]
     timestamp: str | None = None
     payload: dict

   class IngestEventResponse(BaseModel):
     person_id: str
     event_id: int
     old_overload_score: float
     new_overload_score: float
     old_status: str
     new_status: str
     recomputed_signals: list[str]

   router = APIRouter()

   # async def — единообразие с другими endpoints в проекте (FastAPI рекомендация).
   # recompute_cheap внутри pure sync (sqlite + signals.compute), это OK.
   @router.post("/ingest/event", response_model=IngestEventResponse)
   async def ingest_event(body: IngestEventBody):
     from app.db import get_connection
     from app.ingest.recompute import recompute_cheap
     from datetime import datetime, timezone
     import json

     conn = get_connection()

     # Validate person exists
     row = conn.execute("SELECT id FROM people WHERE id=?", (body.person_id,)).fetchone()
     if not row:
       raise PersonNotFound(body.person_id)

     # Validate timestamp format BEFORE any DB writes
     if body.timestamp:
       try:
         datetime.fromisoformat(body.timestamp)  # raises ValueError if not ISO8601
       except ValueError:
         raise BadEvent(f"Invalid timestamp format: '{body.timestamp}' (expected ISO8601)")

     # Validate payload size BEFORE INSERT
     payload_str = json.dumps(body.payload)
     if len(payload_str) > 50_000:
       raise BadEvent(f"Payload too large: {len(payload_str)} bytes (max 50000)")

     ts = body.timestamp or datetime.now(timezone.utc).isoformat()

     cur = conn.execute(
       "INSERT INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
       (body.person_id, body.type, ts, payload_str)
     )
     event_id = cur.lastrowid
     # Commit BEFORE recompute — recompute_cheap reads events table.
     # Новый event должен быть уже в DB чтобы сигналы (fix_revert, night_commits, etc.)
     # посчитали его. SQLite в default journal mode (DELETE) сериализует concurrent
     # writes через file lock — race condition при INSERT+UPDATE невозможен на хакатон-load.
     # Не оптимизируй (single transaction) — это out-of-scope для Agent J.
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

3. backend/app/errors.py — СНАЧАЛА прочитай файл:
   cat backend/app/errors.py
   Если BadEvent уже есть — НЕ дублируй, просто импортируй.
   Если нет — добавь:
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
  3. Score Ivan'а изменился (delta != 0). Точная величина зависит от
     текущего количества events: 1 night-commit поверх 60 уже имеющихся
     даст микро-сдвиг (~+0.003), это нормально. Главное — old != new.
  4. Invalid type → 400 BAD_EVENT
  5. Несуществующий person → 404 PERSON_NOT_FOUND
  6. Payload >50KB → 400 BAD_EVENT с понятным сообщением

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
  python scripts/push_event.py ivan slack_msg "не успею к утру"
  python scripts/push_event.py maria commit "feat: new dashboard"

ВАЛИДНЫЕ TYPES (точно как в CONTRACTS):
  commit | slack_msg | meeting_attended | task_update | review | pr
  ⚠️ "slack" БЕЗ "_msg" — невалидно, упадёт BAD_EVENT.

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
   - --night → timestamp всегда в "ночь только что прошедшую":
       now = datetime.now(UTC); today_2am = now.replace(hour=2, minute=47, second=0, microsecond=0)
       if now < today_2am: today_2am -= timedelta(days=1)  # ещё не дошли до 02:47 сегодня
       Возвращает today_2am. Это попадает в last 14d окно сигналов всегда.
   - --weekend → последняя прошедшая суббота 14:00 UTC
   - default → timestamp = now (UTC ISO8601)
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
   - При ошибке от backend печатать дружелюбно. Например 404:
       ❌ Error 404: person 'nobody' not found.
       Available people: ivan, maria, tom, anna, peter
       (список бери из data/fake_team.json или зашитый константой)
     При 400 BAD_EVENT: показать текст message от backend как есть.

2. scripts/demo_replay.sh (опционально):
   #!/usr/bin/env bash
   # Прогоняет 3-4 события для демо с задержкой.
   # ВАЖНО: задержка >= polling interval frontend'а (10 сек на dashboard,
   # 5 сек на graph). Иначе 2 события объединятся в одно визуальное
   # обновление и WOW-эффект пропадёт.
   set -e
   echo "Press Enter to push event 1: Ivan night commit"
   read
   python scripts/push_event.py ivan commit "fix: revert broke prod again" --night
   sleep 12  # подождём что polling успел показать обновление
   echo "Press Enter to push event 2: Ivan slack at 3am"
   read
   python scripts/push_event.py ivan slack_msg "не успею, всё ломается"
   sleep 12
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
3. merge agent/i-dashboard-frontend → main
   ⚠ App.tsx будет полностью переписан (рефакторинг в GraphPage). Мерж простой:
   берём I-версию целиком — старый код Phase 1 теперь в GraphPage.tsx.
4. merge agent/j-live-ingest → main
5. merge agent/k-push-event → main
6. Polling в GraphPage (orchestrator сам добавит, 15 строк):
   - dashboard polling — Agent I уже сделал (10 сек)
   - graph polling — добавляю в GraphPage (5 сек, вызовет fetchGraph(layer))
   - person polling — НЕ нужен, /person читается только при клике на ноду
7. Обновить scripts/prewarm_cache.py — добавить dashboard прогрев:
   - Сделать GET /dashboard один раз → это прогреет primary_reason для всех
     attention persons (Ivan на текущих данных)
8. docker compose up --build → smoke + manual test
9. python scripts/prewarm_cache.py — все insights+recognition+dashboard

### После integration

- /dashboard → 200 с правильной структурой
- Кнопка View details → переход на graph (selectedId сохраняется)
- POST /ingest/event → dashboard через 10 сек, graph через 5 сек обновляется
- Демо-сценарий: ты пушишь "ivan night commit" вручную, граф мерцает Ивану

---

## Чеклист orchestrator'а

- [x] CONTRACTS.md обновлён под Phase 2 (sections /dashboard и /ingest/event)
- [x] data/samples/sample_dashboard.json создан
- [x] AGENT_TASKS_V2.md запушен в main (с правками после ревью Лилит и self-review)
- [ ] Передать Лилит этот файл
- [ ] Лилит запускает H, I, J, K параллельно
- [ ] git fetch каждые 15-20 мин
- [ ] Merge ветки в порядке H → I → J → K
- [ ] Добавить graph polling в GraphPage (orchestrator)
- [ ] Обновить scripts/prewarm_cache.py: добавить /dashboard вызов
- [ ] docker compose up --build → smoke 12/12 + новые endpoints
- [ ] prewarm — все insights/recognition/dashboard primary_reason'ы

## Известные нюансы (после self-review)

- **Polling stratification:** /dashboard каждые 10 сек (Agent I), /graph каждые
  5 сек (orchestrator после merge). НЕ оба в App.tsx — каждый в своей странице,
  cleanup при unmount.
- **Frontend public/samples:** Agent I копирует sample_dashboard.json один раз
  в первом коммите. Дальше Vite раздаёт автоматом, не нужно перекопировать.
- **WEIGHTS дублируются** в `signals/composite.py` и `ingest/recompute.py`.
  Это сознательная изоляция — если меняешь, синхронизируй обе.
- **tone_delta fallback везде = 0.0** (не 0.5). H, J, и frontend HeatmapMatrix —
  все три используют 0.0 как "no data" → прозрачная heatmap-ячейка.
- **App.tsx рефакторится в тонкий switcher.** Старый layout уезжает в
  GraphPage.tsx (Agent I делает полный move, не copy).
- [ ] Smoke test после integration
- [ ] Prewarm cache (с primary_reason)
