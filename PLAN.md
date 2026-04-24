# Veins — План хакатона (48 часов)

> AI система которая видит то, что менеджер не замечает.
> Собирает сигналы из GitHub/Jira/Slack/Zoom → Knowledge Graph → GraphRAG + Claude → конкретные действия.

---

## 🎯 Problem Statement (30 сек для жюри)

**71% менеджеров чувствуют ответственность за wellbeing команды — но только половина реально что-то делает.**
Не потому что не хотят. Потому что **не видят**.

Burnout, overload, токсичные паттерны копятся незаметно — пока человек не уволился.

> Источник: Reward Gateway Wellbeing Report 2025

---

## 💡 Решение

**Veins** — zero-effort система мониторинга команды:
- Ноль опросников
- Ноль лишних действий от сотрудников
- Менеджер получает **что именно сделать прямо сейчас**

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────┐
│           ИСТОЧНИКИ ДАННЫХ              │
│  GitHub → коммиты, время, частота       │
│  Jira   → задачи, дедлайны, velocity    │
│  Slack  → сообщения, тон, время         │
│  Zoom   → транскрипция созвонов         │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│         ОБРАБОТКА ДАННЫХ                │
│  Groq Whisper → транскрипция (free)     │
│  Gemini embed → векторы (pre-computed)  │
│  Claude       → sentiment + tone delta  │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│         KNOWLEDGE GRAPH (NetworkX)      │
│  Ноды:  Person, Repo, Task, Meeting     │
│  Рёбра: commits_to, co_authored,        │
│         reviews_pr, assigned_to,        │
│         attended                        │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│         GraphRAG + Claude API           │
│  Only relevant nodes → no hallucination │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│         ДАШБОРД МЕНЕДЖЕРА               │
│  🟢 / 🟡 / 🔴  статусы                  │
│  AI инсайты + one-click actions         │
└─────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Слой           | Технология                                                       |
| -------------- | ---------------------------------------------------------------- |
| Backend        | Python 3.11 + FastAPI                                            |
| Graph          | NetworkX (хакатон) / GraphWise API (в питче — prod integration)  |
| Frontend       | **Vite + React** + Tailwind                                      |
| Viz            | **`react-force-graph-3d`** (wow, fallback → `-2d` за 10 мин)     |
| Speech-to-text | **Groq Whisper** (free tier, быстро) + hardcoded speaker_id      |
| Embeddings     | Gemini `text-embedding-004` через OpenRouter, pre-computed       |
| Embed backup   | Google AI Studio ключ (на случай если OpenRouter ляжет)          |
| Vector search  | **numpy + cosine similarity** (питчим как "sqlite-vec")          |
| LLM proxy      | **ShadoClaw** — личный wrapper, live-демо идёт через него        |
| LLM — insights | Claude **Opus 4.7** (1-2 запроса на демо, качество критично)     |
| LLM — bulk     | Claude **Sonnet 4.6** (commit tone × 500, sentiment в Slack)     |
| LLM — pipeline | Claude **Haiku 4.5** (дешёвый pre-compute, если нужен)           |
| DB             | SQLite (people, events, edges, chunks, cache)                    |
| Deploy         | Docker compose, локально (demo идёт с ноута)                     |

### Model strategy rationale
Разделение Opus / Sonnet / Haiku = "right model for right task" — это **питч-усилитель**. Не жги Opus на каждый чанк: дорого, медленно, и жюри это заметит.

---

## 📅 Таймлайн — по программе хакатона

### 🔴 ДО пятницы (pre-work, делаем заранее)

Всё что не требует сцены — сделать **до** регистрации:

- [ ] GitHub токен создан, fake-team репо собран (5 акков, 2 недели реалистичной истории)
- [ ] `.env` template: `SHADOCLAW_API_KEY`, `GITHUB_TOKEN`, `OPENROUTER_KEY`, `GOOGLE_AI_KEY`, `GROQ_KEY`
- [ ] Mock-файлы готовы: `mock_slack.json`, `mock_jira.json`, `mock_calendar.json`
- [ ] `meeting.mp3` → прогнать Groq Whisper → `transcript.json` committed в репо
- [ ] Dockerfile'ы + `docker-compose.yml` skeleton (пустой, но чтоб compose up не падал)
- [ ] `requirements.txt` + `package.json` с зависимостями (pre-installed)

