# Veins — Agent Tasks

> 6 готовых ТЗ для субагентов. Лилит копирует prompt целиком → запускает агента.
> Все 6 могут стартовать **одновременно** — зависимости развязаны через `data/samples/`.

---

## Общая преамбула (вставлять в КАЖДЫЙ prompt первой секцией)

```
Ты субагент проекта Veins-Hack — хакатонный MVP для трекинга здоровья команды.
Работаешь в git worktree, пушишь только в свою ветку.

Репо: https://github.com/bormotun44ik/Veins-Hack
Worktree path: /home/bormotun/Code/veins-agent-<X>
Твоя ветка: agent/<X>-<name>

ПЕРЕД ЛЮБЫМ КОДОМ прочитай целиком:
  1. /home/bormotun/Code/Veins-Hack/ARCHITECTURE.md — структура, твоя зона
  2. /home/bormotun/Code/Veins-Hack/CONTRACTS.md    — схемы, API, sample fixtures
  3. /home/bormotun/Code/Veins-Hack/KARPATHY.md     — как ты должен работать
  4. /home/bormotun/Code/Veins-Hack/PLAN.md         — общий контекст (readonly)

Применяй KARPATHY.md ко всему что делаешь:
  • не молчи в блокере >15 мин
  • пиши МИНИМУМ кода
  • не выходи из своей зоны
  • не меняй CONTRACTS.md
  • отчитайся по шаблону DONE/BLOCKED/CHANGED/NEXT

Коммиты: каждые 30-45 минут, сообщение "<agent-letter>: <short>".
Push: только в свою ветку. Никогда не push в main.
```

---

## 🅰️ AGENT A — Ingest + DB

### Branch & worktree
```
branch: agent/a-ingest
worktree: /home/bormotun/Code/veins-agent-a
```

### Prompt для Лилит (copy-paste целиком)

```
[ОБЩАЯ ПРЕАМБУЛА выше]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent A — Ingest + DB
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ (пишешь ТОЛЬКО в эти файлы):
  backend/app/db.py
  backend/app/config.py
  backend/app/ingest/__init__.py
  backend/app/ingest/github.py
  backend/app/ingest/slack.py
  backend/app/ingest/jira.py
  backend/app/ingest/calendar.py
  backend/app/ingest/transcript.py
  backend/tests/test_ingest/*.py (опционально)

ЧТО НУЖНО СДЕЛАТЬ:

1. backend/app/db.py
   - init_db(path: str) -> None  — создаёт таблицы из CONTRACTS.md §SQLite если не существуют
   - get_connection() -> sqlite3.Connection — синглтон, row_factory = sqlite3.Row
   - Использует path из config.DATABASE_PATH

2. backend/app/config.py
   - pydantic-settings BaseSettings, читает .env
   - Поля: database_path, data_dir, github_token, github_repo,
           shadoclaw_api_key, shadoclaw_base_url,
           use_fake_github (bool), log_level,
           groq_api_keys: list[str]  # читает GROQ_API_KEY_1..5, фильтрует пустые
   - Groq ротация: groq_client() → возвращает groq.Groq(api_key=next_key) round-robin
   - Singleton: settings = Settings()

3. backend/app/ingest/github.py
   - async def pull_github(conn) -> int  — возвращает количество загруженных events
   - Если config.use_fake_github == True → читает data/fake_team.json и данные для events
     оттуда (см. sample_events.jsonl формат)
   - Если False → тянет через PyGithub за последние 14 дней из config.github_repo
     (по умолчанию "bormotun44ik/veeins-test")
   - Пишет в таблицы: people, events (type='commit' | 'pr' | 'review'), repos

   МАППИНГ email → person_id (hardcoded, соответствует fake_team.json):
   EMAIL_TO_ID = {
     "ivan.petrov@team.dev":    "ivan",
     "maria.ivanova@team.dev":  "maria",
     "tom.nielsen@team.dev":    "tom",
     "anna.kowalska@team.dev":  "anna",
     "peter.dimitrov@team.dev": "peter",
   }
   Коммиты от неизвестных email — пропускать (continue).
   Если people таблица пустая — засеять из EMAIL_TO_ID + fake_team.json profiles.

4. backend/app/ingest/slack.py
   - async def load_slack(conn) -> int
   - Читает data/mock_slack.json (формат в CONTRACTS §Event type=slack_msg)
   - Пишет в events

5. backend/app/ingest/jira.py
   - async def load_jira(conn) -> int
   - Читает data/mock_jira.json
   - Пишет в tasks + events type='task_update'

6. backend/app/ingest/calendar.py
   - async def load_calendar(conn) -> int
   - Читает data/mock_calendar.json
   - Пишет meetings + events type='calendar', type='meeting_attended'

7. backend/app/ingest/transcript.py
   - async def load_transcript(conn) -> int
   - Если data/transcript.json существует → читает его (pre-computed, быстро)
   - Если НЕ существует → транскрибирует data/meeting.mp3 через Groq Whisper:
       from groq import Groq
       client = settings.groq_client()  # round-robin из config
       with open("data/meeting.mp3", "rb") as f:
           result = client.audio.transcriptions.create(
               model="whisper-large-v3-turbo",
               file=f,
               response_format="verbose_json"
           )
       # Сохранить в data/transcript.json для следующих запусков
   - Из segments считает talk_ratio per speaker (words_spoken / total_words)
   - Пишет events type='meeting_attended' для каждого speaker

8. backend/app/ingest/__init__.py
   - async def ingest_all(conn) -> dict[str, int]  — вызывает все loaders по очереди,
     возвращает {source: count}

ОГРАНИЧЕНИЯ:
  • Не трогай backend/app/signals/, graph/, llm/, rag/
  • Не создавай shared utils кроме db.py
  • Idempotent: повторный ingest не дублирует записи (используй INSERT OR IGNORE по id для
    people/repos/tasks; для events — dedupe по (person_id, type, timestamp, payload hash))

ЗАВИСИМОСТЬ: ждёшь пока Agent F положит файлы в data/. Если их нет — сначала проверь
data/samples/sample_events.jsonl и падай с понятной ошибкой "run Agent F first".

DoD:
  1. docker compose up backend → не падает
  2. из python shell: from app.ingest import ingest_all; ingest_all() → возвращает dict
  3. sqlite3 veins.db "SELECT COUNT(*) FROM events" → > 100
  4. 1 happy-path тест на github.py с фейк-данными

ОТЧЁТ:
  DONE:     ...
  BLOCKED:  ...
  CHANGED:  (должно быть пусто — ты только в своей зоне)
  NEXT:     что должен сделать orchestrator перед мержем в main
```

