from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
from qdrant_client import AsyncQdrantClient, models

from app.infrastructure.rag.qdrant_retriever import ensure_collection, stable_chunk_id


@dataclass(frozen=True, slots=True)
class Chunk:
    source: str
    index: int
    content: str
    metadata: dict[str, str]


def chunk_text(text: str, *, size: int = 1200, overlap: int = 200) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata, text[end + 5 :]


def _read_document(file: Path) -> tuple[dict[str, str], str]:
    suffix = file.suffix.lower()
    if suffix in {".md", ".txt"}:
        raw = file.read_text(encoding="utf-8")
        return _parse_front_matter(raw) if suffix == ".md" else ({}, raw)
    if suffix == ".pdf":
        reader = PdfReader(str(file))
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        return {}, text
    return {}, ""


def load_directory(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for file in sorted(f for f in path.rglob("*") if f.suffix.lower() in {".md", ".txt", ".pdf"}):
        metadata, text = _read_document(file)
        metadata = {
            "source": file.name,
            "document_path": str(file),
            "document_id": metadata.get("document_id", file.stem),
            "policy_type": metadata.get("policy_type", file.stem),
            "version": metadata.get("version", "unversioned"),
            "effective_date": metadata.get("effective_date", "unknown"),
            "status": metadata.get("status", "active"),
            **metadata,
        }
        for idx, content in enumerate(chunk_text(text)):
            chunks.append(Chunk(source=file.name, index=idx, content=content, metadata=metadata))
    return chunks


async def ingest_directory(
    *,
    directory: Path,
    client: AsyncQdrantClient,
    collection: str,
    embedding_model: str,
    api_key: str,
) -> int:
    chunks = load_directory(directory)
    if not chunks:
        return 0
    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
    vectors = await embeddings.aembed_documents([c.content for c in chunks])
    await ensure_collection(client=client, collection=collection, vector_size=len(vectors[0]))
    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        payload = {**chunk.metadata, "content": chunk.content, "chunk_index": chunk.index}
        points.append(
            models.PointStruct(
                id=stable_chunk_id(chunk.source, chunk.index, chunk.content),
                vector=vector,
                payload=payload,
            )
        )
    await client.upsert(collection_name=collection, points=points, wait=True)
    return len(points)