**Почему важно:** на площадке не будет времени на "ой pyannote не ставится".

---

### 🟣 Пятница — ДЕН 1 | Start & Team Up

| Время | Что по программе | Что делаю я |
| --- | --- | --- |
| 17:30–18:30 | Регистрация + networking | Разведка: кто менторы, кто жюри, запомнить лица |
| 18:30–19:00 | Откриване | Слушаем |
| 19:00–19:30 | Партньори + правила | **Записать критерии точно** как озвучат |
| 19:30–20:15 | Представяне идей | **Питчим идею** если формат требует — готов elevator 30 сек |
| 20:15–21:00 | Кетъринг | Есть, хорошо поговорить с менторами |
| **21:00–23:00** | **Първа сесия AI hacking (2ч)** | ↓ блок 1 ↓ |

#### Блок 1 (Пт 21:00–23:00, 2ч) — Foundation

**Цель:** работающий `/graph` endpoint к 23:00.

- [ ] `git init`, структура: `backend/`, `frontend/`, `data/`
- [ ] FastAPI скелет: `/health`, `/graph`
- [ ] GitHub API → pull коммиты из fake-team репо → NetworkX
- [ ] SQLite schema (из секции ниже)
- [ ] 1 метрика работает end-to-end: `night_commits_ratio`

**После 23:00:** спать. Не геройствуй, суббота — марафон 15ч.

---

### 🟠 Суббота — ДЕН 2 | Build Day

| Время | Программа | Что делаю я |
| --- | --- | --- |
| 08:30–09:00 | Откриване + кофе | Setup рабочего места, docker up |
| **09:00–12:00** | **Втора сесия (3ч)** | ↓ блок 2 ↓ |
| 12:00–13:00 | **Срещи с ментори** | ↓ критично, готовим вопросы ↓ |
| 13:00–14:00 | Обяд | Есть, **думать не о коде** — голова отдыхает |
| 14:00–15:00 | **Workshop** | Обязательно. Слушаем, возможно полезно |
| **15:00–17:30** | **Трета сесия (2.5ч)** | ↓ блок 3 ↓ |
| **17:30–19:00** | **Checkpoint + ментори** | ↓ демо-скелет должен работать ↓ |
| 19:00–20:00 | Вечеря | Есть |
| **20:00–23:00** | **Четвърта сесия (3ч)** | ↓ блок 4 ↓ |

#### Блок 2 (Сб 09:00–12:00, 3ч) — Signals + Graph

**Цель:** все живые GitHub-сигналы + композитный overload_score.

- [ ] Все 8 live GitHub метрик (night_commits, fix_revert, tone_delta, pr_lag, bus_factor, ...)
- [ ] Парсинг mock JSON (Slack, Jira, Calendar)
- [ ] Composite `overload_score` = weighted sum
- [ ] Рёбра в графе: `commits_to`, `co_authored`, `reviews_pr`, `assigned_to`, `attended`
- [ ] `/graph?layer=stress|collab|workload` — три подмножества

#### Mentor-meeting (Сб 12:00–13:00) — готовим заранее

**3 конкретных вопроса** которые нужно успеть задать:
1. У кого из жюри **GraphWise-background** — подтвердить что GraphRAG = хук
2. Reward Gateway — показать архитектуру, спросить **какие сигналы для них самые важные** (чтобы в демо их подсветить)
3. Показать текущий граф → **спросить что wow, что скучно** → скорректировать Блок 3

#### Блок 3 (Сб 15:00–17:30, 2.5ч) — GraphRAG + Claude

**Цель:** клик на ноду → реальный инсайт от Claude.

- [ ] Gemini embeddings всех текстов → SQLite blob (можно начать в обед в фоне)
- [ ] Numpy cosine retrieval: top-K чанков + 1-hop соседей графа
- [ ] Prompt template: "сигналы + чанки + граф → 3 инсайта + 3 действия"
- [ ] Sonnet 4.6 — bulk commit tone (прогнать заранее, закэшить)
- [ ] Opus 4.7 — финальный insight endpoint `/insights/{person}`
- [ ] **Pre-warm кэш** для демо-сценария: Иван, Мария, Том

