# WORLDOS Architecture

## Architectural Principles

1. **Domain Logic Isolation**: Domain logic must not depend on FastAPI, PostgreSQL directly, or Redis directly.
2. **Pluggable LLMs**: LLM providers must be replaceable (abstracted). Initially, OpenAI is supported along with a mock provider for tests.
3. **Structured Decisions**: Agent decisions must be structured and validated.
4. **Deterministic Simulation**: World state mutations must be deterministic and testable. The LLM NEVER directly modifies world state.
5. **Immutable Events**: Events must be immutable, preserving causal relationships.
6. **Resilience**: The simulation must continue when the LLM is unavailable.
7. **Testability**: Tests must not require real LLM API calls.
8. **No Chain-of-Thought Storage**: Do not store chain-of-thought, only concise decision summaries.
9. **Simplicity over Frameworks**: Avoid unnecessary abstractions. Prefer simple, explicit code. Do NOT use agent frameworks like LangChain, LangGraph, CrewAI, AutoGen.

## Core Architecture

The architecture follows a modular domain-driven design structure:

- `api/`: REST APIs and controllers
- `core/`: Application settings and global configurations
- `domain/`: Pure python business logic models and services. Divided into subdomains (`world`, `character`, `city`, etc.)
- `agents/`: Agent orchestration and loop execution logic
- `memory/`: Memory retrieval and semantic search logic
- `llm/`: LLM provider abstraction and structured output parsing
- `persistence/`: Database repositories and SQLAlchemy models
- `infrastructure/`: External integrations (e.g. Redis client, HTTP clients)

## The Core Loop

1. **Agent Perception**: The agent observes current state and recent events.
2. **Memory Retrieval**: Relevant past memories are loaded based on perception.
3. **Decision Making**: LLM generates a structured action proposal based on goals, personality, and beliefs.
4. **Action Execution**: The Deterministic Simulation Engine validates and applies the action, mutating world state and producing events.
5. **Consequences**: Triggers downstream effects across the world state.
