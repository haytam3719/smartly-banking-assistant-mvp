from app.infrastructure.rag.ingestion import chunk_text


def test_chunking_preserves_text_and_overlap() -> None:
    text = "A" * 3000
    chunks = chunk_text(text, size=1000, overlap=100)
    assert len(chunks) >= 3
    assert all(chunks)
    assert chunks[0][-100:] == chunks[1][:100]
