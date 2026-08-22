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
- **Immutable Event System**: A rigorous, auditable event pub-sub store tracking all significant domain occurrences (trades, protests, migrations, etc.). All events strictly map via an acyclic parent-child graph and are mathematically immutable upon creation.
- **Cascading Consequence Engine**: A deterministic breadth-first-search engine modeling rippling effects of events (e.g., `FOOD_SHORTAGE` -> `PROTEST` -> `POLITICAL_TENSION`). Preventative mechanisms like cascade depth-limiting, rule cooldowns, and cryptographic duplicate-event suppression are built-in.
- **Agent Architecture**: A strictly constrained agent decision layer built entirely around structured Pydantic representations (e.g., `AgentContext`, `AgentAction`). Enforces that agents only *propose* actions via immutable snapshots, completely shielding world-state integrity.
- **Pluggable LLM Abstraction**: A fault-tolerant wrapper (`LLMProvider`) standardizing the interaction with underlying models (e.g., OpenAI). Provides native JSON schema enforcement, usage/latency metrics, timeout thresholds, and robust fallback responses. No "chain-of-thought" is unnecessarily stored.
- **Character Decision Engine**: An orchestrator translating simulation state into LLM prompts without spamming APIs. Operates on priority-driven frequency cooldowns, utilizing LLM-derived deterministic fallbacks on errors.
- **Action Execution Engine**: The final gatekeeper resolving proposed LLM actions against domain rules (e.g., checking bank balances before purchases). Operates within strict nested database transactions that completely rollback and gracefully capture rejection data upon invalid action attempts.
- **Agent Memory System**: A persistent memory system that filters events by importance thresholds, storing only significant occurrences (e.g., betrayals, major trades). Utilizes a relevance-scoring retriever that prioritizes entity overlap to feed agents highly contextual, long-term memory.
- **Personality & Beliefs**: Characters possess normalized personality traits (ambition, greed, empathy) which drive a subjective `BeliefUpdateEngine`. Characters observing identical events form divergent, entirely subjective (and sometimes inaccurate) beliefs about other agents, factions, and policies.
- **Dynamic Relationships**: An organic social web tracking trust, respect, friendship, hostility, influence, and obligation. Relationships evolve deterministically based on agent interactions (e.g., helping during a crisis spikes obligation, while betrayal spikes hostility).
- **Faction Simulation**: Organizations (Factions) operate as macro-agents using the exact same decision engine architecture. Factions perceive their wealth, power, and ideology, proposing macro-level actions like recruiting, funding protests, or forming alliances.
- **Deterministic Political Engine**: A policy-driven government simulation handling taxes, wages, subsidies, military spending, and market regulations. The engine calculates citizen approval, stability, and security capacity strictly without randomness—predictably triggering events like protests or strikes when conditions deteriorate or opposing factions exert pressure.
- **World Lifecycle Management**: API-driven controls for starting, pausing, and advancing the simulation. Features a non-mutating world cloning architecture that automatically untangles and remaps complex circular dependencies (like Faction leaders), allowing users to branch historical scenarios natively in the database.
- **Real-time Event Streaming**: A resilient WebSockets layer backed by Redis pub-sub. Selectively broadcasts incremental domain events (e.g., market crashes, character actions, protests) to connected clients in real-time, completely bypassing the need to poll massive full-world state payloads.
- **Robust Quality & Determinism**: A meticulously calibrated testing framework that guarantees 100% deterministic, deadlock-free integration tests across asynchronous boundaries. Proactively prevents PostgreSQL connection pool deadlocks and strictly isolates async event loops to ensure high reliability across operating systems.

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
