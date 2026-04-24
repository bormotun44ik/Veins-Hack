# Veins — Architecture (Single Source of Truth)

> Этот файл — **единственный источник правды** по структуре проекта.
> Любой агент, который хочет добавить файл/папку — сначала правит этот файл, получает апрув orchestrator'а, потом пишет.

---

## Принципы

1. **Один агент = одна папка.** Агент пишет только в свою зону, читает из чужих только через интерфейсы (CONTRACTS.md).
2. **Никаких shared utils.** Если агент A и агент B обоим нужен хелпер — каждый делает свой. Дубликат лучше связи.
3. **Monorepo, две независимые сборки:** backend (Python), frontend (Node). Не импортируют друг друга.
4. **Контракт > реализация.** Код должен соответствовать CONTRACTS.md. Если код и контракт разошлись — меняется код.
5. **Sample fixtures > mock внутри тестов.** Все примеры данных лежат в `data/samples/` и в `CONTRACTS.md` inline.

---

## Дерево проекта

```
Veins-Hack/
├── PLAN.md                     # общий план хакатона (readonly для агентов)
├── ARCHITECTURE.md             # этот файл
├── CONTRACTS.md                # схемы, API, sample fixtures
├── AGENT_TASKS.md              # 6 готовых ТЗ для субагентов
├── KARPATHY.md                 # behavioral guidelines (вставляется в каждый агент-prompt)
├── DESIGN.md                   # UI guidelines (ждём от Лилит)
├── README.md                   # как запустить
├── .env.example
├── docker-compose.yml
│
├── backend/                                # Python, FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml                      # опционально: ruff/mypy config
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                         # FastAPI entry — Agent C
│   │   ├── db.py                           # SQLite connection + init — Agent A
│   │   ├── config.py                       # env loading (pydantic-settings) — Agent A
│   │   │
│   │   ├── ingest/                         # === AGENT A ZONE ===
│   │   │   ├── __init__.py
│   │   │   ├── github.py                   # pull real GitHub OR load data/fake_team.json
│   │   │   ├── slack.py                    # parse data/mock_slack.json
│   │   │   ├── jira.py                     # parse data/mock_jira.json
│   │   │   ├── calendar.py                 # parse data/mock_calendar.json
│   │   │   └── transcript.py               # load data/transcript.json
│   │   │
│   │   ├── signals/                        # === AGENT B ZONE ===
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # abstract: compute(person_id, db) -> float
│   │   │   ├── night_commits.py
│   │   │   ├── fix_revert.py
│   │   │   ├── tone_delta.py               # использует llm/client — bulk mode
│   │   │   ├── pr_lag.py
│   │   │   ├── bus_factor.py
│   │   │   ├── co_isolation.py
│   │   │   ├── weekend_activity.py
│   │   │   └── composite.py                # weighted sum → overload_score
│   │   │
│   │   ├── graph/                          # === AGENT C ZONE ===
│   │   │   ├── __init__.py
│   │   │   ├── builder.py                  # events → NetworkX graph
│   │   │   ├── layers.py                   # stress_layer / collab_layer / workload_layer
│   │   │   └── api.py                      # FastAPI router /graph
│   │   │
│   │   ├── llm/                            # === AGENT D ZONE ===
│   │   │   ├── __init__.py
│   │   │   ├── client.py                   # ShadoClaw wrapper + model router
│   │   │   ├── prompts.py                  # jinja-style templates
│   │   │   ├── cache.py                    # SHA256(prompt) → response in SQLite
│   │   │   └── api.py                      # FastAPI router /insights, /action
│   │   │
│   │   └── rag/                            # === AGENT D ZONE ===
│   │       ├── __init__.py
│   │       └── context.py                  # graph-based context assembly
│   │
│   └── tests/
│       ├── conftest.py                     # общий fixture: seeded in-memory SQLite
│       ├── test_signals/
│       │   └── test_*.py
│       ├── test_graph/
│       │   └── test_*.py
│       └── test_llm/
│           └── test_*.py
│
├── frontend/                               # === AGENT E ZONE === (Vite + React + TS)
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts                          # typed client для FastAPI
│       ├── types.ts                        # зеркало контрактов
│       ├── components/
│       │   ├── GraphView.tsx               # react-force-graph-3d
│       │   ├── LayerToggle.tsx             # 3 кнопки: stress / collab / workload
│       │   ├── InsightPanel.tsx            # sidebar с Claude response
│       │   ├── PersonCard.tsx              # карточка человека в sidebar
│       │   └── ActionButtons.tsx           # "Что делать" / "Написать" / "Recognition"
│       └── styles/
│           └── index.css                   # Tailwind entry
│
├── data/                                   # === AGENT F ZONE ===
│   ├── samples/                            # READONLY для всех, только F пишет
│   │   ├── sample_events.jsonl             # 50 events — референс формата для всех
│   │   ├── sample_graph.json               # пример /graph response
│   │   ├── sample_insight.json             # пример /insights response
│   │   └── sample_person.json              # пример /person/{id}
│   ├── fake_team.json                      # 5 людей с biographies
│   ├── mock_slack.json                     # ~60 сообщений
│   ├── mock_jira.json                      # ~15 задач
│   ├── mock_calendar.json                  # митинги
│   └── transcript.json                     # pre-computed Whisper output
│
└── scripts/
    ├── seed_demo.py                        # Agent F: генерит всё в SQLite из data/
    ├── smoke_test.sh                       # Orchestrator: docker up + curl /graph + /insights
    └── prewarm_cache.py                    # Orchestrator: прогрев Claude кэша перед демо
```

