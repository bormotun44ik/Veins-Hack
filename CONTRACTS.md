# Veins — Contracts (API, schemas, fixtures)

> Этот документ — **контракт между всеми агентами**. Если код и контракт расходятся — **код меняется**, не контракт.
> Менять контракт может только **orchestrator** после явного решения.

---

## Оглавление

1. [Environment variables](#environment-variables)
2. [SQLite schema](#sqlite-schema)
3. [Event schema](#event-schema)
4. [Graph schema (nodes + edges)](#graph-schema)
5. [API endpoints](#api-endpoints)
6. [Signal contract](#signal-contract)
7. [LLM client contract](#llm-client-contract)
8. [Cache key format](#cache-key-format)
9. [Error contract](#error-contract)
10. [Sample fixtures (INLINE)](#sample-fixtures)

---

## Environment variables

Файл `.env` (создаётся из `.env.example`):

```bash
# LLM
SHADOCLAW_BASE_URL=https://api.shadoclaw.example.com/v1
SHADOCLAW_API_KEY=sk-shado-xxx
# fallback пока ShadoClaw spec не утверждён:
ANTHROPIC_API_KEY=sk-ant-xxx

# Ingest
GITHUB_TOKEN=ghp_xxx
GROQ_API_KEY=gsk_xxx              # для offline Whisper, если понадобится re-transcribe

# Embeddings (pre-computed, опционально)
OPENROUTER_API_KEY=sk-or-xxx
GOOGLE_AI_API_KEY=xxx             # backup для Gemini

# App
DATABASE_PATH=/app/db/veins.db
DATA_DIR=/app/data
LOG_LEVEL=INFO
USE_FAKE_GITHUB=true              # true → читать data/fake_team.json, false → live API
```

---

## SQLite schema

Создаётся в `backend/app/db.py` функцией `init_db()`. Вызывается при старте FastAPI.

```sql
-- люди (центральные акторы)
CREATE TABLE IF NOT EXISTS people (
  id TEXT PRIMARY KEY,                    -- 'ivan', 'maria', 'tom', 'anna', 'peter'
  name TEXT NOT NULL,                     -- 'Ivan Petrov'
  role TEXT,                              -- 'Senior Backend Engineer'
  avatar_url TEXT,                        -- https://...
  overload_score REAL DEFAULT 0.0,        -- 0.0-1.0, пересчитывается composite.py
  baseline_sentiment REAL DEFAULT 0.0,    -- -1.0 to +1.0, baseline за 3 мес назад
  metadata_json TEXT                      -- JSON: все остальные поля
);

-- сырые события от всех источников
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id TEXT NOT NULL,
  type TEXT NOT NULL,                     -- см. Event.type ниже
  timestamp TEXT NOT NULL,                -- ISO8601 UTC: '2026-04-20T22:47:00Z'
  payload_json TEXT NOT NULL,             -- type-specific payload
  FOREIGN KEY (person_id) REFERENCES people(id)
);
CREATE INDEX IF NOT EXISTS idx_events_person_type ON events(person_id, type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- репозитории
CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,                    -- 'veins-core'
  name TEXT NOT NULL,
  url TEXT
);

-- задачи
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,                    -- 'TASK-1'
  title TEXT NOT NULL,
  priority TEXT,                          -- 'low' | 'medium' | 'high' | 'critical'
  status TEXT,                            -- 'todo' | 'in_progress' | 'review' | 'done'
  deadline TEXT,                          -- ISO8601 или null
  assignee_id TEXT,                       -- person_id
  FOREIGN KEY (assignee_id) REFERENCES people(id)
);

-- митинги
CREATE TABLE IF NOT EXISTS meetings (
  id TEXT PRIMARY KEY,
  title TEXT,
  datetime TEXT,                          -- ISO8601
  duration_minutes INTEGER
);

-- рёбра графа (материализованные)
CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  src TEXT NOT NULL,                      -- person_id или repo_id или task_id
  dst TEXT NOT NULL,
  type TEXT NOT NULL,                     -- см. edge types
  weight REAL DEFAULT 1.0,
  metadata_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);

-- LLM cache (страховка демо)
CREATE TABLE IF NOT EXISTS llm_cache (
  prompt_hash TEXT PRIMARY KEY,           -- SHA256 hex
  model TEXT NOT NULL,                    -- 'opus' | 'sonnet' | 'haiku'
  response TEXT NOT NULL,                 -- JSON string
  created_at TEXT NOT NULL                -- ISO8601
);
```

---

## Event schema

Каждая запись в `events.payload_json` — JSON строка. Структура зависит от `type`.

### `type = 'commit'`
```json
{
  "sha": "a1b2c3d",
  "message": "fix: null pointer in auth",
  "repo_id": "veins-core",
  "branch": "main",
  "co_authors": ["maria"],
  "additions": 12,
  "deletions": 4,
  "files_touched": ["src/auth.py", "tests/test_auth.py"]
}
```

### `type = 'pr'`
```json
{
  "number": 42,
  "repo_id": "veins-core",
  "title": "Add rate limiting",
  "state": "open",
  "created_at": "2026-04-20T10:00:00Z",
  "merged_at": null,
  "reviewers": ["maria"],
  "additions": 120,
  "deletions": 15
}
```

### `type = 'review'`
```json
{
  "pr_number": 42,
  "repo_id": "veins-core",
  "submitted_at": "2026-04-21T08:30:00Z",
  "state": "approved",
  "pr_opened_at": "2026-04-20T10:00:00Z",
  "lag_hours": 22.5
}
```

### `type = 'slack_msg'`
```json
{
  "channel": "team-general",
  "text": "опять этот баг...",
  "reply_to": null,
  "thread_root": null,
  "mentions": [],
  "sentiment": null
}
```

### `type = 'task_update'`
```json
{
  "task_id": "TASK-1",
  "action": "reassigned",
  "from": "tom",
  "to": "ivan",
  "status": "in_progress"
}
```

### `type = 'meeting_attended'`
```json
{
  "meeting_id": "M-2026-04-22-standup",
  "talk_ratio": 0.12,
  "words_spoken": 84,
  "sentiment": -0.3,
  "interruptions_given": 0,
  "interruptions_received": 2
}
```

### `type = 'calendar'`
```json
{
  "title": "1:1 with manager",
  "start": "2026-04-22T14:00:00Z",
  "duration_minutes": 30,
  "back_to_back": true
}
```

---

## Graph schema

### Node types (4 в MVP)

| Type | Properties |
|---|---|
| `Person` | `{ id, name, role, avatar_url, overload_score, baseline_sentiment, status: "green"\|"yellow"\|"red" }` |
| `Repo` | `{ id, name, url }` |
| `Task` | `{ id, title, priority, status, deadline }` |
| `Meeting` | `{ id, title, datetime, duration_minutes }` |

**Status derivation** (builds `Person.status` from `overload_score`):
- `0.0 - 0.4` → `"green"`
- `0.4 - 0.7` → `"yellow"`
- `0.7 - 1.0` → `"red"`

### Edge types (5 в MVP)

| Type | From → To | Properties | Computed from |
|---|---|---|---|
| `commits_to` | Person → Repo | `{ count, recency_days, night_ratio }` | events type='commit' |
| `co_authored` | Person → Person | `{ count_2weeks, last_date }` | commit.co_authors |
| `reviews_pr` | Person → Person | `{ count, avg_lag_hours }` | events type='review' |
| `assigned_to` | Task → Person | `{ priority, overdue: bool }` | tasks table |
| `attended` | Person → Meeting | `{ talk_ratio, sentiment }` | events type='meeting_attended' |

### Three layers (фильтры одного графа)

| Layer | Показывает node types | Показывает edge types |
|---|---|---|
| `stress` | только Person (size = overload_score × 10) | none |
| `collab` | Person | `co_authored`, `reviews_pr` |
| `workload` | Person + Task | `assigned_to` |

---

## API endpoints

Base URL: `http://localhost:8000`

### `GET /health`
```json
→ 200
{ "status": "ok", "version": "0.1.0" }
```

### `GET /graph?layer=<layer>`
Query params: `layer` ∈ `{"stress", "collab", "workload"}`, default `"stress"`.
```json
→ 200
{
  "layer": "collab",
  "nodes": [
    { "id": "ivan",  "type": "Person", "name": "Ivan Petrov",  "role": "Senior Backend",
      "avatar_url": "...", "overload_score": 0.82, "status": "red", "baseline_sentiment": 0.1 },
    { "id": "maria", "type": "Person", "name": "Maria Ivanova", "role": "Tech Lead",
      "avatar_url": "...", "overload_score": 0.35, "status": "green", "baseline_sentiment": 0.6 }
  ],
  "links": [
    { "source": "ivan", "target": "maria", "type": "reviews_pr",
      "weight": 3.0, "metadata": { "count": 3, "avg_lag_hours": 22.5 } },
    { "source": "maria", "target": "ivan", "type": "co_authored",
      "weight": 1.0, "metadata": { "count_2weeks": 1, "last_date": "2026-04-10T09:00:00Z" } }
  ]
}
```

### `GET /person/{id}`
```json
→ 200
{
  "id": "ivan",
  "name": "Ivan Petrov",
  "role": "Senior Backend Engineer",
  "avatar_url": "https://...",
  "status": "red",
  "overload_score": 0.82,
  "signals": {
    "night_commits_ratio": 0.68,
    "fix_revert_ratio": 0.55,
    "commit_tone_delta": -0.71,
    "pr_review_lag_hours": 38.0,
    "bus_factor": 0.78,
    "co_author_isolation": 1.0,
    "weekend_activity": 0.4
  },
  "mock_signals": {
    "slack_silence_days": 3,
    "velocity_delta": -0.4,
    "back_to_back_meetings_pct": 0.7
  },
  "neighbors": ["maria", "tom"],
  "recent_events_count": 47
}
```

### `GET /insights/{person_id}`
```json
→ 200
{
  "person_id": "ivan",
  "generated_at": "2026-04-24T12:00:00Z",
  "model": "opus",
  "cached": true,
  "insights": [
    "За 2 недели коммиты только ночью (68% после 22:00), вдвое выше baseline.",
    "55% коммитов — fix/revert. Человек тушит пожары, а не делает фичи.",
    "Единственный owner 78% файлов в repo — критический bus factor."
  ],
  "actions": [
    "Провести 1:1 сегодня, фокус на нагрузке, не на задачах.",
    "Перебросить 2 таска на Тома (у него overload 0.3).",
    "Организовать knowledge sharing по auth-модулю — снизит bus factor."
  ]
}
```

### `POST /action/recognition/{person_id}`
```json
→ 200
{
  "person_id": "maria",
  "text": "Maria, спасибо за быстрый ревью PR #42 вчера и за то что разобралась с моим тред-багом в 18:00 пятницы. Ты снова спасла спринт 🙏"
}
```

### `GET /dashboard` *(phase 2 — Agent H)*

Manager overview — single screen, всё что нужно для "ситуация команды за 3 секунды".

```json
→ 200
{
  "summary": {
    "red_count": 1,
    "yellow_count": 0,
    "green_count": 4,
    "avg_overload": 0.39,
    "peak": { "person_id": "ivan", "overload_score": 0.78 }
  },
  "attention": [
    {
      "person_id": "ivan",
      "name": "Ivan Petrov",
      "role": "Senior Backend Engineer",
      "avatar_url": "https://i.pravatar.cc/150?u=ivan",
      "status": "red",
      "overload_score": 0.78,
      "top_insight": "100% night commits + 100% fix/revert ratio + full co-author isolation = solo-firefighting production at night.",
      "top_action": "Schedule 1:1 this week, pair second engineer onto veins-core to break isolation.",
      "primary_reason": "isolated night-firefighter"
    }
  ],
  "shoutouts": [
    { "person_id": "peter", "name": "Peter Dimitrov", "role": "QA Engineer",
      "avatar_url": "https://i.pravatar.cc/150?u=peter", "overload_score": 0.20 },
    { "person_id": "anna",  "name": "Anna Kowalska",  "role": "Frontend Engineer",
      "avatar_url": "https://i.pravatar.cc/150?u=anna",  "overload_score": 0.26 },
    { "person_id": "maria", "name": "Maria Ivanova",  "role": "Tech Lead",
      "avatar_url": "https://i.pravatar.cc/150?u=maria", "overload_score": 0.34 }
  ],
  "heatmap": {
    "ivan": {
      "night_commits_ratio": 1.0, "fix_revert_ratio": 1.0, "commit_tone_delta": 0.5,
      "pr_review_lag_hours": 0.75, "bus_factor": 0.67, "co_author_isolation": 1.0,
      "weekend_activity": 0.40
    },
    "maria": { "...": "...same shape per person" }
  },
  "generated_at": "2026-04-25T08:00:00Z"
}
```

**Правила Agent H:**
- `attention` — все red + yellow, отсортированы по overload убыванию.
- `shoutouts` — top 3 green с наименьшим overload. Если зелёных < 3 — берёт что есть.
- `top_insight` / `top_action` — первый элемент из cached `/insights/{person_id}`. Если кэша нет → endpoint **не зовёт live LLM** (демо-критично, не тормозить), вместо этого возвращает строку `"Cache warm-up needed — run scripts/prewarm_cache.py"`.
- `primary_reason` — короткая подпись (3-4 слова), генерируется через Sonnet 1 раз и кешируется в `llm_cache` под key `dashboard_reason:{person_id}:{insight_hash}`.

### `POST /ingest/event` *(phase 2 — Agent J)*

Live data append — для демо-сценария "Иван закоммитил прямо сейчас".

```json
← Body
{
  "person_id": "ivan",
  "type": "commit",                     // commit | slack_msg | meeting_attended | task_update | review | pr
  "timestamp": "2026-04-25T02:47:00Z",  // optional, default = now
  "payload": {                          // type-specific (см. Event schema)
    "sha": "deadbee",
    "message": "fix: revert broke prod again",
    "repo_id": "veins-core",
    "branch": "main",
    "co_authors": [],
    "files_touched": ["src/auth.py"]
  }
}

→ 200
{
  "person_id": "ivan",
  "event_id": 51,
  "old_overload_score": 0.78,
  "new_overload_score": 0.83,
  "old_status": "red",
  "new_status": "red",
  "recomputed_signals": ["night_commits_ratio", "fix_revert_ratio"]
}
```

**Правила Agent J:**
- INSERT в events
- Дёргает `composite.compute_overload(person_id)` — **БЕЗ tone_delta** (slow LLM call), только дешёвые сигналы. tone_delta пересчитываем не чаще раз в 5 минут (cooldown).
- UPDATE people SET overload_score
- Возвращает diff чтобы frontend мог анимировать изменение
- Не валидирует payload против Event schema на этом этапе (trust caller для демо)

### Error responses

Все ошибки — формат `{ "error": { "code": "STRING", "message": "human readable" } }`

| HTTP | code | when |
|---|---|---|
| 400 | `BAD_LAYER` | invalid `?layer=` value |
| 400 | `BAD_EVENT` | `POST /ingest/event` с invalid type или missing person_id |
| 404 | `PERSON_NOT_FOUND` | `/person/{id}` или `/ingest/event` с несуществующим person_id |
| 503 | `LLM_UNAVAILABLE` | ShadoClaw недоступен И кэша нет |
| 500 | `INTERNAL_ERROR` | всё остальное |

---

## Signal contract

Каждый сигнал — отдельный модуль `backend/app/signals/<name>.py`, экспортирует:

```python
def compute(person_id: str, conn) -> float:
    """
    Возвращает метрику в [0.0, 1.0].
    0.0 = норма, 1.0 = максимальная тревога.

    Params:
        person_id: ID из таблицы people
        conn: sqlite3.Connection (readonly)

    Returns:
        float в [0.0, 1.0]. Если данных недостаточно — возвращает 0.0.

    Не бросает исключения наружу (на ошибку БД → лог + return 0.0).
    """
```

### Composite weights (в `composite.py`)

```python
WEIGHTS = {
    "night_commits":   0.20,
    "fix_revert":      0.15,
    "tone_delta":      0.20,   # главный сигнал
    "pr_lag":          0.10,
    "bus_factor":      0.10,
    "co_isolation":    0.15,
    "weekend":         0.10,
}
# overload_score = clamp(sum(weight[k] * signal[k] for k in WEIGHTS), 0.0, 1.0)
```

---

## LLM client contract

`backend/app/llm/client.py`:

```python
from typing import Literal

Model = Literal["opus", "sonnet", "haiku"]

async def ask(
    model: Model,
    system: str,
    user: str,
    cache_key: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """
    Единая точка входа к Claude через ShadoClaw.

    Если cache_key задан — сначала проверяется llm_cache table.
    Если hit — возвращает из кэша, ставит флаг cached=True через contextvar.

    Реальные модели (за алиасами):
      opus   → claude-opus-4-7
      sonnet → claude-sonnet-4-6
      haiku  → claude-haiku-4-5-20251001

    При сетевой ошибке:
      1. Проверяет llm_cache ещё раз
      2. Если кэш пустой — raises LLMUnavailable

    Returns:
        str — raw text response (caller парсит JSON если нужно)
    """
```

### ShadoClaw interface (TENTATIVE — уточняется)

```python
# Пока нет spec от Алексея — заглушка использует стандартный Anthropic SDK.
# При получении spec меняется ТОЛЬКО тело функции ask() — контракт остаётся.

# Headers:
#   Authorization: Bearer <SHADOCLAW_API_KEY>
#   Content-Type: application/json
#
# Request body совместим с Anthropic Messages API.
# Response тоже совместим.
```

---

## Cache key format

```python
import hashlib, json

def make_cache_key(task: str, person_id: str, input_hash: str) -> str:
    """
    task: "insight" | "action" | "recognition" | "commit_tone"
    person_id: "ivan"
    input_hash: SHA256(json.dumps(context, sort_keys=True))[:16]
    """
    return f"{task}:{person_id}:{input_hash}"

def make_prompt_hash(system: str, user: str, model: str) -> str:
    payload = json.dumps({"s": system, "u": user, "m": model}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
```

Pre-warming: `scripts/prewarm_cache.py` прогоняет все 5 людей × 4 задачи = 20 кэш-записей перед демо.

---

## Error contract

```python
# backend/app/errors.py (Agent C создаёт)
class VeinsError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

class PersonNotFound(VeinsError):
    code = "PERSON_NOT_FOUND"
    http_status = 404

class BadLayer(VeinsError):
    code = "BAD_LAYER"
    http_status = 400

class LLMUnavailable(VeinsError):
    code = "LLM_UNAVAILABLE"
    http_status = 503
```

FastAPI exception handler ловит VeinsError → возвращает JSON по формату выше.

---

## Sample fixtures

Эти примеры **обязательны для агентов B, C, D, E** — они пишут против них, пока ingest не готов.
Полные файлы лежат в `data/samples/`.

### `sample_events.jsonl` (первые 10 строк, всего 50)

```jsonl
{"id": 1, "person_id": "ivan", "type": "commit", "timestamp": "2026-04-22T23:47:00Z", "payload": {"sha": "a1b2c3d", "message": "fix: another null pointer in auth again", "repo_id": "veins-core", "branch": "main", "co_authors": [], "additions": 4, "deletions": 2, "files_touched": ["src/auth.py"]}}
{"id": 2, "person_id": "ivan", "type": "commit", "timestamp": "2026-04-23T02:12:00Z", "payload": {"sha": "b2c3d4e", "message": "revert: broke auth, rolling back", "repo_id": "veins-core", "branch": "main", "co_authors": [], "additions": 0, "deletions": 18, "files_touched": ["src/auth.py"]}}
{"id": 3, "person_id": "ivan", "type": "commit", "timestamp": "2026-04-23T03:05:00Z", "payload": {"sha": "c3d4e5f", "message": "hotfix: token expiry not checked", "repo_id": "veins-core", "branch": "main", "co_authors": [], "additions": 8, "deletions": 2, "files_touched": ["src/auth.py"]}}
{"id": 4, "person_id": "maria", "type": "commit", "timestamp": "2026-04-22T10:15:00Z", "payload": {"sha": "d4e5f6g", "message": "feat: add pagination to user list", "repo_id": "veins-core", "branch": "feat/pagination", "co_authors": ["tom"], "additions": 45, "deletions": 3, "files_touched": ["src/api/users.py", "tests/test_users.py"]}}
{"id": 5, "person_id": "maria", "type": "review", "timestamp": "2026-04-22T14:30:00Z", "payload": {"pr_number": 42, "repo_id": "veins-core", "submitted_at": "2026-04-22T14:30:00Z", "state": "approved", "pr_opened_at": "2026-04-22T13:55:00Z", "lag_hours": 0.58}}
{"id": 6, "person_id": "tom", "type": "commit", "timestamp": "2026-04-22T11:40:00Z", "payload": {"sha": "e5f6g7h", "message": "refactor: extract validator helper", "repo_id": "veins-core", "branch": "main", "co_authors": ["maria"], "additions": 30, "deletions": 28, "files_touched": ["src/validators.py"]}}
{"id": 7, "person_id": "ivan", "type": "pr", "timestamp": "2026-04-21T22:30:00Z", "payload": {"number": 51, "repo_id": "veins-core", "title": "Fix: race in session cache", "state": "open", "created_at": "2026-04-21T22:30:00Z", "merged_at": null, "reviewers": ["maria"], "additions": 80, "deletions": 45}}
{"id": 8, "person_id": "maria", "type": "review", "timestamp": "2026-04-23T16:00:00Z", "payload": {"pr_number": 51, "repo_id": "veins-core", "submitted_at": "2026-04-23T16:00:00Z", "state": "changes_requested", "pr_opened_at": "2026-04-21T22:30:00Z", "lag_hours": 41.5}}
{"id": 9, "person_id": "ivan", "type": "slack_msg", "timestamp": "2026-04-22T23:51:00Z", "payload": {"channel": "team-general", "text": "не успею к дедлайну завтра", "reply_to": null, "thread_root": null, "mentions": [], "sentiment": null}}
{"id": 10, "person_id": "ivan", "type": "meeting_attended", "timestamp": "2026-04-22T09:00:00Z", "payload": {"meeting_id": "M-2026-04-22-standup", "talk_ratio": 0.08, "words_spoken": 34, "sentiment": -0.4, "interruptions_given": 0, "interruptions_received": 1}}
```

### `sample_graph.json`

```json
{
  "layer": "collab",
  "nodes": [
    {"id": "ivan", "type": "Person", "name": "Ivan Petrov", "role": "Senior Backend",
     "avatar_url": "https://i.pravatar.cc/150?u=ivan", "overload_score": 0.82,
     "status": "red", "baseline_sentiment": 0.1},
    {"id": "maria", "type": "Person", "name": "Maria Ivanova", "role": "Tech Lead",
     "avatar_url": "https://i.pravatar.cc/150?u=maria", "overload_score": 0.35,
     "status": "green", "baseline_sentiment": 0.6},
    {"id": "tom", "type": "Person", "name": "Tom Nielsen", "role": "Backend",
     "avatar_url": "https://i.pravatar.cc/150?u=tom", "overload_score": 0.55,
     "status": "yellow", "baseline_sentiment": 0.3},
    {"id": "anna", "type": "Person", "name": "Anna Kowalska", "role": "Frontend",
     "avatar_url": "https://i.pravatar.cc/150?u=anna", "overload_score": 0.28,
     "status": "green", "baseline_sentiment": 0.5},
    {"id": "peter", "type": "Person", "name": "Peter Dimitrov", "role": "QA",
     "avatar_url": "https://i.pravatar.cc/150?u=peter", "overload_score": 0.22,
     "status": "green", "baseline_sentiment": 0.4}
  ],
  "links": [
    {"source": "ivan", "target": "maria", "type": "reviews_pr", "weight": 3.0,
     "metadata": {"count": 3, "avg_lag_hours": 28.5}},
    {"source": "maria", "target": "tom", "type": "co_authored", "weight": 4.0,
     "metadata": {"count_2weeks": 4, "last_date": "2026-04-23T10:00:00Z"}},
    {"source": "maria", "target": "anna", "type": "co_authored", "weight": 2.0,
     "metadata": {"count_2weeks": 2, "last_date": "2026-04-20T15:00:00Z"}},
    {"source": "tom", "target": "peter", "type": "reviews_pr", "weight": 2.0,
     "metadata": {"count": 2, "avg_lag_hours": 6.0}}
  ]
}
```

Заметка для демо: `ivan` имеет **нулевые co_authored** рёбра — это визуальное доказательство изоляции на collab layer.

### `sample_insight.json`

```json
{
  "person_id": "ivan",
  "generated_at": "2026-04-24T12:00:00Z",
  "model": "opus",
  "cached": false,
  "insights": [
    "68% коммитов за 2 недели — ночные (после 22:00), против baseline 15% три месяца назад.",
    "55% коммитов содержат 'fix', 'revert', 'hotfix' — человек второй месяц тушит пожары вместо фич.",
    "Ноль co-authored коммитов за 2 недели при baseline 4/нед — социальная изоляция в команде."
  ],
  "actions": [
    "Провести 1:1 сегодня до 18:00, фокус на нагрузке (не на конкретных задачах).",
    "Перераспределить 2 таска с критическим приоритетом на Тома (overload 0.55, справится).",
    "Организовать knowledge-sharing сессию по auth-модулю — одновременно снижает bus factor и возвращает Ивана в команду."
  ]
}
```

### `sample_person.json`

```json
{
  "id": "ivan",
  "name": "Ivan Petrov",
  "role": "Senior Backend Engineer",
  "avatar_url": "https://i.pravatar.cc/150?u=ivan",
  "status": "red",
  "overload_score": 0.82,
  "signals": {
    "night_commits_ratio": 0.68,
    "fix_revert_ratio": 0.55,
    "commit_tone_delta": -0.71,
    "pr_review_lag_hours": 38.0,
    "bus_factor": 0.78,
    "co_author_isolation": 1.0,
    "weekend_activity": 0.4
  },
  "mock_signals": {
    "slack_silence_days": 3,
    "velocity_delta": -0.4,
    "back_to_back_meetings_pct": 0.7
  },
  "neighbors": ["maria"],
  "recent_events_count": 47
}
```

---

## Как агенты используют контракты

- **Agent A** читает §SQLite, §Event, §Environment → реализует ingest + db.py
- **Agent B** читает §Signal contract, работает против `data/samples/sample_events.jsonl`
- **Agent C** читает §Graph, §API → реализует graph + FastAPI routes, работает против sample_events
- **Agent D** читает §LLM, §Cache, §API (insights/action) → работает против `sample_graph.json`
- **Agent E** читает §API + `sample_graph.json` + `sample_insight.json` → пишет UI
- **Agent F** читает весь файл → генерит `data/samples/*` и `seed_demo.py`

**Правило:** если агенту нужно изменение контракта — **пишет PR в CONTRACTS.md** с комментарием "proposed by agent X", orchestrator апрувит или отклоняет.