#### Checkpoint (Сб 17:30–19:00) — критическая точка

**Что показываем менторам:**
- Граф работает, 5 нод с цветами
- Клик на Ивана → Claude даёт реальный insight
- Фронт минимальный, но кликабельный

**Что спрашиваем:**
- "Понятна ли история с первого взгляда?"
- "Какой из 3 инсайтов самый сильный?"
- "Чего не хватает для WOW?"

**Если фронт не готов** — показываем curl'ы + JSON, это нормально на checkpoint.

#### Блок 4 (Сб 20:00–23:00, 3ч) — Frontend WOW

**Цель:** красивое демо к 23:00.

- [ ] Vite + React + Tailwind, single page
- [ ] `react-force-graph-3d` — граф команды (fallback `-2d` через 10 мин если кривой)
- [ ] **Three-layer toggle** (WOW):
  - 🔴 Stress — только Person, размер = overload
  - 🤝 Collaboration — рёбра `co_authored` + `reviews_pr`
  - 🚧 Workload — Task-ноды + `assigned_to`
- [ ] Sidebar: клик на ноду → insight + 3 action-кнопки
- [ ] SSE streaming Claude ответов через ShadoClaw
- [ ] Demo seed: Иван 🔴, Том 🟡, Мария+Анна+Петя 🟢

**К 23:00 обязательно:** end-to-end работает, demo-сценарий проходит от начала до конца.

**После 23:00:** **спать**, не править фичи. Воскресенье утром — только полировка.

---

### 🟢 Воскресенье — ДЕН 3 | Demo & Awards

| Время | Программа | Что делаю я |
| --- | --- | --- |
| 08:30–09:00 | Откриване | Coffee, docker up, проверить что всё работает |
| **09:00–12:00** | **Финални корекции (3ч)** | ↓ блок 5: polish only ↓ |
| **12:00** | 🛑 **DEADLINE сабмит** | Всё, коммитим, не трогаем |
| 12:00–13:00 | Обяд | Репетиция питча в голове |
| **13:00–15:30** | **Представяне (~7 мин/команда)** | ↓ демо ↓ |
| 15:30–16:15 | Оценяване | Ждать |
| 16:15–17:00 | Награждаване | 🏆 |
| 17:00–18:00 | Networking | Собрать контакты менторов, Reward Gateway особенно |

#### Блок 5 (Вс 09:00–12:00, 3ч) — Polish & Pitch

**Правило:** 09:00–11:00 полировка, **11:00–12:00 заморозка кода** и только презентация.

- [ ] 09:00–10:00 — фикс критичных багов (только то что сломает демо)
- [ ] 10:00–10:30 — записать **fallback-видео 90 сек** (страховка на случай падения)
- [ ] 10:30–11:00 — финальный pre-warm кэша для всех кнопок демо
- [ ] 11:00–11:30 — **5 слайдов**:
  1. Problem (71% RG цифра)
  2. Solution (zero-effort, one picture)
  3. Architecture (GraphRAG + Claude + Whisper)
  4. Demo → live
  5. Ask (ROI / pilot partners)
- [ ] 11:30–12:00 — **3 прогона питча** с таймером, целимся в **4:30** (buffer на Q&A)
- [ ] **12:00 — сабмит**, руки убрать от кода

#### Демо-скрипт (4:30)

1. **0:00–0:30** — problem hook (цифра RG 71%, "менеджер слеп")
2. **0:30–1:00** — solution + architecture diagram (10 сек)
3. **1:00–3:30** — **LIVE DEMO**:
   - Collaboration layer → кликаем Ивана → insight от Claude
   - Переключаем на Stress layer → показываем весь красный
   - Workload layer → видно что Иван блокирует Тома и Марию
   - Кнопка "Что делать" → 3 действия от Claude
4. **3:30–4:00** — recognition для Марии (контраст: не только плохое)
5. **4:00–4:30** — "архитектура поддерживает GraphWise prod integration, Slack/Jira live API"

---

## 🎬 Демо-сценарий (3 минуты)

