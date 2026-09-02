from __future__ import annotations

import json
from datetime import UTC, datetime

from langchain_openai import ChatOpenAI

from app.domain.models import GroundedAnswer, RagEvidence, RoutingDecision, ToolResult
from app.infrastructure.llm.prompts import ANSWER_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT


class OpenAILLMRouter:
    def __init__(self, *, model: str, api_key: str, timeout_seconds: float) -> None:
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0, timeout=timeout_seconds)
        self.structured = llm.with_structured_output(RoutingDecision)

    async def route(self, message: str) -> RoutingDecision:
        today = datetime.now(UTC).date().isoformat()
        return await self.structured.ainvoke(
            [
                {"role": "system", "content": f"{ROUTER_SYSTEM_PROMPT}\n\nTODAY={today}"},
                {"role": "user", "content": message},
            ]
        )


class OpenAIAnswerGenerator:
    def __init__(self, *, model: str, api_key: str, timeout_seconds: float) -> None:
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0, timeout=timeout_seconds)
        self.structured = llm.with_structured_output(GroundedAnswer)

    async def generate(
        self,
        *,
        message: str,
        tool_results: list[ToolResult],
        rag_evidence: list[RagEvidence],
        clarification_question: str | None,
        unsupported: bool,
    ) -> GroundedAnswer:
        if clarification_question:
            return GroundedAnswer(answer=clarification_question)
        if unsupported:
            return GroundedAnswer(
                answer="Je peux vous aider sur les informations bancaires couvertes par ce service.",
                insufficient_evidence=True,
            )

        evidence = {
            "tools": [r.model_dump(mode="json") for r in tool_results],
            "rag": [
                {
                    "source": e.source,
                    "chunk_id": e.chunk_id,
                    "score": e.score,
                    "content": e.content,
                }
                for e in rag_evidence
            ],
        }
        return await self.structured.ainvoke(
            [
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"USER QUESTION:\n{message}\n\nVERIFIED EVIDENCE:\n{json.dumps(evidence, ensure_ascii=False, default=str)}",
                },
            ]
        )
