# WORLDOS

WORLDOS is an autonomous persistent world simulation powered by agentic AI.

## Overview

The world contains characters, cities, factions, governments, resources, economies, relationships, goals, beliefs, memories, political events, economic events, and cascading consequences.

The user is primarily an OBSERVER, not a direct character controller.

## Core Loop

1. **WORLD STATE**
2. **AGENT PERCEPTION**
3. **MEMORY RETRIEVAL**
4. **GOALS + PERSONALITY + BELIEFS**
5. **LLM DECISION**
6. **STRUCTURED ACTION**
7. **ACTION VALIDATION**
8. **DETERMINISTIC SIMULATION ENGINE**
9. **WORLD STATE CHANGE**
10. **EVENT**
11. **CONSEQUENCES**
12. **NEW WORLD STATE**
13. **AGENTS WAKE UP**

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.x, PostgreSQL, Redis, Pydantic v2, Alembic, asyncio, pytest
- **Frontend**: Next.js, TypeScript, Tailwind CSS, React Flow, Recharts
- **Infrastructure**: Docker, Docker Compose

## Development

See [architecture.md](docs/architecture.md) for architectural guidelines.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Infrastructure

```bash
docker compose up -d
```
