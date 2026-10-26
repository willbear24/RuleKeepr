import chromadb

from backend.app.config import settings
from backend.app.schemas.chunk import SourceChunk
from backend.app.services.chunker import chunk_rulebook

COLLECTION_NAME = "rulebooks"

_collection = None


def get_collection():
    """Connect to ChromaDB on first use so importing this module never needs a server."""
    global _collection
    if _collection is None:
        client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
        _collection = client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return _collection


def retrieve(
    question: str,
    game_id: int,
    n_results: int = 5,
    max_distance: float = 0.8,
) -> list[SourceChunk]:
    """Return the chunks of one game's rulebook closest to the question."""
    collection = get_collection()
    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        where={"game_id": game_id},
    )

    chunks = []
    for document, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        if dist <= max_distance:
            chunks.append(
                SourceChunk(
                    game_id=meta["game_id"],
                    game_title=meta["game_title"],
                    chunk_index=meta["chunk_index"],
                    section=meta.get("section") or None,
                    text=document,
                    score=round(1 - dist, 4),
                )
            )
    return chunks


def ingest_game(game_id: int, title: str, text: str) -> int:
    """Chunk one rulebook and store it in ChromaDB, replacing any earlier version.

    Returns the number of chunks stored. Safe to re-run.
    """
    chunks = chunk_rulebook(text)
    collection = get_collection()

    # Delete first so a shorter rewrite doesn't leave stale chunks behind.
    collection.delete(where={"game_id": game_id})
    if not chunks:
        return 0

    collection.upsert(
        ids=[f"{game_id}-{chunk.index}" for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "game_id": game_id,
                "game_title": title,
                "chunk_index": chunk.index,
                # Chroma metadata can't hold None.
                "section": chunk.section or "",
            }
            for chunk in chunks
        ],
    )
    return len(chunks)
