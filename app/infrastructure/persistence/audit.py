from __future__ import annotations

import json

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.request_context import RequestContext

logger = structlog.get_logger(__name__)


class SafeAuditRepository:
    """Stores orchestration metadata only; never raw balances/transactions/RAG contents."""

    def __init__(self, engine: AsyncEngine | None) -> None:
        self.engine = engine

    async def record(self, *, context: RequestContext, event: str, metadata: dict[str, object]) -> None:
        safe = self._sanitize(metadata)
        logger.info("audit_event", request_id=context.request_id, conversation_id=context.conversation_id, event=event, metadata=safe)
        if self.engine is None:
            return
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO assistant_audit_event(request_id, conversation_id, customer_ref_hash, event_type, metadata)
                    VALUES (:request_id, :conversation_id, encode(digest(:customer_id, 'sha256'),'hex'), :event_type, CAST(:metadata AS jsonb))
                    """
                ),
                {
                    "request_id": context.request_id,
                    "conversation_id": context.conversation_id,
                    "customer_id": context.customer_id,
                    "event_type": event,
                    "metadata": json.dumps(safe, default=str),
                },
            )

    @classmethod
    def _sanitize(cls, value: object) -> object:
        if isinstance(value, dict):
            return {str(k): cls._sanitize(v) for k, v in value.items() if str(k).lower() not in {"data", "content", "balance", "transactions"}}
        if isinstance(value, (list, tuple, set)):
            return [cls._sanitize(v) for v in value]
        return value