1. **Граф команды** на экране — ноды с цветами, связи
2. Клик на **🔴 Иван** → AI объясняет:
   > "3 дня молчал на митингах, коммиты в 2 ночи, velocity упал на 40%"
3. Кнопка **"Что делать"** → 3 конкретных действия от Claude
4. Кнопка **"Recognition для Марии"** → готовый текст за 2 сек
5. Транскрипт митинга → кто сколько говорил + sentiment

---

## 🏆 Соответствие критериям жюри

| Критерий         | Вес | Как закрываем                                 |
| ---------------- | --- | --------------------------------------------- |
| Идея + потенциал | 30% | Реальная боль (данные RG), B2B SaaS, ROI ясен |
| AI интеграция    | 25% | GraphRAG + Whisper + Embeddings + Claude      |
| UI/UX            | 25% | Граф-визуализация + one-click действия        |
| Продукт          | 20% | Живое демо на реальных GitHub-данных          |

### Резонанс с каждым жюри

| Жюри                | Хук                                              |
| ------------------- | ------------------------------------------------ |
| Reward Gateway      | Решение главной боли из их же отчёта             |
| GraphWise (Русев)   | GraphRAG в центре архитектуры — их технология    |
| Sirma               | Глубокая AI интеграция, не просто LLM-wrapper    |
| 1ForFit             | Wellbeing = их домен                             |
| Университет         | Универсальная проблема любой команды             |

---

## 📊 Signal Catalog

### 🔴 Живые (GitHub API) — main wow-фактор

| Сигнал | Формула | Что показывает |
| --- | --- | --- |
| `night_commits_ratio` | commits 22:00-06:00 / total | работа по ночам |
| `weekend_activity` | commits/PRs на Sat/Sun | нарушение work-life |
| `fix_revert_ratio` | (`fix/bug/revert/hotfix`) / total commits | тушит пожары вместо фич |
| `commit_tone_delta` | Claude sentiment сейчас − baseline 3 мес назад | **главная фишка** — никто не делает tone-delta |
| `pr_review_lag` | avg часы от open до review | перегруз или демотивация |
| `bus_factor` | % файлов где человек единственный коммитер | риск для команды |
| `co_author_isolation` | кол-во уникальных co-authors за 2 недели | соц-изоляция |
| `pr_churn_own_code` | сколько раз правит свои же файлы за 2 недели | метание, потеря уверенности |

### 🟡 Мок (правдоподобные JSON)

| Источник | Сигналы |
| --- | --- |
| Slack | response_latency_decay, message_time_distribution, reply_to_broadcast_ratio, silence_days |
| Jira  | velocity_trend, context_switches_per_day, reassignments, overdue_tasks |
| Zoom transcript | talk_ratio, sentiment per speaker, interruption_count |
| Calendar | back_to_back_meetings, no_focus_time_hours, meetings_per_day |

### ⭐ Самый сильный для демо
**`commit_tone_delta`** — "Иван 3 месяца назад писал с положительным тоном, последние 2 недели — frustrated".
Это то что ни один HR-tool не показывает, и Claude делает это в один промпт.

---

## 🕸 Graph Schema

### Типы нод (MVP: 4 штуки)

| Нода | Ключевые поля | Зачем |
| --- | --- | --- |
| **Person** | id, name, role, avatar, overload_score, baseline_sentiment | центральные акторы команды |
| **Repo** | id, name, url | куда коммитят, где owns_file |
| **Task** | id, title, priority, status, deadline | Workload layer |
| **Meeting** | id, title, datetime, duration | talk_ratio + вовлечённость |

*В питче говорим: "Архитектура поддерживает Project, PR, Incident, Channel — добавляются в проде одним файлом."*

### Типы рёбер (MVP: 5 штук)

| Ребро | От → К | Вес | Что рассказывает |
| --- | --- | --- | --- |
| `commits_to` | Person → Repo | count, recency | базовая активность |
| `co_authored` | Person → Person | count за 2 недели | **соц-граф команды (ключевое!)** |
| `reviews_pr` | Person → Person | count, avg_lag | кто кого ревьюит, bottleneck |
| `assigned_to` | Task → Person | priority, overdue_flag | overload визуально |
| `attended` | Person → Meeting | talk_ratio, sentiment | вовлечённость |

