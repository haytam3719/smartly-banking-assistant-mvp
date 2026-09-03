# Threat model (condensed)

## Assets

- customer-specific banking data;
- authenticated customer identity;
- policy corpus and versions;
- model/tool credentials;
- orchestration/audit trail.

## Main threats and controls

### Cross-customer data access
Control: customer identity is supplied by trusted request context to the gateway, never by the LLM. Transfer ownership is enforced upstream and demonstrated in the mock adapter.

### Prompt injection from user or RAG content
Control: retrieved documents are treated as evidence/data. The model cannot create arbitrary tool names or customer identities. Structured routing is policy-validated before execution.

### Hallucinated customer facts
Control: final generation receives Tool/RAG evidence and must state inability to verify when evidence is missing. Dynamic data can only come from tools.

### Excessive/expensive calls
Control: route types, max-tool limit, deduplication, top-k retrieval, score threshold and short timeouts.

### Sensitive observability data
Control: audit metadata excludes raw tool results/RAG content. Production telemetry must sanitize authorization/session headers and avoid recording prompts with PII.

### Upstream instability
Control: bounded retry only for transient connection/5xx failures, no retry for authorization/not-found, tight timeouts, safe customer-facing errors.

### Poisoned/outdated policy corpus
Control: ingest only approved sources; include document version/effective date metadata; use a controlled publication pipeline and deletion/reindex workflow.
