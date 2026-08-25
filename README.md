# WORLDOS

WORLDOS is an autonomous persistent world simulation.

## Overview

Unlike a chatbot or scripted game, characters independently make decisions inside a deterministic world. The user is primarily an observer, watching emergent events, economic shifts, and political maneuvers unfold through a real-time causal graph.

## Architecture

At the core of WORLDOS is an invariant-enforced simulation engine paired with an LLM-driven decision loop.

```mermaid
flowchart TD
    A[World State] --> B[Agent Perception]
    B --> C[Memory]
    C --> D[Goals]
    D --> E[LLM Decision]
    E --> F[Structured Action]
    F --> G[Validation]
    G --> H[Simulation]
    H --> I[Event]
    I --> J[Consequences]
    J --> K[New World State]
    K --> A
```

### Core Systems

- **Agent Architecture**: Agents are autonomous actors running inside the simulation clock. They perceive the state of the world, synthesize memories, and choose structural actions via an LLM.
- **Deterministic Simulation**: A strict, tick-based engine isolated from LLM hallucinations. All state transitions (hunger, resource decay, time passing) are purely mathematical and predictable.
- **Economic Model**: A closed-loop ledger system. Resources and money cannot magically appear or disappear. Prices dynamically adjust based on scarcity, supply, and demand curves.
- **Political Model**: Governments manage taxes and stability. High unrest, food shortages, or low wealth can trigger systemic political consequences like protests or reforms.
- **Faction System**: Agents belong to factions (Guilds, Noble Houses, Mercenaries). Factions have collective wealth, influence, and ideologies that drive macro-level conflicts.
- **Memory**: Agents record summarized observations of critical events. Memories decay or reinforce over time, directly informing future LLM context windows.
- **Beliefs**: Higher-order synthesized opinions about other characters, factions, or the state of the world (e.g., "The King is weak", "The merchants are hoarding grain").
- **Relationships**: A quantitative relationship graph tracking trust, respect, fear, friendship, and hostility, updated dynamically by event consequences.
- **Event System**: All domain occurrences (trades, protests, movements) are stored as immutable events in an event bus.
- **Causal Graph**: Every event retains a `parent_event_id`, creating an acyclic directed graph that allows observers to trace the exact chain of causality from a macro-event down to an individual's decision.
- **WebSockets**: Real-time telemetry pipeline utilizing Redis Pub/Sub and FastAPI WebSockets to stream events to the Next.js observer dashboard seamlessly.
- **Counterfactuals**: The deterministic architecture allows the simulation to branch and test hypothetical scenarios without affecting the main timeline.
- **LLM Failure Handling**: If the LLM produces invalid schema, hallucinates unavailable resources, or timeouts, the Agent Scheduler falls back to safe, deterministic heuristic actions to prevent simulation crashes.
- **Cost Optimization**: The simulation intelligently buffers context and restricts LLM calls to critical decision boundaries to minimize API costs.

## Getting Started

### Local Setup (Python/Node)

1. Clone the repository and navigate to the project directory.
2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install websockets
   ```
3. Install frontend dependencies:
   ```bash
   cd ../frontend
   npm install
   ```

### Docker Setup

WORLDOS requires PostgreSQL and Redis. The easiest way to run the infrastructure is via Docker Compose:

```bash
docker-compose up -d
```

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/worldos
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=your_api_key
CORS_ORIGINS=["http://localhost:3000"]
```

### Database Setup

Run the Alembic migrations to initialize the database schema:

```bash
cd backend
alembic upgrade head
```

### LLM Configuration

The decision engine supports any OpenAI-compatible endpoint. Ensure `LLM_API_KEY` is set. You can configure the specific model in `app/core/config.py`.

### Running the Simulation

1. Start the FastAPI backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```
2. Start the Next.js Observer Dashboard:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:3000/demo` in your browser.

### Running Tests

The test suite validates database invariants, agent decision parsing, and deadlock prevention.

```bash
cd backend
pytest -v
```

## Demo Scenario: The Grain Crisis

The default scenario initializes a fragile world where food supplies are critically low, testing the resilience of the economic and political systems.

*The demo scenario is not implemented as a scripted sequence; the observed chain emerges from agent decisions and simulation rules.*

### Example Emergent Chain

1. **Scarcity**: A drought reduces farm yields (Deterministic System).
2. **Economic Shift**: The market price of grain skyrockets due to low supply (Economic Model).
3. **Agent Action**: A poor laborer cannot afford food and their health declines (Agent Needs).
4. **Cognitive Shift**: The laborer forms a belief that the Merchant Guild is hoarding grain (Belief System).
5. **Macro Event**: The laborer, driven by high unrest, chooses the `PROTEST` action (LLM Decision).
6. **Consequence**: The protest damages city stability and decreases the Merchant Guild's influence (Simulation Rules).

---
*Note: WORLDOS does not claim to possess AGI, human-level intelligence, true consciousness, or the ability to generate scientifically accurate economic predictions.*
