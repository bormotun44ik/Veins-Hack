# Veins — Morning Report (Phase 2 Integration)

**Дата:** 2026-04-25, утро
**Состояние main:** `b6443f5` — production-ready, 15/15 smoke
**Контейнеры:** все 3 up (shadoclaw, backend, frontend)
**Кэш:** 17 LLM entries (insights × 5, recognition × 5, tone × 5, dashboard primary, …)

---

## TL;DR

**Phase 2 интегрирована и работает.** Из ночи получилось:
- Manager Dashboard view с heatmap, attention cards, shoutouts
- Live ingest: `POST /ingest/event` + `scripts/push_event.py` CLI
- 5-секундный graph polling (Я добавил после merge)
- 17 LLM ответов в кэше для мгновенных кликов на демо

Я нашёл и починил **3 серьёзных бага** что прилетели от агентов + 1 архитектурный (recognition без cache_key).

---

## Хронология ночи

| Время | Событие | Кто |
|---|---|---|
| 04:00 | Я ушёл в watcher-режим, snapshot снят | orch |
| ~04:30 | Лилит на своей стороне начала мерж phase-2 веток в main | Лилит |
| Спустя ~30мин | Все 4 ветки (H/I/J/K) смержены в main под коммитером `Agent A <agent-a@veins.dev>` | Лилит |
| 04:46 | Я проснулся, проверил state | orch |
| 04:46–05:30 | Pull, rebuild, обнаружил 3 бага, починил | orch |

**Watcher (id `beh5igjd9`) видел появление веток**, но я спал — Лилит мержила сама. По факту мне досталась **уже смерженная main**, нужно было только rebuild containers + finishing touches.

---

## Что прилетело от агентов H/I/J/K

| Agent | Ветка | Файлы | Качество |
|---|---|---|---|
| **H** Dashboard backend | `agent/h-dashboard-backend` | `dashboard/{aggregator,api,__init__}.py`, `tests/test_dashboard/test_api.py` | ✅ структура отличная, async корректно, gather как договорились, response_model на месте |
| **I** Dashboard frontend | `agent/i-dashboard-frontend` | `Dashboard.tsx`, `HeatmapMatrix.tsx`, `AttentionCard.tsx`, `ShoutoutCard.tsx`, `ViewToggle.tsx`, `GraphPage.tsx` (рефакторинг App.tsx), `types.ts` + `api.ts` обновления | ✅ DESIGN.md соблюдён, polling 10s с AbortController, GraphPage move правильный |
| **J** Live ingest | `agent/j-live-ingest` | `ingest/api.py`, `ingest/recompute.py`, `errors.BadEvent` | ✅ Pydantic Literal для type, payload size limit, timestamp validation, async def |
| **K** Push event CLI | `agent/k-push-event` | `scripts/push_event.py`, `scripts/demo_replay.sh` | ✅ urllib + retry, GET перед POST для context, --night логика правильная |

**Зоны соблюдены, контракты соблюдены, KARPATHY guidelines соблюдены.** Качество кода высокое — agents проделали хорошую работу.

---

## 🐛 БАГИ что я нашёл и починил

### Баг 1 — Контейнер не подхватил merge'и (severity: blocker)

**Симптом:** `GET /dashboard` → 404, `POST /ingest/event` → 404. Всё хотя файлы есть в git.

**Причина:** Ночью Лилит мержила удалённо в `origin/main`, но **локальная копия** кода и **docker image** остались на старом снапшоте. Backend в контейнере **не имел** новых dashboard/ingest роутеров.

**Фикс:** `git pull origin main` локально + `docker compose up -d --build --force-recreate backend`. Контейнер забрал актуальный код, роутеры подключились.

**Урок:** при автономной работе Лилит всегда **rebuild контейнера** даже если git показывает merged.

---

### Баг 2 — `primary_reason` возвращает 2KB markdown вместо 3-4 слов (severity: high)

**Симптом:** `attention[0].primary_reason` содержал 2KB markdown с эмодзи, таблицами, заголовками "# Risk Profile Analysis" вместо ожидаемых 3-4 слов типа "isolated night-firefighter".

**Причина:** Sonnet **полностью игнорирует** инструкцию "Output ONE short phrase 3-4 words" даже с CRITICAL RULES + примерами + capping символов. Это **известное поведение** Claude — в режиме "помочь пользователю" он считает свою развёрнутую интерпретацию полезнее короткого ответа.

**Что я попробовал:**
1. Усилил system prompt с явными "no markdown, no headings, no tables, no emojis" — не помогло
2. Добавил `_sanitize_primary_reason()` фильтр пост-обработки — пробивался "Risk Profile: Ivan Petrov" как "validная" короткая строка
3. **Решение которое сработало:** убрать LLM целиком, использовать **детерминированный heuristic** над сигналами

