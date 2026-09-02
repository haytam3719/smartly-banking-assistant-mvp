from __future__ import annotations

import hashlib

from app.domain.models import RagEvidence
from app.infrastructure.cache.redis_cache import RedisJsonCache


class CachedRetriever:
    """Caches only general RAG evidence; customer Tool data is never cached here."""

    def __init__(self, inner, cache: RedisJsonCache, namespace: str = "rag:v1") -> None:
        self.inner = inner
        self.cache = cache
        self.namespace = namespace

    async def retrieve(self, query: str) -> list[RagEvidence]:
        digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
        key = f"{self.namespace}:{digest}"
        cached = await self.cache.get(key)
        if cached and isinstance(cached.get("items"), list):
            return [RagEvidence.model_validate(item) for item in cached["items"]]

        items = await self.inner.retrieve(query)
        await self.cache.set(key, {"items": [item.model_dump(mode="json") for item in items]})
        return items
