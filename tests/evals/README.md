# Evaluation set

`scenarios.json` is an offline routing contract. A CI job with model credentials can call the real router and measure exact route/tool selection, while unit tests keep the core policy deterministic.

Recommended release gates:

- route accuracy >= 98% on the curated banking set;
- zero unauthorized customer identity/tool-argument violations;
- hybrid order correctness = 100%;
- tool-call precision > tool-call recall for sensitive endpoints (prefer clarification over an unnecessary call);
- grounded-answer unsupported-claim rate below an agreed threshold measured by human review + automated checks.