### Three-layer viz (wow-момент демо)

Один граф, три toggle-режима — менеджер переключает и видит разные истории:

| Слой | Показывает ноды | Показывает рёбра | История |
| --- | --- | --- | --- |
| 🔴 **Stress** | только Person, размер = overload | скрыто | "кто горит" |
| 🤝 **Collaboration** | Person | `co_authored`, `reviews_pr` | "кто изолирован / кто bottleneck" |
| 🚧 **Workload** | Person + Task | `assigned_to` | "у кого завал по задачам" |

### Главный нарратив демо (по графу)

На **Collaboration view** кликаем Ивана:
- `co_authored` рёбра: **0 за 2 недели** ← изоляция видна визуально
- `owns_file` = 78% в repo X ← bus factor
- `commits_to` рёбра: все timestamps ночные
- Claude читает граф: **"Иван изолирован + единственный владелец критичного кода + работает по ночам = classic pre-burnout"**

Это тот структурный диагноз, который не даст ни один HR-tool.

---

## 🚧 Risk register

| Риск                              | Mitigation                                           |
| --------------------------------- | ---------------------------------------------------- |
| Whisper в live медленный          | Прогнать через Groq заранее → `transcript.json` в репо |
| Claude API лимиты на демо         | ShadoClaw проксирует, кэш частых запросов в SQLite   |
| ShadoClaw упал во время демо      | Pre-warmed кэш ответов для демо-сценария             |
| **3D граф глючит / тяжёлый**      | Fallback на `react-force-graph-2d` — API идентичный, 10 мин |
| react-force-graph лагает >50 нод  | Ограничить демо 5-7 нодами                           |
| Gemini embed API лимит            | Google AI Studio ключ как backup, всё равно pre-computed |
| OpenRouter ляжет                  | Прямой Google AI Studio ключ                         |
| Slack/Jira/Teams API — auth долгий| Всё mock JSON, живой только GitHub                   |
| Сеть на площадке упала            | Fallback видео 90 сек + локальный кэш                |
| GitHub токен/репо не готовы       | Собрать fake-team репо заранее (5 акков, 2 недели истории) |
| GraphWise интеграция не успеем    | Упоминаем архитектурно — "prod integration ready"    |

---

## 🎯 MVP scope (если горит время)

**Must have** (без этого не демо):
- GitHub live → граф
- 3 живые метрики: `night_commits_ratio`, `fix_revert_ratio`, `commit_tone_delta`
- Claude инсайты по человеку (через ShadoClaw)
- Дашборд со светофором + force-graph

**Should have:**
- One-click actions (что делать / написать / recognition)
- Slack mock + response_latency_decay
- Jira mock + velocity trend
- Groq Whisper транскрипт (pre-computed)

**Nice to have:**
- Calendar mock (back-to-back meetings)
- Talk ratio на митинге из транскрипта
- Co-author network / bus factor визуализация

---

## 📂 Структура репо

```
Hackaton/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── graph/               # NetworkX logic + 3-layer builders
│   │   ├── ingest/              # github.py, slack.py, whisper.py, jira.py
│   │   ├── signals/             # night_commits, tone_delta, bus_factor, ...
│   │   ├── rag/                 # embeddings + numpy cosine retrieval
│   │   └── llm/                 # ShadoClaw client + prompts (opus/sonnet/haiku)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Vite + React
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── GraphView.tsx    # react-force-graph-3d
│   │   │   ├── LayerToggle.tsx  # Stress / Collab / Workload
│   │   │   └── InsightPanel.tsx # Claude stream + actions
│   │   └── api.ts
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── data/
│   ├── mock_slack.json
│   ├── mock_jira.json
│   ├── mock_calendar.json
│   ├── meeting.mp3
│   └── transcript.json          # pre-computed через Groq Whisper
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 💾 SQLite schema

```sql
people (
  id TEXT PRIMARY KEY,
  name TEXT,
  role TEXT,
  overload_score REAL,
  baseline_sentiment REAL
)

