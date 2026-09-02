from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5
from pathlib import Path
from typing import Any

from langchain_openai import OpenAIEmbeddings
from qdrant_client import AsyncQdrantClient, models

from app.domain.models import RagEvidence


class QdrantRetriever:
    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        collection: str,
        embedding_model: str,
        api_key: str,
        top_k: int,
        score_threshold: float,
    ) -> None:
        self.client = client
        self.collection = collection
        self.embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def retrieve(self, query: str) -> list[RagEvidence]:
        vector = await self.embeddings.aembed_query(query)
        response = await self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=self.top_k,
            score_threshold=self.score_threshold,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="status", match=models.MatchValue(value="active"))]
            ),
            with_payload=True,
        )
        evidence: list[RagEvidence] = []
        for point in response.points:
            payload = dict(point.payload or {})
            content = str(payload.pop("content", ""))
            source = str(payload.get("source", "unknown"))
            if not content:
                continue
            evidence.append(
                RagEvidence(
                    chunk_id=str(point.id),
                    source=source,
                    content=content,
                    score=float(point.score),
                    metadata=payload,
                )
            )
        return evidence


async def ensure_collection(
    *, client: AsyncQdrantClient, collection: str, vector_size: int
) -> None:
    exists = await client.collection_exists(collection)
    if not exists:
        await client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )


def stable_chunk_id(source: str, index: int, content: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"{source}:{index}:{content}"))