---

## Зоны ответственности агентов

| Agent | Имя | Пишет в | Читает из | Зависит от |
|---|---|---|---|---|
| **A** | Ingest + DB | `backend/app/ingest/`, `backend/app/db.py`, `backend/app/config.py` | `data/*.json` | F (fixtures) |
| **B** | Signals | `backend/app/signals/` + tests | `backend/app/db.py` (через контракт), `data/samples/sample_events.jsonl` | независим (через sample) |
| **C** | Graph + API | `backend/app/graph/`, `backend/app/main.py` | `backend/app/db.py`, `data/samples/sample_events.jsonl` | независим (через sample) |
| **D** | LLM + RAG | `backend/app/llm/`, `backend/app/rag/` | `backend/app/graph/api.py` контракт, `data/samples/sample_graph.json` | независим (через sample) |
| **E** | Frontend | `frontend/` полностью | `data/samples/sample_graph.json`, `sample_insight.json` | независим (через sample) |
| **F** | Fixtures + Seed | `data/`, `scripts/seed_demo.py` | CONTRACTS.md | стартует первым, потом свободен |

**Ключевая идея:** благодаря `data/samples/` все продуктовые агенты стартуют **одновременно**. Они не ждут A/F — у них спецификация формата в sample-файлах.

---

## Workflow агентов (правила)

### Git workflow

1. Каждый агент работает в **своей worktree**: `git worktree add ../veins-agent-<X> agent/<X>-<name>`
2. Коммитит в ветку `agent/<X>-<name>`
3. Когда закончил — пушит + пингует orchestrator
4. **Orchestrator (ты + Claude-интегратор) мержит через PR**. Никаких прямых push в main.

### Что агент НЕ делает

- ❌ Не создаёт файлы вне своей зоны
- ❌ Не меняет CONTRACTS.md / ARCHITECTURE.md / PLAN.md
- ❌ Не ставит зависимости которых нет в `requirements.txt` / `package.json` без согласования
- ❌ Не коммитит `.env` или секреты
- ❌ Не запускает миграции/БД-операции, ломающие других

### Что агент ДЕЛАЕТ

- ✅ Следует CONTRACTS.md как священному писанию
- ✅ Пишет тесты минимум для happy-path (не coverage, а "у меня есть 1 тест что работает")
- ✅ Работает против `data/samples/*` если живой источник не готов
- ✅ При любом сомнении — **останавливается и спрашивает** (см. KARPATHY.md §1)
- ✅ Отчитывается короткой строкой: что сделано / что сломано / что нужно от других

---

## Интеграционные точки

Это места где зоны агентов соприкасаются. Меняются **только с апрувом orchestrator'а**.

### 1. SQLite database (Agent A ↔ all)
- `Agent A` определяет схему в `db.py` (CREATE TABLE statements)
- Все остальные читают через вызов `db.get_connection()` — не знают про путь к файлу
- Схема в CONTRACTS.md §SQLite — **единственная правда**

### 2. FastAPI app (Agent C ↔ Agent D)
- `backend/app/main.py` (C) регистрирует роутеры из `graph/api.py` (C) и `llm/api.py` (D)
- Оба роутера — стандартные `APIRouter()`, подключаются через `app.include_router()`

### 3. LLM client (Agent B ↔ Agent D)
- `Agent B` (signals/tone_delta.py) использует `from app.llm.client import ask`
- Agent D гарантирует что функция `ask()` существует и работает по контракту

### 4. Graph → RAG (Agent C → Agent D внутри app)
- `Agent D` (rag/context.py) читает готовый NetworkX граф через `from app.graph.builder import build_graph`

### 5. Frontend ↔ Backend (Agent E ↔ Agent C/D)
- Frontend использует ТОЛЬКО HTTP API, контракт в CONTRACTS.md §API
- CORS разрешён для `localhost:5173` (Vite dev)

---

## Docker / deploy

```yaml
# docker-compose.yml (managed by orchestrator)
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - veins-db:/app/db
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    depends_on: [backend]

volumes:
  veins-db:
```

SQLite файл живёт в named volume `veins-db` → не пересоздаётся при `docker compose down`.

---

## DoD проекта (к воскресенью 12:00)

1. `docker compose up --build` поднимает backend + frontend за < 30 сек
2. `curl localhost:8000/graph?layer=stress` возвращает JSON с 5 нодами
3. `curl localhost:8000/insights/ivan` возвращает insight (из кэша, мгновенно)
4. `localhost:5173` показывает 3D-граф, клик работает, two-layer toggle работает
5. `scripts/smoke_test.sh` возвращает exit code 0