events (                       -- все сырые сигналы: commit, slack msg, meeting, task
  id INTEGER PRIMARY KEY,
  person_id TEXT,
  type TEXT,                   -- 'commit' | 'slack_msg' | 'meeting' | 'task' ...
  timestamp DATETIME,
  payload_json TEXT
)

edges (                        -- knowledge graph edges
  id INTEGER PRIMARY KEY,
  src TEXT, dst TEXT,
  type TEXT,                   -- 'commits_to' | 'co_authored' | 'reviews_pr' | 'assigned_to' | 'attended'
  weight REAL,
  metadata_json TEXT
)

chunks (                       -- текст для retrieval
  id INTEGER PRIMARY KEY,
  source_type TEXT,            -- 'commit_msg' | 'slack_msg' | 'transcript_seg'
  source_id TEXT,
  person_id TEXT,
  text TEXT,
  embedding BLOB               -- numpy array, cosine search
)

cache (                        -- 🛟 страховка демо
  prompt_hash TEXT PRIMARY KEY,
  response TEXT,
  model TEXT,
  created_at DATETIME
)
```

---

## ✅ Definition of Done (к 12:00 воскресенья)

1. `docker compose up` запускает всё < 30 сек
2. Клик на красную ноду → инсайт появляется < 5 сек (из кэша)
3. Three-layer toggle переключается плавно
4. Pre-warmed кэш покрывает полный демо-сценарий офлайн
5. Fallback-видео 90 сек записано и на ноуте
6. 5 слайдов готовы, питч прогнан 3 раза, укладывается в 4:30
7. README.md в репо (2 абзаца: что это + как запустить)

---

## 🗓 Ключевые дедлайны (по порядку)

| Время | Что должно быть готово |
| --- | --- |
| **Пт 23:00** | `/graph` endpoint, одна метрика end-to-end |
| **Сб 12:00** | Все сигналы, граф + рёбра, готов к ментор-встрече |
| **Сб 17:30** | Claude insights работают, готов checkpoint demo |
| **Сб 23:00** | **Full end-to-end**: фронт + 3 layer + клик + insight |
| **Вс 11:00** | Кодинг заморожен, fallback-видео записано |
| **Вс 12:00** | 🛑 Submit. Hands off. |
| **Вс ~13:30** | Демо на сцене, ~4:30 чистыми |

---

## 🤖 Implementation Plan — параллельные субагенты

### Философия

Один человек + 12 часов = невозможно реализовать полный план.
Один человек + 12 часов + **5-7 параллельных Claude-субагентов с правильной изоляцией** = реально.

**Ты = orchestrator.** Не кодишь руками. Ты:
1. Спавнишь агентов с чёткими ТЗ
2. Читаешь их отчёты
3. Делаешь интеграцию / merge / code review
4. Разруливаешь конфликты контрактов
5. Принимаешь решения по трейдофам

Агенты **не коммитят** в main напрямую. Каждый работает в `isolation: "worktree"` либо в своей изолированной папке, ты mergeишь.

---

### 🔑 Pre-flight: Contracts (Пт 21:00–21:30, 30 мин)

**Критично сделать ПЕРЕД запуском агентов.** Контракты = интерфейсы между модулями. Если их нет — агенты будут писать несовместимые вещи.

Создать `CONTRACTS.md`:

```markdown
## Event schema (SQLite events table)
{
  "id": int,
  "person_id": str,
  "type": "commit" | "slack_msg" | "meeting" | "task" | "pr" | "review",
  "timestamp": ISO8601,
  "payload": {...type-specific}
}

## Graph node types
Person: {id, name, role, avatar_url, overload_score, baseline_sentiment}
Repo:   {id, name, url}
Task:   {id, title, priority, status, deadline}
Meeting:{id, title, datetime, duration}

## Graph edge types
commits_to:   Person → Repo    {count, recency, night_ratio}
co_authored:  Person → Person  {count, last_date}
reviews_pr:   Person → Person  {count, avg_lag_hours}
assigned_to:  Task → Person    {priority, overdue}
attended:     Person → Meeting {talk_ratio, sentiment}

