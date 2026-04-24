# Veins-Hack — Launch Playbook

> **Читают это:** ты (bormotun), Лилит, orchestrator (Claude Code локальный).
> **Назначение:** синхронизация момента "всё готово → жмём старт → погнали".

---

## 🚦 Pre-launch checklist (ты делаешь перед тем как Лилит запустит агентов)

### 1. Инфраструктура на твоей машине

- [ ] **ShadoClaw запущен** на `127.0.0.1:8317`
  ```bash
  cd <path-to-shadoclaw-no-restricts>
  npx openclaw login          # один раз, сохранит OAuth токен
  OPENCLAW_STRIP_SYSTEM=1 npx openclaw serve
  ```
  Проверка: `curl http://127.0.0.1:8317/health` → 200 OK

- [ ] **`.env` создан** из `.env.example`:
  ```bash
  cd /home/bormotun/Code/Veins-Hack
  cp .env.example .env
  # отредактируй:
  #   GITHUB_TOKEN=ghp_actual-token  (с доступом к veeins-test репо)
  #   (Groq ключи уже внутри — или замени на новые если ревочил)
  ```

- [ ] **GitHub репо `bormotun44ik/veeins-test` создан** (пустой ОК — Agent F запушит историю).

- [ ] **Docker есть и работает**: `docker --version && docker compose version`

- [ ] **worktree директория существует или создаётся легко**:
  ```bash
  mkdir -p /home/bormotun/Code  # уже должна быть
  ```

### 2. Безопасность (опциональные фиксы до старта)

- [ ] **Groq keys leak** (решение твоё):
  - Вариант A: revoke старые 5 ключей в Groq Console → выпустить новые → `.env` обновить → force-push чистой истории
    ```bash
    git filter-repo --replace-text <(echo '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=gsk_REVOKED')
    # (повторить для каждого; либо BFG)
    git push --force origin main
    ```
  - Вариант B: не фиксить (free tier, "пох")
    → Agent G при sweep пометит это как 🟢 Low (ты принял решение)

- [ ] **interwiew.md удалить** (если сохранил на мобилу):
  ```bash
  rm interwiew.md
  git add -A && git commit -m "remove interwiew scratch note"
  git push origin main
  ```

### 3. Финальный smoke

- [ ] `git log --oneline -5` — последний коммит твой или Лилит (ок)
- [ ] `git status` — working tree clean
- [ ] Orchestrator (Claude Code local) знает что стартуем

---

## 🚀 Launch: сообщение для Лилит

Когда чеклист выше зелёный — Лилит получает ОДНО сообщение:

```
Стартуем агентов Veins-Hack.

Репо: https://github.com/bormotun44ik/Veins-Hack (main, up-to-date)
Читай: AGENT_TASKS.md в корне репо — 6 готовых промптов.

ПОРЯДОК ЗАПУСКА:
  1. Agent F (Fixtures) — СРАЗУ, приоритет. Без него sample_*.json для остальных нет.
  2. Через 15 минут после F — Agent A (Ingest+DB).
  3. Параллельно с A (сразу же, против samples):
     Agent B (Signals), Agent C (Graph+API), Agent D (LLM+RAG), Agent E (Frontend)

  Agent G (Security) — НЕ ЗАПУСКАТЬ. Orchestrator сам запустит после merge всех в main.

Каждый агент:
  • Работает в отдельном git worktree (см. preамбулу в AGENT_TASKS.md)
  • Пушит в ветку agent/<letter>-<name>
  • Отчитывается DONE/BLOCKED/CHANGED/NEXT после каждого push
  • НЕ трогает main, НЕ трогает чужие зоны, НЕ меняет CONTRACTS.md

Orchestrator (Claude Code local) мержит ветки в main через PR.

Ключевые факты для всех агентов:
  • ShadoClaw: 127.0.0.1:8317 (docker: host.docker.internal:8317), auth не нужен
  • GitHub: veeins-test (живой), GITHUB_TOKEN в .env
  • Groq: 5 ключей round-robin в .env

Поехали.
```

---

## 🎛 Orchestrator playbook (что я делаю после старта)

### Каждые 15-20 минут:
```bash
cd /home/bormotun/Code/Veins-Hack
git fetch --all --prune
git branch -a | grep agent/
```

### Когда вижу новую ветку / push:

1. **Читаю отчёт** агента (Лилит перенаправит или я найду в коммит-message)
2. **Checkout branch локально** в worktree:
   ```bash
   git worktree add ../veins-review-<X> agent/<X>-<name>
   cd ../veins-review-<X>
   ```
