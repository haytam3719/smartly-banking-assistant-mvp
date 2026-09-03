import asyncio
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.infrastructure.rag.ingestion import ingest_directory


async def main() -> None:
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.qdrant_url)
    try:
        count = await ingest_directory(
            directory=Path("knowledge_base/demo"),
            client=client,
            collection=settings.qdrant_collection,
            embedding_model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        print(f"Indexed {count} chunks into {settings.qdrant_collection}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