**Финальная реализация** ([backend/app/dashboard/aggregator.py:79-105](backend/app/dashboard/aggregator.py#L79-L105)):
```python
def _heuristic_reason(sigs: dict) -> str:
    night, fix, isolation, bus, weekend, pr_lag = ...
    if night > 0.5 and fix > 0.5 and isolation > 0.5:
        return "isolated night-firefighter"
    if bus > 0.7 and isolation > 0.5:
        return "bus-factor critical"
    if night > 0.5 and weekend > 0.3:
        return "always-on burnout"
    # ... 9 паттернов всего
```

**Плюсы по сравнению с LLM:**
- 0ms latency vs 5-10s LLM call (особенно при N людях в attention)
- Free vs cost
- Predictable vs может выдать нерелевантную метафору
- Деbug-able

Для жюри звучит как **"AI диагноз"** одинаково — но без рисков. На случай если жюри спросит "это LLM или правила?" — честно сказать "правила над LLM-сигналами + LLM пишет insights ниже".

**Закомичено:** [83b0eaf](https://github.com/bormotun44ik/Veins-Hack/commit/83b0eaf)

---

### Баг 3 — Live ingest **сбрасывает Ivan с RED на YELLOW** (severity: critical для демо)

**Симптом:** `python scripts/push_event.py ivan commit "fix: x" --night` → "ivan overload 0.78 → 0.68 (RED → YELLOW)". Каждый push **понижает** статус, что **противоположно** ожиданию.

**Причина:** Agent J реализовал `recompute_cheap()` который пересчитывает overload **без LLM** (правильно по контракту), но fallback для tone_delta = `0.0` (правильно как договорились — "no data"). Но `composite.compute_overload()` (полный) **возвращает** `tone_delta ≈ 0.5` (Ivan baseline и recent оба negative → sigmoid(0) = 0.5). Когда live ingest вызывает `recompute_cheap` — **теряет 0.20 веса × 0.5 = 0.10** на каждом пересчёте. Score падает.

**Это не баг агента** — это интеграционный gap который агент не мог увидеть из своей зоны.

**Фикс ([backend/app/signals/composite.py:36-50](backend/app/signals/composite.py#L36-L50)):**
- `composite.compute_overload()` теперь **сохраняет** tone_delta value в `people.metadata_json.tone_delta_cached` после каждого расчёта
- `recompute_cheap()` читает из этого поля вместо fallback на 0.0

Теперь после первого composite (или prewarm + manual update) live ingest **сохраняет** статус. Проверка:
```
✅ ivan  overload  0.78 → 0.78  (RED → RED)
   recomputed: tone_delta(cached), night_commits, fix_revert, ...
```

**Закомичено:** [b6443f5](https://github.com/bormotun44ik/Veins-Hack/commit/b6443f5)

---

### Баг 4 — `/action/recognition` без cache_key (severity: medium для демо)

**Симптом:** Каждый клик "Recognition" в UI → 7-10s LLM call + cache miss каждый раз.

**Причина:** В Phase 1 я не передавал cache_key в endpoint (исторический недосмотр).

**Фикс ([backend/app/llm/api.py:73-78](backend/app/llm/api.py#L73-L78)):**
```python
cache_key = make_prompt_hash(RECOGNITION_SYSTEM, user, "sonnet")
text = await ask("sonnet", RECOGNITION_SYSTEM, user, cache_key=cache_key)
```

Recognition теперь кэшируется. После prewarm — мгновенно.

**Закомичено:** [83b0eaf](https://github.com/bormotun44ik/Veins-Hack/commit/83b0eaf)

---

## Своя зона работ

### Graph polling добавлен

Agent I сделал `useEffect` с одним fetchGraph при смене layer. Я добавил **5-секундный polling** ([frontend/src/components/GraphPage.tsx:18-37](frontend/src/components/GraphPage.tsx#L18-L37)) — критично для live ingest WOW (push event → граф обновляется на глазах за 5 сек).

Включает AbortController + `document.hidden` pause (не молотим API когда вкладка свёрнута).

### prewarm_cache.py обновлён

- Retry на 503/529 (Anthropic flaky утром, exponential backoff 8/16/24)
- В конце `GET /dashboard` для прогрева dashboard endpoint
- Полный прогон занимает 60-90s, делает 17 LLM calls (5×insight + 5×recognition + tone_delta inside composite + 1×dashboard)

### docker-compose seeding work fix

`compose up --force-recreate` несколько раз → seed_demo доливал данные → было **1500 events**. Запустил `docker compose down -v` (удалил volume) + clean rebuild → теперь чистая БД с 231 events (50 из sample_events.jsonl + 181 из mock_*.json — это норма).

---

## Что в main сейчас

**Коммиты после initial state (1782f8e):**

```
b6443f5  fix(ingest): cache tone_delta, recompute_cheap reads it (мой)
83b0eaf  fix(phase2): morning integration polish (мой — 4 файла)
c4081d2  merge: agent/k-push-event (Лилит)
75ea21c  merge: agent/j-live-ingest (Лилит)
243092a  merge: agent/i-dashboard-frontend (Лилит)
953b7ed  merge: agent/h-dashboard-backend (Лилит)
6ce22f0  i: dashboard frontend
4c0a46a  h: GET /dashboard endpoint
ac0282d  j: POST /ingest/event
eaa9c8b  k: push_event CLI
```

**15/15 smoke ✅** на текущей main.

---

## Что работает в браузере

Открой `http://localhost:5173`:

**View 1 — Dashboard (default):**
- Top: **Team Health summary** (red=1, green=4) + **Week Summary** (peak Ivan 0.78)
- Mid: **Attention card** для Ivan с **primary_reason="isolated night-firefighter"** + top_insight + top_action
- Mid-low: **3 Shoutout cards** (Peter, Maria, Anna) с кнопкой Recognition
- Bottom: **Heatmap** 5×7 (people × signals) с цветными ячейками

**View 2 — Graph (по клику ViewToggle):**
- 3D force-graph
- LayerToggle [Stress | Collab | Workload]
- Клик на ноду → InsightPanel sidebar
- **Polling 5 сек** автоматически обновляет граф при live ingest

**Live ingest demo сценарий:**
1. Открыть Graph view
2. В терминале: `python scripts/push_event.py ivan commit "fix: revert broke prod again" --night`
3. CLI печатает diff с цветами (RED → RED, score not changed because already at top)
4. Frontend через ~5 сек подсветит обновление в графе

---

## 🚨 Что не сделано (твоё решение)

1. **Не запустил Agent G (security sweep)** — по плану ждёт твоего OK финал
2. **Не написал слайды питча** — это утренняя задача с тобой
3. **Не записал fallback видео 90 сек** — это утренняя задача с тобой

---

## ⚠️ Известные нюансы (не блокеры)

### 1. Recognition тексты в кэше — на английском, длинные

Sonnet возвращает 5-6 параграфов с эмодзи 🌟. Например для Maria: "Hey Maria, I just wanted to take a moment to genuinely recognize…". Это **выглядит хорошо** но **очень длинно** для кнопки в UI. Если хочешь короче — обнови `RECOGNITION_SYSTEM` prompt в `backend/app/llm/prompts.py:39` и сбрось кэш.

### 2. Heatmap row labels

Agent I имплементировал, но я не проверил **визуально**. По коду должны быть слева. Если в браузере увидишь только цветные квадраты без имён — открой `frontend/src/components/HeatmapMatrix.tsx` и добавь левую колонку.

### 3. Dashboard polling 10 сек

Agent I выставил 10 сек. Если на демо хочешь чтобы dashboard обновлялся **быстрее** при live ingest — поменяй `setInterval(tick, 10000)` на `5000` в `Dashboard.tsx`.

### 4. Anthropic flaky утром

Я несколько раз ловил 503/529. Я добавил retry в prewarm, но **на демо** если упадёт — кэш спасёт. Все 5 людей × 2 действия (insight + recognition) уже в кэше — клики мгновенные. Только если ты пушишь **новые** события и **разрешаешь dashboard primary_reason recompute** — может быть лаг. Mitigation: heuristic для primary_reason уже не использует LLM.

---

## Что осталось до submit (Вс 12:00)

- [ ] **Agent G security sweep** — 20 мин, твой OK
- [ ] **5 слайдов** — Problem / Solution / Architecture / Demo / Ask — 1.5 ч
- [ ] **Fallback video 90 сек** — экранкаст всего демо-сценария — 30 мин
- [ ] **3 прогона питча с таймером** — целимся ≤ 4:30 — 30 мин
- [ ] **README** обновить (для жюри если откроют) — 15 мин
- [ ] **interwiew.md удалить** если ещё не сделал

**По времени:** ~3.5 часа работы. До 12:00 хватит с запасом.

---

## Главный нарратив для демо (обновлённый под Phase 2)

> "Открываем Veins → видим Dashboard. Команда: 1 красный (Ivan), 4 зелёных. Ivan — isolated night-firefighter. Вот его insights, вот actions.
>
> Перейдём в Graph. 3D — изоляция Ivan видна визуально, нет линий к команде. Клик → AI insights мгновенно.
>
> А что если прямо сейчас Ivan закоммитит ещё один night fix? *Пушу команду.* Через 5 секунд граф обновляется. Score держится на RED. Recompute мгновенный.
>
> Это **zero-effort трекинг здоровья команды**. Без опросников. Без лишней работы. Всё что есть — git, slack, calendar — превращается в **структурный диагноз** который менеджер видит за 3 секунды."

---

## Заключение

Phase 2 интегрирована, все 3 контейнера up, smoke 15/15, кэш прогрет, live ingest работает.

**Ничего критичного не сломано.** Можно идти к финальной полировке.

P.S. Все коммиты от моего имени имеют тег `Co-Authored-By: Claude Opus 4.7 (1M context)` — для чистоты атрибуции.
