from __future__ import annotations

from contextlib import AsyncExitStack
import os
from dataclasses import dataclass

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.application.chat_service import ChatService
from app.core.config import Settings
from app.infrastructure.banking.http_gateway import HttpBankingGateway
from app.infrastructure.banking.mock_gateway import MockBankingGateway
from app.infrastructure.llm.openai_adapters import OpenAIAnswerGenerator, OpenAILLMRouter
from app.infrastructure.cache.redis_cache import RedisJsonCache
from app.infrastructure.persistence.audit import SafeAuditRepository
from app.infrastructure.rag.cached_retriever import CachedRetriever
from app.infrastructure.rag.qdrant_retriever import QdrantRetriever
from app.orchestration.graph import BankingAssistantGraph
from app.orchestration.policies import RoutingPolicy


@dataclass(slots=True)
class Container:
    chat_service: ChatService
    exit_stack: AsyncExitStack
    engine: AsyncEngine
    qdrant: AsyncQdrantClient
    redis: Redis

    async def close(self) -> None:
        await self.qdrant.close()
        await self.redis.aclose()
        await self.engine.dispose()
        await self.exit_stack.aclose()


async def build_container(settings: Settings) -> Container:
    stack = AsyncExitStack()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    router = OpenAILLMRouter(
        model=settings.openai_router_model,
        api_key=settings.openai_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    answer = OpenAIAnswerGenerator(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    base_retriever = QdrantRetriever(
        client=qdrant,
        collection=settings.qdrant_collection,
        embedding_model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
        top_k=settings.rag_top_k,
        score_threshold=settings.rag_score_threshold,
    )
    retriever = CachedRetriever(
        base_retriever,
        RedisJsonCache(redis, settings.cache_ttl_seconds),
        namespace=f"rag:{settings.qdrant_collection}",
    )

    if settings.banking_backend_mode.lower() == "mock":
        banking = MockBankingGateway()
    else:
        http_banking = HttpBankingGateway(
            base_url=settings.banking_api_base_url,
            token=settings.banking_api_token,
            timeout_seconds=settings.banking_api_timeout_seconds,
        )
        stack.push_async_callback(http_banking.close)
        banking = http_banking

    checkpointer = None
    if settings.langgraph_checkpoints_enabled:
        os.environ["LANGGRAPH_STRICT_MSGPACK"] = "true" if settings.langgraph_strict_msgpack else "false"
        if not settings.langgraph_aes_key:
            raise RuntimeError("LANGGRAPH_AES_KEY is required when persistent checkpoints are enabled")
        serde = EncryptedSerializer.from_pycryptodome_aes(settings.langgraph_aes_key.encode("utf-8"))
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.langgraph_postgres_uri, serde=serde)
        )
        await checkpointer.setup()

    graph = BankingAssistantGraph(
        router=router,
        banking=banking,
        retriever=retriever,
        answer_generator=answer,
        audit=SafeAuditRepository(engine),
        policy=RoutingPolicy(settings.max_tools_per_request),
        checkpointer=checkpointer,
    )
    return Container(
        chat_service=ChatService(graph, expose_debug_trace=settings.expose_debug_trace),
        exit_stack=stack,
        engine=engine,
        qdrant=qdrant,
        redis=redis,
    )