---

## 🅱️ AGENT B — Signals

### Branch & worktree
```
branch: agent/b-signals
worktree: /home/bormotun/Code/veins-agent-b
```

### Prompt для Лилит

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent B — Signals
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/signals/__init__.py
  backend/app/signals/base.py
  backend/app/signals/night_commits.py
  backend/app/signals/fix_revert.py
  backend/app/signals/tone_delta.py
  backend/app/signals/pr_lag.py
  backend/app/signals/bus_factor.py
  backend/app/signals/co_isolation.py
  backend/app/signals/weekend_activity.py
  backend/app/signals/composite.py
  backend/tests/test_signals/*.py

КОНТРАКТ (CONTRACTS.md §Signal contract):
  Каждый сигнал экспортирует:
    def compute(person_id: str, conn) -> float  # 0.0..1.0

ЗАВИСИМОСТЬ ОТ ДРУГИХ АГЕНТОВ:
  • Работаешь ПРОТИВ data/samples/sample_events.jsonl (не ждёшь Ingest!)
  • Для тестов: test fixture загружает sample_events.jsonl во временную SQLite
    с схемой из CONTRACTS §SQLite
  • Когда Ingest (Agent A) закончит — твой код БЕЗ ИЗМЕНЕНИЙ заработает на живой БД

ДЕТАЛИ СИГНАЛОВ:

1. night_commits.py
   ratio коммитов с 22:00 до 06:00 UTC за последние 14 дней.
   Если коммитов < 5 → return 0.0.
   Нормировано на [0, 1] через min(1.0, ratio * 1.5).

2. fix_revert.py
   ratio коммитов с keywords: fix, bug, revert, hotfix, rollback, oops
   (case-insensitive, в commit.message).
   Нормально 0.2, тревога 0.6+. Нормировано: clamp((ratio - 0.2) / 0.4, 0, 1).

3. tone_delta.py
   Использует from app.llm.client import ask (см. LLM contract).
   Пакетно: берёт последние 20 commit messages → Sonnet → {"sentiment": -1..+1}.
   Берёт первые 20 (baseline) → то же.
   Возвращает sigmoid(baseline - current) → [0, 1].
   Cache-key: "commit_tone:{person_id}:{hash}".

4. pr_lag.py
   avg lag_hours для PR review-ов которые этот человек OPEN'ил (т.е. ждал ревью).
   Нормировано: clamp(avg_hours / 48, 0, 1).  # 48ч = красная тревога

5. bus_factor.py
   % файлов в репо где person — единственный committer за 14 дней.
   max по всем репам в которые он коммитил. Нормировано: ratio напрямую (уже [0,1]).

6. co_isolation.py
   1 - (unique co_authors за 14 дней / max_expected).
   max_expected = 5 (если 5+ coauthors — healthy). Нормировано напрямую.

7. weekend_activity.py
   ratio коммитов на Sat/Sun (UTC). Нормировано: min(1, ratio * 2).

8. composite.py
   WEIGHTS из CONTRACTS §Composite weights.
   def compute_overload(person_id, conn) -> float
   def update_all_people(conn) -> None  # UPDATE people SET overload_score для всех

ОГРАНИЧЕНИЯ:
  • ТОЛЬКО чтение из conn, никаких UPDATE/INSERT кроме composite.update_all_people
  • Не импортируй код из graph/, ingest/ — только db.py и llm/client.py (для tone_delta)
  • Если LLM недоступен → tone_delta возвращает 0.0, НЕ падай

DoD:
  1. pytest backend/tests/test_signals/ → все зелёные
  2. python -c "from app.signals import night_commits; print(night_commits.compute('ivan', conn))"
     → 0.68 для Ивана (на sample)
  3. composite.compute_overload('ivan', conn) → 0.75-0.90
  4. composite.compute_overload('maria', conn) → 0.25-0.45

ОТЧЁТ по шаблону.
```

---

## 🅲 AGENT C — Graph + API

### Branch & worktree
```
branch: agent/c-graph
worktree: /home/bormotun/Code/veins-agent-c
```

### Prompt для Лилит

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent C — Graph Builder + FastAPI
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/main.py                   ← FastAPI entry
  backend/app/errors.py                 ← exception classes (см. CONTRACTS §Error)
  backend/app/graph/__init__.py
  backend/app/graph/builder.py
  backend/app/graph/layers.py
  backend/app/graph/api.py
  backend/tests/test_graph/*.py

ЧТО ДЕЛАЕШЬ:

1. backend/app/errors.py
   VeinsError + PersonNotFound + BadLayer + LLMUnavailable по CONTRACTS §Error contract.

2. backend/app/main.py
   - FastAPI app(title="Veins", version="0.1.0")
   - CORS: localhost:5173
   - on_startup: init_db() + ingest_all() если USE_FAKE_GITHUB (первый запуск)
   - Exception handler для VeinsError → JSON {"error": {"code": ..., "message": ...}}
   - include_router(graph.api.router) и include_router(llm.api.router)  # llm.api пишет Agent D
   - GET /health → {"status": "ok", "version": "0.1.0"}

3. backend/app/graph/builder.py
   - def build_graph(conn) -> networkx.MultiDiGraph
   - Читает events + people + tasks + meetings + edges
   - Создаёт ноды типов Person/Repo/Task/Meeting с properties из CONTRACTS §Graph
   - Создаёт рёбра 5 типов (commits_to, co_authored, reviews_pr, assigned_to, attended)
     из events (агрегация)

4. backend/app/graph/layers.py
   - def stress_layer(G) -> MultiDiGraph   # только Person ноды, без рёбер
   - def collab_layer(G) -> MultiDiGraph   # Person + рёбра co_authored, reviews_pr
   - def workload_layer(G) -> MultiDiGraph # Person + Task + рёбра assigned_to
   - def to_json(G) -> dict  # {"nodes": [...], "links": [...]} по API контракту

5. backend/app/graph/api.py
   - from fastapi import APIRouter
   - GET /graph?layer=<stress|collab|workload>
   - layer default = "stress"
   - invalid layer → raise BadLayer
   - Возвращает result из to_json с полем "layer"

   - GET /person/{person_id}
   - Собирает полный person context (CONTRACTS §API /person/{id})
   - signals читает из UPDATE people SET overload_score (обновляет Agent B)
   - Если человека нет → raise PersonNotFound

ЗАВИСИМОСТЬ:
  • Работаешь против data/samples/sample_events.jsonl (не ждёшь Agent A/B).
  • Для layer'ов — overload_score читается из people.overload_score. До того как Agent B
    пересчитает — используется hardcoded значение из sample_events seed (там проставлено).
  • graph.api.router регистрируется в main.py. llm.api.router тоже — его импорт может
    временно падать (Agent D ещё пишет). Сделай try/except ImportError + print warning
    чтобы стартовал без llm.

ОГРАНИЧЕНИЯ:
  • Не пиши сигналы, не зови Claude
  • Не меняй schema SQLite
  • Не пиши frontend

DoD:
  1. docker compose up backend → http://localhost:8000/health возвращает 200
  2. curl localhost:8000/graph?layer=stress → sample_graph.json-совместимый JSON
  3. curl localhost:8000/graph?layer=collab → есть co_authored рёбра
  4. curl localhost:8000/person/ivan → signals + neighbors
  5. curl localhost:8000/person/notexist → 404 {"error": {"code": "PERSON_NOT_FOUND", ...}}

ОТЧЁТ.
```

---

## 🅳 AGENT D — LLM + RAG

### Branch & worktree
```
branch: agent/d-llm
worktree: /home/bormotun/Code/veins-agent-d
```

### Prompt для Лилит

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent D — LLM Client + RAG + Insight endpoints
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  backend/app/llm/__init__.py
  backend/app/llm/client.py
  backend/app/llm/prompts.py
  backend/app/llm/cache.py
  backend/app/llm/api.py
  backend/app/rag/__init__.py
  backend/app/rag/context.py
  backend/tests/test_llm/*.py

КЛЮЧЕВЫЕ КОНТРАКТЫ (в CONTRACTS.md):
  §LLM client contract
  §Cache key format
  §API /insights/{id}, /action/recognition/{id}

ЧТО ДЕЛАЕШЬ:

1. backend/app/llm/client.py
   - async def ask(model, system, user, cache_key=None, max_tokens=2048, temperature=0.3) -> str
   - Модели:
       opus   → "claude-opus-4-7"
       sonnet → "claude-sonnet-4-6"
       haiku  → "claude-haiku-4-5-20251001"
   - ShadoClaw OpenProxy (no-restricts dev build): локальный прокси на 127.0.0.1:8317
     Полностью совместим с Anthropic Messages API — просто меняем base_url.
     Реализация:
       client = anthropic.AsyncAnthropic(
           api_key="not-required",   # no-restricts версия
           base_url=settings.shadoclaw_base_url  # http://127.0.0.1:8317/v1
       )
     Никаких кастомных заголовков не нужно. Работает как стандартный Anthropic SDK.
   - При cache_key:
       1. check llm_cache table
       2. если hit — return (set contextvar cached=True)
       3. если miss — call Claude, save в cache, return

2. backend/app/llm/cache.py
   - def get_cached(prompt_hash) -> str | None
   - def set_cached(prompt_hash, model, response) -> None
   - def make_prompt_hash(system, user, model) -> str  (из CONTRACTS)

3. backend/app/llm/prompts.py
   Четыре шаблона — jinja не нужен, f-strings достаточно:

   INSIGHT_SYSTEM = "Ты senior engineering manager с эмпатией ..."
   def insight_user_prompt(person_context: dict) -> str: ...
   → output: raw text, 3 буллета insights + 3 буллета actions, парсится regex

   ACTION_SYSTEM = "Ты коуч ..."
   RECOGNITION_SYSTEM = "Ты пишешь тёплое сообщение благодарности ..."
   COMMIT_TONE_SYSTEM = "Оцени sentiment ... return JSON {sentiment: -1..+1}"

4. backend/app/rag/context.py
   - def build_person_context(person_id: str, conn) -> dict
   - Возвращает всё что нужно Claude (без embeddings — для MVP):
       - профиль person (name, role, overload_score, signals)
       - 1-hop соседи: {neighbor_id, edge_type, weight}
       - 20 recent events (commit messages, slack msgs): [{type, timestamp, short_text}]
       - mock signals если есть: slack_silence_days, velocity_delta
   - Size target: <4000 токенов. Если больше — режь events до 10.

5. backend/app/llm/api.py
   - from fastapi import APIRouter
   - GET /insights/{person_id}
     • context = build_person_context(id, conn)
     • если context пустой → PersonNotFound
     • cache_key = make_cache_key("insight", id, sha256(json(context))[:16])
     • text = await ask("opus", INSIGHT_SYSTEM, insight_user_prompt(context), cache_key)
     • parse text → {insights: [str, str, str], actions: [str, str, str]}
     • return {person_id, generated_at, model, cached, insights, actions}

   - POST /action/recognition/{person_id}
     • similar pattern, model=sonnet, шаблон RECOGNITION
     • return {person_id, text}

ЗАВИСИМОСТЬ:
  • Agent C регистрирует твой router. До того как он готов — ты всё равно пишешь модуль,
    orchestrator подключит.
  • Работаешь против data/samples/sample_person.json для тестов context-сборки.
  • Для live LLM вызовов: если нет валидного ключа → тесты падают, это ОК,
    в CI/demo прогреем кэш через scripts/prewarm_cache.py.

ОГРАНИЧЕНИЯ:
  • НЕ трогай graph/, ingest/, signals/. Импортируй из них — ОК.
  • НЕ пиши embeddings (не делаем в MVP — в CONTRACTS обоснование).
  • Parse LLM output устойчиво: если формат сломан → return {"insights": ["LLM returned malformed response"], "actions": []}

DoD:
  1. python -c "import asyncio; from app.llm.client import ask; print(asyncio.run(ask('sonnet','','ping', cache_key='test')))"
     → возвращает строку
  2. curl -X GET localhost:8000/insights/ivan (после интеграции с Agent C) → JSON из CONTRACTS
  3. повторный curl → cached=True, <50ms
  4. prompts.py имеет happy-path тест (mock Claude return)

ОТЧЁТ.
```

---

## 🅴 AGENT E — Frontend

### Branch & worktree
```
branch: agent/e-frontend
worktree: /home/bormotun/Code/veins-agent-e
```

### Prompt для Лилит

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent E — Frontend (Vite + React + react-force-graph-3d)
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  frontend/ полностью

ПРОЧИТАЙ ДОПОЛНИТЕЛЬНО:
  /home/bormotun/Code/Veins-Hack/DESIGN.md — визуал guidelines

ЧТО ДЕЛАЕШЬ:

1. frontend/ bootstrap:
   - package.json + vite.config.ts + tsconfig.json
   - React 18, TypeScript, Tailwind 3, react-force-graph-3d, three
   - PostCSS + Tailwind config
   - npm scripts: dev, build, preview

2. src/types.ts — зеркало CONTRACTS §API (руками, не генерируй):
   - Person, Node, Link, GraphResponse, InsightResponse, PersonResponse

3. src/api.ts:
   - const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000"
   - fetchGraph(layer: "stress"|"collab"|"workload") → GraphResponse
   - fetchPerson(id) → PersonResponse
   - fetchInsights(id) → InsightResponse
   - postRecognition(id) → {text: string}

4. src/components/GraphView.tsx:
   - ForceGraph3D с nodeVal = node.overload_score * 8 + 4
   - nodeColor по status (green/yellow/red из DESIGN)
   - linkColor = белый с opacity 0.3
   - onNodeClick → вызов prop callback

5. src/components/LayerToggle.tsx:
   - Три кнопки в шапке, segmented control
   - onChange(layer) → родитель делает fetchGraph(layer)

6. src/components/InsightPanel.tsx:
   - Если selected === null → пустое состояние "Select a person"
   - Если selected: header (avatar, name, role, status badge, overload bar)
   - Секция Signals (6-7 прогресс-баров)
   - Секция Insights (3 bullet пункта, fade-in анимация)
   - ActionButtons

7. src/components/ActionButtons.tsx:
   - "Что делать" (primary) → показать actions из insights
   - "Написать" (secondary) → открыть modal с pre-filled текстом
   - "Recognition" (secondary) → POST /action/recognition/{id}, показать результат

8. src/App.tsx:
   - State: layer, selectedPersonId, graphData, insightData
   - useEffect: fetchGraph(layer) при смене layer
   - useEffect: fetchPerson(id) + fetchInsights(id) при смене selectedPersonId
   - Layout по DESIGN.md

ДАННЫЕ ДЛЯ РАЗРАБОТКИ (до того как backend готов):
  • В src/api.ts: если import.meta.env.VITE_MOCK === "true" →
    читай /samples/sample_graph.json, /samples/sample_insight.json из public/
  • Скопируй data/samples/sample_graph.json и sample_insight.json в frontend/public/samples/
    в первом коммите

ОГРАНИЧЕНИЯ:
  • НЕ делай роутинг (react-router). Один экран — один URL.
  • НЕ добавляй state-management библиотеки (redux/zustand). useState + useEffect достаточно.
  • НЕ вытаскивай логику в hooks "для красоты" — inline достаточно для MVP.
  • Тёмная тема, никаких переключателей.

DoD:
  1. cd frontend && npm install && npm run dev → http://localhost:5173 открывается
  2. На экране 3D граф с 5 нодами (из sample_graph.json)
  3. Клик на ноду → правая панель показывает InsightPanel с данными из sample_insight.json
  4. Переключение layer-ов работает (визуально меняется)
  5. Action "Recognition" вызывает backend (или mock при VITE_MOCK=true)

ОТЧЁТ.
```

---

## 🅵 AGENT F — Fixtures + Seed + Real GitHub

### Branch & worktree
```
branch: agent/f-fixtures
worktree: /home/bormotun/Code/veins-agent-f
```

### Prompt для Лилит

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent F — Demo fixtures + Real GitHub history + Seed script
═══════════════════════════════════════════

ЗОНА ОТВЕТСТВЕННОСТИ:
  data/ полностью
  scripts/seed_demo.py
  scripts/generate_github_history.py   ← новый скрипт

РЕПО ДЛЯ АНАЛИЗА (живые данные с GitHub):
  https://github.com/bormotun44ik/veeins-test
  GitHub token: из .env GITHUB_TOKEN
  USE_FAKE_GITHUB=false (дефолт)

ЧТО ДЕЛАЕШЬ:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЧАСТЬ 1: Реальная GitHub история
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

scripts/generate_github_history.py
Скрипт генерирует 2 недели реалистичной git-истории в репо veeins-test.
Принцип: коммиты с backdating через GIT_AUTHOR_DATE + GIT_COMMITTER_DATE env vars.

5 git identities (разные user.email/name):
  ivan.petrov@team.dev    — Ivan Petrov
  maria.ivanova@team.dev  — Maria Ivanova
  tom.nielsen@team.dev    — Tom Nielsen
  anna.kowalska@team.dev  — Anna Kowalska
  peter.dimitrov@team.dev — Peter Dimitrov

Паттерны коммитов (14 дней, начиная с today-14d):
  Иван:
    - 60-70% коммитов в 22:00-04:00 UTC
    - 50%+ сообщений содержат: fix, revert, hotfix, bug
    - 0 co-authored коммитов за последние 2 недели
    - ~15 коммитов total
    - Примеры сообщений: "fix: null pointer in auth again",
      "revert: broke login flow", "hotfix: token expiry",
      "fix: race condition in cache", "bug: session not cleared"

  Мария:
    - 90% коммитов в 09:00-18:00 UTC
    - Co-authored: 4+ коммита с tom.nielsen, 2 с anna.kowalska
    - Позитивные сообщения: "feat:", "add:", "improve:", "refactor:"
    - ~12 коммитов

  Том:
    - Дневные коммиты, mix feat/fix
    - Co-authored с Марией
    - ~10 коммитов

  Анна:
    - Дневные, в основном frontend файлы
    - ~8 коммитов

  Пётр:
    - Мало коммитов, рабочее время
    - ~4 коммита

Пример команд (Python subprocess):
  env = {
    "GIT_AUTHOR_NAME": "Ivan Petrov",
    "GIT_AUTHOR_EMAIL": "ivan.petrov@team.dev",
    "GIT_AUTHOR_DATE": "2026-04-10T23:47:00",
    "GIT_COMMITTER_NAME": "Ivan Petrov",
    "GIT_COMMITTER_EMAIL": "ivan.petrov@team.dev",
    "GIT_COMMITTER_DATE": "2026-04-10T23:47:00",
    **os.environ
  }
  subprocess.run(["git", "commit", "-m", "fix: null pointer"], env=env, cwd=repo_path)

Файлы для трогания (рандомные изменения): src/auth.py, src/api.py, src/utils.py,
  src/models.py, tests/test_auth.py, tests/test_api.py, README.md

PR'ы через GitHub API (PyGithub):
  - 3 открытых PR от Ивана (без ревью или с лагом >24ч)
  - 2 PR от Марии (быстро заревьюены Томом)
  Review events тоже создать через API.

После генерации — запушить в veeins-test через `git push`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ЧАСТЬ 2: Mock данные (всё остальное)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. data/fake_team.json — 5 людей (используется только при USE_FAKE_GITHUB=true):
   [
     {"id": "ivan",  "name": "Ivan Petrov",    "role": "Senior Backend Engineer",
      "github_email": "ivan.petrov@team.dev",
      "avatar_url": "https://i.pravatar.cc/150?u=ivan",
      "baseline_sentiment": 0.1,   "archetype": "burnout"},
     {"id": "maria", "name": "Maria Ivanova",  "role": "Tech Lead",
      "github_email": "maria.ivanova@team.dev",
      "avatar_url": "https://i.pravatar.cc/150?u=maria",
      "baseline_sentiment": 0.6,   "archetype": "healthy-leader"},
     {"id": "tom",   "name": "Tom Nielsen",    "role": "Backend Engineer",
      "github_email": "tom.nielsen@team.dev",
      "avatar_url": "https://i.pravatar.cc/150?u=tom",
      "baseline_sentiment": 0.3,   "archetype": "moderate-load"},
     {"id": "anna",  "name": "Anna Kowalska",  "role": "Frontend Engineer",
      "github_email": "anna.kowalska@team.dev",
      "avatar_url": "https://i.pravatar.cc/150?u=anna",
      "baseline_sentiment": 0.5,   "archetype": "healthy"},
     {"id": "peter", "name": "Peter Dimitrov", "role": "QA Engineer",
      "github_email": "peter.dimitrov@team.dev",
      "avatar_url": "https://i.pravatar.cc/150?u=peter",
      "baseline_sentiment": 0.4,   "archetype": "healthy"}
   ]

2. data/samples/sample_events.jsonl
   50 строк, формат из CONTRACTS §Event schema.
   Генерируй на основе тех же паттернов что в GitHub истории:
     ivan ≈ 0.82, maria ≈ 0.35, tom ≈ 0.55, anna ≈ 0.28, peter ≈ 0.22

3. data/samples/sample_graph.json — из CONTRACTS §Sample fixtures, скопируй.
4. data/samples/sample_insight.json — из CONTRACTS.
5. data/samples/sample_person.json — из CONTRACTS.

6. data/mock_slack.json (~60 сообщений, 14 дней):
   Иван: поздние (22:00+), "не успею", "опять баг", тишина 3+ дней
   Мария: активная днём, позитивные реакции
   Остальные: фоновые

7. data/mock_jira.json (~15 задач):
   3 критичных → Иван (2 overdue), Мария 4 in-progress, Том 3, Анна 3, Пётр 2

8. data/mock_calendar.json (~20 митингов):
   Иван: back-to-back (вт/чт), Мария: 2-3/день, остальные: 1-2/день

9. data/meeting.mp3 — скачай любой короткий (2-3 мин) публичный WAV/MP3 с разговором
   (например https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3 как заглушку)
   ИЛИ синтезируй через Python gtts:
     from gtts import gTTS
     text = "Maria: Let's start standup. Tom: I'm blocked on auth module..."
     gTTS(text).save("data/meeting.mp3")

10. data/transcript.json — РЕАЛЬНАЯ транскрипция через Groq Whisper:
    - Берёшь data/meeting.mp3
    - Гонишь через Groq API (whisper-large-v3-turbo, free tier)
    - Groq ключи с ротацией (см. GROQ_API_KEYS в .env)
    - Формат output:
    {
      "meeting_id": "M-2026-04-22-standup",
      "duration_sec": 900,
      "raw_text": "...",
      "segments": [
        {"speaker": "maria", "text": "Let's start...", "start": 0, "end": 8},
        {"speaker": "tom",   "text": "I'm blocked...", "start": 9, "end": 25},
        {"speaker": "ivan",  "text": "ok", "start": 26, "end": 28}
      ]
    }
    ⚠️ Groq Whisper не делает diarization (speaker separation) — присваивай speaker
    по очереди (round-robin: maria→tom→ivan→maria...) если только 1 сегмент.
    Committed в репо чтобы не гнать повторно на демо.

11. scripts/seed_demo.py
    python scripts/seed_demo.py --fresh
    Очищает БД, init_db(), ingest_all()
    Печатает: "Seeded {N} events, {M} people"

ОГРАНИЧЕНИЯ:
  • Не меняй sample_*.json после первого коммита.
  • generate_github_history.py — запускать ОДИН раз, репо veeins-test чистить перед запуском.
  • Если меняешь формат данных — пиши в CONTRACTS.md и жди апрув.

DoD:
  1. python scripts/generate_github_history.py → репо veeins-test содержит ~50 коммитов
  2. cat data/samples/sample_events.jsonl | wc -l → 50
  3. data/transcript.json существует, содержит segments
  4. python scripts/seed_demo.py --fresh → "Seeded ~50 events, 5 people"
  5. jq . data/mock_slack.json → валидный JSON, ~60 записей

ОТЧЁТ.
```

---

## 🅶 AGENT G — Security (фоновый)

Запускается ПОЗЖЕ, после Сб 21:00. Не параллельно с остальными.

```
[ОБЩАЯ ПРЕАМБУЛА]

═══════════════════════════════════════════
ТВОЯ РОЛЬ: Agent G — Security Sweep (read-only)
═══════════════════════════════════════════

ЗАПУСК: только когда Agent A-F отчитались DONE.
Режим: read-only. Ничего не правит сам, только составляет отчёт.

ЗОНА ЧТЕНИЯ: весь репозиторий.
ЗОНА ЗАПИСИ: только SECURITY_REPORT.md в корне репо.

ЧТО ИЩЕШЬ:
  • SQL injection (f-string в sqlite3.execute вместо parameterized queries)
  • Command injection (subprocess shell=True с user input)
  • Secrets leakage (хардкод токенов, .env в коммитах)
  • CORS allow "*" в production-like endpoints
  • Unvalidated user input в FastAPI (Path params без типов)
  • eval/exec/pickle.loads
  • Open redirects, SSRF
  • Missing rate limiting на /insights (дорогой endpoint)

ФОРМАТ ОТЧЁТА (SECURITY_REPORT.md):

  ## Findings

  ### 🔴 Critical
  - [file:line] описание → fix suggestion

  ### 🟡 Medium
  ...

  ### 🟢 Low (nice-to-fix)
  ...

  ## Clean
  Все остальные проверенные паттерны.

DoD:
  1. SECURITY_REPORT.md создан и запушен в agent/g-security
  2. Orchestrator знает что критичного нет или список явных fix'ов
```

---

## Порядок запуска (Лилит читает сверху вниз)

### Фаза 1 — стартуем все 6 одновременно

Пт 21:30 (или сейчас, если начинаем раньше):
```
Лилит запускает 6 subagent'ов в параллель:
  Agent F — Fixtures            (стартует, потому что все нужны его sample_*.json)
  Agent A — Ingest + DB         (ждёт sample_events.jsonl 15 мин, потом кодит)
  Agent B — Signals             (сразу, против sample_events)
  Agent C — Graph + API         (сразу, против sample_events)
  Agent D — LLM + RAG           (сразу, против sample_person/sample_graph)
  Agent E — Frontend            (сразу, против sample_graph/sample_insight)
```

**Agent F стартует первым и за 30-45 мин выдаёт sample_*.json → разблокирует всех.**

### Фаза 2 — Integration hour (orchestrator руками)

После того как 3+ агента отчитались DONE → orchestrator:
1. pull все ветки
2. merge в main по одной через PR
3. docker compose up → smoke test
4. Фиксит конфликты / баги на стыках

### Фаза 3 — Security sweep + polish

Agent G + мелкие UI-fix агенты.

---

## Чеклист orchestrator'а (ты + Claude)

- [ ] Прочитать AGENT_TASKS.md целиком
- [ ] Убедиться что skeleton есть в репо (эту задачу делает Claude-orchestrator)
- [ ] Передать все 6 prompts Лилит — одним сообщением
- [ ] Лилит подтверждает запуск
- [ ] Каждые 20 мин: `git fetch --all; git branch -a` → смотреть что прилетает
- [ ] Как только агент пушит → читать отчёт → мержить/возвращать на доработку
- [ ] Ведёшь интеграционный TODO в голове/чате
```
