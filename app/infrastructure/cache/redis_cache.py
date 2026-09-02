from __future__ import annotations

import json

from redis.asyncio import Redis


class RedisJsonCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def get(self, key: str) -> dict[str, object] | None:
        raw = await self.redis.get(key)
        if raw is None:
            return None
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    async def set(self, key: str, value: dict[str, object]) -> None:
        await self.redis.set(key, json.dumps(value, default=str), ex=self.ttl_seconds)
