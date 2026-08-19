# WORLDOS

WORLDOS is an autonomous persistent world simulation powered by agentic AI.

## Overview

The world contains characters, cities, factions, governments, resources, economies, relationships, goals, beliefs, memories, political events, economic events, and cascading consequences.

The user is primarily an OBSERVER, not a direct character controller.

## Implemented Features

- **Robust Persistence Layer**: Fully asynchronous SQLAlchemy 2.0 configuration with PostgreSQL, Redis, and a Unit of Work repository pattern.
- **Core Domain Entities**: Complete modeling of `World`, `City`, `Character`, `Faction`, `Resource`, `Inventory`, `Relationship`, `Goal`, `Memory`, and `Event` ecosystems.
- **Procedural World Generation**: A strictly deterministic, seed-based world generator that creates highly coherent starting states (tying character occupations to appropriate factions, relationships, and resource constraints). Accessible via the `POST /worlds/generate` API endpoint.
- **Deterministic Simulation Engine**: An autonomous tick-based clock controlling simulation states (`start`, `pause`, `advance`) completely isolated from the HTTP layer. One tick accurately represents one simulated hour, seamlessly rolling over to track days and globally synchronizing world updates.
- **Dynamic Character Needs System**: Character motivations are mathematically modeled via bounded `CharacterNeeds` (`food`, `shelter`, `wealth`, `safety`, `social`, `status`). Need levels deterministically decay and adapt based on environmental contexts (like hunger over time, unemployment, danger, or isolation) generating immutable snapshots for future AI decisions.
- **Economic Production & Consumption**: A closed-loop resource tracker assigning production yields (e.g., miners -> iron) and baseline consumption rates based on character occupation. Protected by strict invariant/conservation ledgers so resources cannot magically appear or disappear.
- **Market & Pricing Simulation**: A localized trading engine calculating real-time, dynamic pricing based on a transparent supply/demand scarcity formula. Transactions operate atomically across character inventories, cleanly handling money and resource transfers.

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