## API endpoints (FastAPI)
GET  /health                    → {status: "ok"}
GET  /graph?layer=stress|collab|workload  → {nodes: [], links: []}
GET  /person/{id}               → full person context
GET  /insights/{person_id}      → {insights: [str], actions: [str]}
POST /action/recognition/{id}   → {text: str}

## Signal contract (backend/signals/*.py)
def compute(person_id: str, db: Connection) -> float  # 0.0 to 1.0

## LLM contract (backend/llm/client.py)
async def ask(model: "opus"|"sonnet"|"haiku", prompt: str, cache_key: str) -> str
```

**Правило:** никто не меняет `CONTRACTS.md` без твоего согласия. Агент может **предложить** изменение → ты апрувишь → обновляешь файл → всем агентам говоришь "pull контракт".

---

### 🎯 Треки работы

#### Track A — Data Ingestion
**Папка:** `backend/ingest/`
**Файлы:** `github.py`, `slack.py`, `jira.py`, `calendar.py`, `whisper.py`
**ТЗ:**
- Читать GitHub live через API (коммиты, PR, reviews, co-authors за 14 дней)
- Парсить `data/mock_slack.json`, `mock_jira.json`, `mock_calendar.json`
- Загрузить Groq-транскрипт `data/transcript.json`
- Всё нормализовать под **Event schema** → writer в SQLite `events` table
**Не трогает:** графы, сигналы, UI
**Контракт input:** .env с токенами, data/ файлы
**Контракт output:** SQLite events table заполнена

#### Track B — Signals
**Папка:** `backend/signals/`
**Файлы:** `night_commits.py`, `fix_revert.py`, `tone_delta.py`, `pr_lag.py`, `bus_factor.py`, `co_isolation.py`, `weekend.py`, `composite.py`
**ТЗ:**
- Каждый сигнал = отдельный файл, функция `compute(person_id, db) -> float`
- `composite.py` агрегирует все в `overload_score` через weighted sum
- `tone_delta.py` использует **Sonnet через LLM client** (см. Track D) — bulk mode
**Зависит от:** Track A (нужны events в DB)
**Контракт input:** SQLite events table
**Контракт output:** UPDATE people SET overload_score

#### Track C — Graph Builder
**Папка:** `backend/graph/`
**Файлы:** `builder.py`, `layers.py`, `api.py`
**ТЗ:**
- `builder.py` — читает events, строит NetworkX граф по **Graph node/edge types**
- `layers.py` — 3 функции `stress_layer()`, `collab_layer()`, `workload_layer()`, каждая возвращает subgraph
- `api.py` — FastAPI router `GET /graph?layer=...`
**Зависит от:** Track A (events), Track B (overload_score)
**Контракт output:** JSON graph по API-спеке

#### Track D — LLM & GraphRAG
**Папка:** `backend/llm/`, `backend/rag/`
**Файлы:** `client.py` (ShadoClaw wrapper), `prompts.py`, `context.py`, `retrieval.py`, `cache.py`
**ТЗ:**
- `client.py` — единая функция `ask()` с выбором Opus/Sonnet/Haiku + кэширование в SQLite
- `retrieval.py` — **graph-based context assembly** (без embeddings для MVP): по person_id достать 1-hop соседей + 14-day events + composite signals
- `prompts.py` — промпт-темплейты для: insight, action, recognition, commit_tone
- `cache.py` — SHA256 от prompt → response lookup
- FastAPI endpoints `/insights/{id}`, `/action/recognition/{id}`
**Зависит от:** Track C (граф готов)
**Контракт output:** JSON insights по API-спеке

#### Track E — Frontend
**Папка:** `frontend/`
**Файлы:** `src/App.tsx`, `components/GraphView.tsx`, `LayerToggle.tsx`, `InsightPanel.tsx`, `api.ts`
**ТЗ:**
- Vite + React + Tailwind setup
- `GraphView.tsx` — `react-force-graph-3d`, size по overload, цвет по статусу
- `LayerToggle.tsx` — 3 кнопки, переключают `?layer=` параметр
- `InsightPanel.tsx` — sidebar, клик по ноде → fetch `/insights/{id}`, 3 action-кнопки
- `api.ts` — клиент к FastAPI по **API endpoints** контракту
**Не зависит от:** ничего (работает с **mock backend** первые 6ч — hardcoded JSON response)
**Переключение на реальный backend:** в Сб 20:00 когда Track D готов

#### Track F — Demo fixtures
**Папка:** `data/`, `scripts/`
**Файлы:** `mock_slack.json`, `mock_jira.json`, `mock_calendar.json`, `fake_team/`, `scripts/seed_demo.py`
**ТЗ:**
- Создать **fake-team GitHub репо** программно (5 аккаунтов, 2 недели коммитов с правильными паттернами для Ивана-burnout)
- Mock Slack (50 сообщений с правдоподобной timeline)
- Mock Jira (10 задач)
- Mock Calendar (митинги)
- `seed_demo.py` — одной командой накатить всё в чистую БД
**Не зависит от:** ничего, **стартует первым**
**Контракт output:** работающие fixtures для всех остальных треков

#### Track G — Security & Review (фоновый)
**Папка:** read-only ко всему
**ТЗ:**
- Читает код в других треках по мере появления
- Ищет: command injection, SQL injection, secret leaks, открытые CORS, eval
- Flag-ит в отчёте, **не правит сам** (правит тот трек откуда баг)
- Финальный security-sweep перед сабмитом воскресенья
**Зависит от:** написанного кода
**Контракт output:** `SECURITY_REPORT.md` с findings

---

### ⏱ Расписание запуска агентов

#### Пт 21:30 (после контрактов)
Спавним **параллельно**:
- Track F (фикстуры) — блокирует все остальные, нужны mock-файлы
- Track E (frontend) — может сразу поднимать Vite + mock JSON

После 30-45 мин когда Track F отдал фикстуры:
- Track A (ingestion)

#### Сб 09:00
- Track A продолжает / завершает
- Track B (signals) — как только A отдал events
- Track C (graph) — как только B отдал overload_score
- Track E параллельно довинчивает UI без реального API

#### Сб 15:00
- Track D (LLM + RAG) — после Track C
- Track E начинает подключать реальный backend вместо мока

#### Сб 20:00 — 🔴 Integration hour
**Ты руками**, не агентами:
- Docker compose up → проверить что всё связано
- Пройти полный demo-сценарий end-to-end
- Починить что сломалось на стыках

#### Сб 21:00
- Track G (security sweep)
- Полировка UI мелкими агентами

#### Вс 09:00–11:00
- Никаких новых агентов
- Только bug fix вручную + fallback видео + слайды

---

### 📋 Orchestration rules (правила для тебя)

**1. Не запускай агента без чёткого ТЗ.**
Плохо: "сделай signals".
Хорошо: "Реализуй `backend/signals/night_commits.py`. Функция `compute(person_id, db) -> float` возвращает ratio коммитов с 22:00 до 06:00. Читает из SQLite events type='commit'. Возвращает 0.0 если коммитов < 3. Тесты в `tests/signals/test_night_commits.py`."

**2. Каждый агент отчитывается одной строкой.**
Что сделал, что сломалось, что нужно от других треков.

**3. Один агент = одна папка.**
Если агенту нужен файл из чужой папки — читает, не пишет. Пишет только свою.

**4. Конфликты контрактов → стоп.**
Если агент говорит "мне нужно поменять API" — не разрешай сам. Думай 1 мин, решай, обновляй `CONTRACTS.md`, перезапускай затронутых агентов.

**5. Isolation: worktree для рискованных задач.**
Track E (frontend), Track A (ingestion) — можно worktree. Track C, D — критический путь, держим в main для быстрой итерации.

**6. Security-агент (G) — фоновый, run_in_background: true.**
Пусть молча шуршит, периодически читаешь его отчёт.

**7. Жги лимиты без сожалений.**
Подписка у тебя есть. 10x усилитель на 48 часов = целевое использование ресурса.

---

### 🧪 Самопроверка раз в 3 часа

Каждые 3 часа — **smoke test**:
1. `docker compose up` работает?
2. `curl localhost:8000/graph` возвращает JSON?
3. Фронт открывается, граф рендерится?

Если "нет" хоть на одном пункте — **стоп новые фичи**, чинишь это. Интеграционные баги в последний час = смерть.

---

**Погнали.**
