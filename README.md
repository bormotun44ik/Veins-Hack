# Veins

> AI-система, которая видит то, что менеджер не замечает. Собирает сигналы из GitHub/Slack/Jira/Zoom → Knowledge Graph → GraphRAG + Claude → конкретные действия.

Hackathon MVP — 48 часов.

---

## Документы

| Файл | Что |
|---|---|
| [PLAN.md](PLAN.md) | Общий план хакатона + демо-сценарий |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Структура репо, зоны агентов |
| [CONTRACTS.md](CONTRACTS.md) | Все схемы, API, sample fixtures |
| [AGENT_TASKS.md](AGENT_TASKS.md) | Готовые ТЗ для 6 параллельных субагентов |
| [KARPATHY.md](KARPATHY.md) | Behavioral guidelines для всех агентов |
| [DESIGN.md](DESIGN.md) | UI guidelines для фронта |

---

## Быстрый старт

```bash
cp .env.example .env
# отредактируй .env — добавь ANTHROPIC_API_KEY как минимум

docker compose up --build
```

- Backend: http://localhost:8000 (`/health`, `/graph`, `/insights/{id}`)
- Frontend: http://localhost:5173

---

## Для разработки без Docker

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Архитектура (TL;DR)

```
GitHub / Slack (mock) / Jira (mock) / Zoom transcript
        ↓
   Ingest → SQLite (events)
        ↓
   Signals → overload_score per person
        ↓
   NetworkX graph (Person/Repo/Task/Meeting × 5 edge types)
        ↓
   FastAPI:  /graph?layer=  /person/{id}  /insights/{id}
        ↓
   React + react-force-graph-3d + three-layer toggle
```

Полная схема — [ARCHITECTURE.md](ARCHITECTURE.md).