3. **Quick review:**
   - код в правильной зоне? (да/нет)
   - контракт соблюдён? (проверяю по CONTRACTS.md)
   - тесты прошли? (`pytest` для backend, `npm run build` для frontend)
4. **Если ОК → merge в main:**
   ```bash
   cd /home/bormotun/Code/Veins-Hack
   git merge --no-ff agent/<X>-<name> -m "merge: agent <X> — <short>"
   git push origin main
   ```
5. **Если не ОК** → пишу Лилит "agent X вернуть на доработку: <причина>"

### Конфликты:
- **Общие файлы** (requirements.txt, package.json, docker-compose.yml):
  - Если два агента добавили разные пакеты → мерж руками, оставляю обоих
  - Если конфликт логики → выбираю в пользу агента чья зона основная
- **Контракт-конфликт** (агент поменял что-то общее):
  - СТОП. Читаю предложение. Решаю ДА/НЕТ. Обновляю CONTRACTS.md если ДА.
  - Пишу всем затронутым агентам "перечитайте CONTRACTS §X, подтяните".

### Smoke test каждые 3 часа:
```bash
./scripts/smoke_test.sh   # Agent F создаст; пока нет — curl'ы вручную
docker compose up --build -d
sleep 5
curl -f localhost:8000/health || echo "BACKEND DOWN"
curl -f localhost:8000/graph?layer=stress || echo "GRAPH DOWN"
curl -f localhost:5173 || echo "FRONTEND DOWN"
```

### Integration hour (Сб ~18:00):
1. Все ветки смержены
2. `docker compose up --build`
3. Проход полного demo-сценария от начала до конца
4. Фиксим что сломалось на стыках (ВРУЧНУЮ, не агентами)
5. `scripts/prewarm_cache.py` — прогрев Claude кэша для демо

### Agent G (Security, Сб ~21:00):
- Когда orchestrator уверен что main стабилен → запускаю Agent G
- Он читает весь main, пишет SECURITY_REPORT.md
- Critical → фиксим сразу, Medium → по времени, Low → в отчёт

---

## 📋 Интеграционные точки — где ломается

Места где агенты соприкасаются и могут рассинхрониться:

| Стык | Кто ↔ Кто | Что проверяю при merge |
|---|---|---|
| DB schema | A → B, C, D | SQLite таблицы соответствуют CONTRACTS.md §SQLite |
| FastAPI routers | C ↔ D | `main.py` include_router без ImportError |
| signals.*.compute() | B → C, D | Сигнатура `(person_id, conn) → float`, none > 1.0 |
| llm.client.ask() | D → B | Не меняет сигнатуру, возвращает str |
| /graph JSON shape | C → E | Совпадает с sample_graph.json |
| /insights JSON shape | D → E | Совпадает с sample_insight.json |
| Event payload types | A → B | Поля payload совпадают с CONTRACTS.md §Event |

---

## 🛑 Стоп-сигналы

Orchestrator **НЕ** мержит в main если:

- ❌ Агент вышел за пределы своей зоны (писал в чужую папку)
- ❌ Агент изменил CONTRACTS.md, ARCHITECTURE.md или PLAN.md
- ❌ Backend тесты красные без объяснения
- ❌ Frontend `npm run build` падает
- ❌ Хардкод секретов в коде (Groq ключи, токены и т.п. в .py/.ts файлах)
- ❌ Критичная зависимость добавлена в requirements.txt / package.json без согласования

Любой из этих — **возврат агента на доработку**. Пишу Лилит, ждём фикс, повторный review.

---

## 🎯 Definition of Done для всего проекта

К Воскресенью 12:00 (submit):

- [ ] `docker compose up --build` поднимается за < 30 сек
- [ ] `curl localhost:8000/health` → 200
- [ ] `curl localhost:8000/graph?layer=stress` → 5 Person нод, overload правильный
- [ ] `curl localhost:8000/graph?layer=collab` → co_authored + reviews_pr рёбра
- [ ] `curl localhost:8000/graph?layer=workload` → Task ноды + assigned_to
- [ ] `curl localhost:8000/person/ivan` → signals + neighbors заполнены
- [ ] `curl localhost:8000/insights/ivan` → JSON с 3 insights + 3 actions, cached=true
- [ ] `localhost:5173` — 3D граф рендерится, layer toggle работает, клик → panel
- [ ] SECURITY_REPORT.md: 0 Critical
- [ ] prewarmed cache для 5 людей × 3 задачи (insight/recognition/action)
- [ ] fallback-видео 90 сек записано
- [ ] 5 слайдов подготовлены, питч прогнан 3 раза ≤ 4:30

---

**Когда этот документ весь зелёный — жюри видит то, что менеджер не замечает.**
