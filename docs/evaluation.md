# Evaluation strategy

A serious assistant needs separate evaluations for **routing**, **retrieval**, **tool execution** and **answer grounding**.

## Routing

Curate paraphrases for each expected source:

- balance → account tool only;
- transactions/spend period → transaction tool only;
- generic fees/procedures → RAG only;
- rejected transfer + resolution → transfer tool then RAG;
- missing transfer reference → clarification.

Measure exact route, exact tool set and unnecessary-call rate.

## Retrieval

For each policy question, label the expected document/chunk family. Measure recall@k, MRR and no-result behavior. Evaluate version/effective-date filters when real documents are available.

## Grounded answers

Review whether every concrete customer fact is supported by a Tool result and every policy claim is supported by retrieved text. A correct refusal/"cannot verify" is better than a fluent unsupported answer.

## Failure injection

Test Banking API timeout, 404, 403, 500, Qdrant unavailable, empty retrieval, model timeout, malformed routing output and duplicate tool plans.

## Performance

Track p50/p95/p99 per graph node, model token usage, Qdrant latency and Banking API latency. Hybrid requests naturally cost more; this should be visible rather than hidden.
