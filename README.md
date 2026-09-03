# Smartly.ai — AI Banking Assistant (production-oriented reference implementation)

This repository implements the technical challenge as a **serious banking-assistant service**, while keeping the challenge's core contract intact:

- general product/rule/procedure questions → **RAG**;
- dynamic/customer-specific questions → **Banking Tools/APIs**;
- mixed questions → **Tools first, then RAG**;
- never fabricate customer information;
- expose `POST /chat`;
- avoid unnecessary calls.

> Important: the challenge mentions a banking knowledge base but no corpus was supplied with the brief. The files under `knowledge_base/demo/` are explicitly **synthetic fixtures** used only to demonstrate ingestion/retrieval. They must be replaced by authoritative documents in a real deployment.

## Why this architecture

This is deliberately a **modular monolith**, not a fake microservice zoo. The request path is latency-sensitive and the domain is still compact. Boundaries are expressed as ports/adapters so Banking APIs, the vector store, model provider, persistence and caching can be split later without rewriting business rules.

```text
Client / Mobile / BFF
        |
        v
   FastAPI /chat
        |
        v
 Request Context + Validation
        |
        v
+---------------------------+
| LangGraph Orchestrator    |
|                           |
|  route (structured LLM)   |
|      |                    |
|      +--> RAG ------------+---+
|      |                        |
|      +--> Tools --------------+--> Evidence Gate --> Grounded Answer
|      |                        |
|      +--> Tools --> RAG ------+
|                           |
+---------------------------+
        |
        +--> Audit events (Postgres)
        +--> Checkpoints (Postgres, optional)
        +--> Metrics / traces (OpenTelemetry)

External adapters:
  Banking APIs (HTTPX) | Qdrant | Redis | OpenAI-compatible model
```

## Production design principles

1. **The LLM plans; application code authorizes and executes.** The model cannot choose a customer identity and cannot call arbitrary endpoints.
2. **Tool calls are typed and policy-validated.** Unsupported tools, duplicate calls, missing transfer IDs and excessive calls are rejected before execution.
3. **Hybrid is Tool → RAG.** Dynamic facts narrow the document lookup. If the tool fails, the RAG step is skipped.
4. **Evidence-bound generation.** The final model receives only approved Tool and RAG evidence. If evidence is insufficient, it must say so.
5. **PII-aware observability.** Audit records contain route/tool metadata, latency and status — not raw balances or full transaction payloads.
6. **Async I/O end-to-end.** FastAPI, HTTPX, Qdrant, Redis and Postgres adapters are asynchronous.
7. **Durable workflow support.** LangGraph can be compiled with an AES-encrypted Postgres checkpointer; local mode may run without it.
8. **Resilience.** Banking API calls have tight timeouts and bounded retries for transient failures only.

## Request contract

The canonical versioned endpoint is `/api/v1/chat`; `/chat` is also exposed as a compatibility alias because the challenge explicitly requires it.

```http
POST /api/v1/chat
Content-Type: application/json
X-Request-ID: optional-client-correlation-id
```

```json
{
  "customer_id": "C1024",
  "conversation_id": "conv-demo-001",
  "message": "Mon virement TR4587 a été refusé. Pourquoi et que dois-je faire ?"
}
```

Example response:

```json
{
  "request_id": "...",
  "conversation_id": "conv-demo-001",
  "answer": "...",
  "route": "HYBRID",
  "source": "get_transfer_status+RAG",
  "citations": [
    {"type": "TOOL", "name": "get_transfer_status"},
    {"type": "RAG", "name": "transfer_policy.md", "chunk_id": "...", "score": 0.83}
  ]
}
```

## Core workflow

### 1. Structured routing

`LLMRouter` receives the message and the current date, and returns a validated `RoutingDecision` rather than free text. The decision can be:

- `RAG_ONLY`
- `TOOLS_ONLY`
- `HYBRID`
- `CLARIFY`
- `UNSUPPORTED`

The policy layer then normalizes and validates the plan before any side effect happens.

### 2. Tool execution

`ToolExecutor` receives the **server-controlled** `customer_id` plus approved tool plans. The model never supplies the customer identity. Multiple independent tools may run concurrently.

The repository includes two Banking adapters:

- `MockBankingGateway` for the challenge/demo;
- `HttpBankingGateway` for a realistic upstream BFF/API integration.

### 3. RAG

The production adapter uses Qdrant. Ingestion supports Markdown, text and PDF documents and stores chunk content plus metadata (`document_id`, `source`, `policy_type`, `version`, `effective_date`, `status`). Retrieval only searches active documents, applies a relevance threshold and returns citations. The final prompt treats retrieved text as **untrusted evidence**, not executable instructions.

### 4. Hybrid flow

For a rejected transfer:

```text
get_transfer_status(TR4587)
        |
        v
status=REJECTED, reason=PAYMENT_LIMIT_EXCEEDED
        |
        v
build evidence-aware RAG query
        |
        v
retrieve transfer policy matching rejection reason
        |
        v
grounded answer
```

If `get_transfer_status` returns not-found/forbidden/timeout, the graph goes directly to the answer node and **does not perform a generic RAG lookup**.

## Repository layout

```text
app/
  api/                 HTTP contract, dependencies, exception handlers
  application/         use cases + ports
  core/                config, logging, telemetry, request context
  domain/              enums, entities, errors
  orchestration/       LangGraph state, nodes, routing policies, graph
  infrastructure/
    banking/           mock + HTTP Banking API adapters
    cache/             Redis adapter
    llm/               router + grounded answer model adapters
    persistence/       SQLAlchemy audit repository
    rag/               Qdrant + embedding adapter
knowledge_base/demo/   synthetic RAG fixtures only
scripts/               ingestion + smoke test
infra/postgres/         audit schema
 tests/                 unit + architecture/evaluation tests
```

## Local run

```bash
cp .env.example .env
# add OPENAI_API_KEY when testing live LLM/RAG behavior

docker compose up -d postgres redis qdrant
pip install -e ".[dev]"
python scripts/ingest.py
uvicorn app.main:app --reload
```

OpenAPI: `http://localhost:8000/docs`

## Tests

```bash
pytest -q
```

The deterministic unit suite does **not** require a real LLM. Live routing/evaluation tests are separately marked.

## Security notes

For challenge compatibility, `customer_id` is present in the request body. In a production bank channel, it must instead be derived from an authenticated token/session and compared against any route/customer context. The same applies to transfer ownership: the Banking gateway is expected to enforce customer ownership server-side.

Never log raw Tool payloads. Do not put account balances, PANs, transaction descriptions or customer profile fields into traces. The included audit repository stores metadata only.

## Scaling path

- run stateless API replicas behind a load balancer;
- keep checkpoints/audit in Postgres;
- run Qdrant as a managed/clustered vector service;
- Redis for small short-lived caches/rate controls;
- separate ingestion from online serving;
- move Banking integration behind an API gateway/service mesh;
- add model-provider failover if required;
- add offline evaluation gates to CI before prompt/model changes.

See `docs/architecture.md`, `docs/threat-model.md` and `docs/evaluation.md` for the design rationale.
