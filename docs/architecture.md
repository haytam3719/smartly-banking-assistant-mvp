# Architecture decision record

## Context

The brief requires a conversational banking assistant that chooses between a knowledge base and customer-specific APIs. The risky part is not text generation; it is **controlled orchestration of trusted data sources**.

## Decision

Use a modular-monolith FastAPI service with LangGraph for explicit workflow state and conditional transitions. The model performs semantic planning through structured output; application code validates the plan and owns all side effects.

## Why not a fully autonomous tool-calling agent?

A general agent loop gives the model more freedom than this banking use case needs. The supported operations are known in advance, and the expected routes are testable. Explicit routing makes it easier to prove that a balance question does not trigger RAG and that a policy question does not trigger a customer API.

## Why LangGraph?

The graph makes RAG-only, Tools-only and Hybrid paths explicit, supports async nodes, can persist state with a Postgres checkpointer, and creates a natural place for future human approval steps.

## Why Qdrant?

A dedicated vector service keeps the online retrieval path independent from transactional/audit persistence. Metadata filters, collection lifecycle and horizontal deployment can evolve separately from application Postgres.

## Why Postgres?

Postgres stores audit metadata and can back LangGraph checkpoints. This gives durable workflow state without placing customer banking data inside the assistant database.

## Online data ownership

The assistant is **not** the system of record. Account/card/transfer/transaction truth remains in Banking APIs. RAG documents are authoritative only for the policy version represented by their metadata.

## Conversation memory

Checkpointing is optional in the challenge profile. In production, use encrypted Postgres-backed checkpoints and apply explicit retention. Avoid persisting raw tool payloads longer than required.

## Future decomposition

If load/team boundaries justify it, split:

- document ingestion/indexing worker;
- online assistant API;
- banking-tool gateway;
- evaluation/observability pipeline.

Do not split merely to claim “microservices”.
