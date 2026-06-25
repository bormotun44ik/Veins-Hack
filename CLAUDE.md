# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Veins is a hackathon MVP: an AI system that ingests signals from GitHub/Slack/Jira/Zoom transcripts, builds a NetworkX knowledge graph, and uses Claude (via ShadoClaw proxy) to generate burnout/overload insights for engineering managers. Two independent builds: Python FastAPI backend, React + Vite frontend.

---

## Commands

### Full stack (Docker)
```bash
cp .env.example .env   # add SHADOCLAW_BASE_URL, GITHUB_TOKEN etc.
docker compose up --build
```
Backend: http://localhost:8000 | Frontend: http://localhost:5173

### Backend (native dev)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (native dev)
```bash
cd frontend
npm install
npm run dev        # Vite dev server, hot reload
npm run build      # tsc -b && vite build
```

### Tests
```bash
cd backend
pytest                                        # all tests
pytest tests/test_signals/test_basic.py      # single file
pytest -k test_night_commits_high            # single test by name
```

### Seeding the DB
```bash
# From repo root, with .venv active:
python scripts/seed_demo_v2.py --fresh   # drops and rebuilds SQLite + LLM cache
python scripts/seed_demo_v2.py           # idempotent (skip if DB exists)
```

### Smoke test + demo utilities
```bash
bash scripts/smoke_test.sh
python scripts/prewarm_cache.py          # pre-warms Claude cache before demo
python scripts/push_event.py             # inject a live event via POST /ingest/event
python scripts/demo_cycle.py            # replay demo scenarios from scripts/demo_scenarios/
```

---

## Architecture

### Data flow
```
GitHub / Slack (mock) / Jira (mock) / Zoom transcript
  → Ingest (app/ingest/)          — parses data/*.json into SQLite
  → Signals (app/signals/)        — compute 0.0-1.0 scores per person
  → composite.py                  — weighted sum → overload_score stored in people.overload_score
  → Graph Builder (app/graph/builder.py)   — SQLite → NetworkX MultiDiGraph
  → Layers (app/graph/layers.py)  — filter graph into stress / collab / workload views
  → RAG context (app/rag/)        — assembles per-person context dict for LLM
  → LLM (app/llm/client.py)       — calls Claude via ShadoClaw proxy, with two-level caching
  → FastAPI endpoints             — served to React frontend
```

### SQLite schema (single DB file, path from `DATABASE_PATH` env)
Tables: `people`, `events`, `repos`, `tasks`, `meetings`, `edges`, `llm_cache`, `signal_snapshots`. All access goes through `app.db.get_connection()` — never hardcode the path.

### Signals (`app/signals/`)
Each signal module exposes `compute(person_id, conn) -> float` (0=healthy, 1=critical). Signals: `night_commits`, `fix_revert`, `tone_delta` (uses LLM via Groq), `pr_lag`, `bus_factor`, `co_isolation`, `weekend_activity`. `composite.py` combines them with fixed weights into `overload_score`.

### Graph (`app/graph/`)
`builder.py` constructs a `nx.MultiDiGraph` from DB events. Node types: Person, Repo, Task, Meeting. Edge types: `commits_to`, `co_authored`, `reviews_pr`, `assigned_to`, `attended`. `layers.py` produces three filtered views served by `/graph?layer=stress|collab|workload`.

### LLM + Caching (`app/llm/`)
`client.py` wraps `anthropic.AsyncAnthropic` pointed at the ShadoClaw proxy (`SHADOCLAW_BASE_URL`). Model aliases: `opus` → `claude-opus-4-7`, `sonnet` → `claude-sonnet-4-6`, `haiku` → `claude-haiku-4-5-20251001`. Two cache layers:
1. **Prompt-hash cache** (`llm_cache` table): `SHA256(system+user+model)` → raw response string.
2. **Smart cache** (`signal_snapshots` table): bucketized signal fingerprint per person, 24h TTL, invalidates on status boundary crossings (green/yellow/red at 0.4 and 0.7).

### RAG context (`app/rag/`)
`context.py` assembles a dict of person metadata + signals. `context_v2.py` extends it with historical trends, peer comparison, role focus hints, and retrieved embedding chunks. `retrieval.py` does cosine similarity over `rag/index.py` embeddings. Always prefer `context_v2`; `context.py` is the v1 fallback.

### Ingest (`app/ingest/`)
On startup, `main.py` calls `ingest_all(conn)` (parses `data/*.json`) then `update_all_people(conn)` (recomputes all signals). `ingest/api.py` exposes `POST /ingest/event` for live event injection; it does a cheap signal recompute and triggers a background Claude re-generation only when a person's status boundary flips (green↔yellow↔red).

### Frontend (`frontend/src/`)
- `api.ts` — typed fetch client; set `VITE_MOCK=true` to use `data/samples/*.json` fixtures without a running backend.
- `types.ts` — mirrors CONTRACTS.md schemas; keep in sync with backend API responses.
- `GraphView.tsx` — `react-force-graph-3d` 3D force graph.
- `InsightPanel.tsx` — sidebar showing Claude insights + action buttons.
- `Dashboard.tsx` — team overview with attention list, shoutouts, heatmap.

### ShadoClaw proxy (`vendor/shadoclaw/`)
An Anthropic-compatible OpenProxy. Required for LLM calls. Set `OPENPROXY_STRIP_SYSTEM=1` in Docker. Native dev: run it manually on port 8317.

---

## Key Contracts

- **CONTRACTS.md** is the authoritative API and schema spec. When backend and contracts diverge, fix the code.
- **data/samples/** contains reference fixtures. Use them in tests; don't mock inline.
- `overload_score` thresholds: `> 0.7` = red, `> 0.4` = yellow, else green.
- All `VeinsError` subclasses (`PersonNotFound`, `BadLayer`, `LLMUnavailable`, `BadEvent`) in `app/errors.py` are handled by the global exception handler in `main.py`.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `SHADOCLAW_BASE_URL` | LLM proxy URL (no `/v1` suffix — SDK appends it) |
| `DATABASE_PATH` | SQLite file path |
| `DATA_DIR` | Path to `data/` folder |
| `GITHUB_TOKEN` / `GITHUB_REPO` | Real GitHub ingest |
| `USE_FAKE_GITHUB=true` | Skip GitHub API, use `data/fake_team.json` |
| `GROQ_API_KEY_1..5` | Whisper transcription, round-robin rotated |
| `VITE_API_BASE` | Frontend → backend base URL |
| `VITE_MOCK=true` | Frontend uses local fixture files only |
