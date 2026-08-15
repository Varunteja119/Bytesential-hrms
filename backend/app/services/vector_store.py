"""
Vector store abstraction (ChromaDB).

Unlike llm_client.py and storage.py, this one runs fully in-process (no
external server needed for the default PersistentClient mode), so it's
the one AI-services piece that's actually verified end-to-end in this
environment — see tests/test_vector_store.py.

Purpose: after a resume is screened, its embedding gets stored here
keyed by candidate_id. This powers "find candidates similar to this job
description" via vector similarity search — the RAG-style piece of AI
Resume Screening, not just a single generate() call per candidate.
"""
from typing import Protocol, TypedDict

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config.settings import settings

COLLECTION_NAME = "candidate_resumes"


class SimilarityMatch(TypedDict):
    candidate_id: str
    distance: float


class VectorStore(Protocol):
    def upsert_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None: ...
    def find_similar_candidates(self, embedding: list[float], n_results: int) -> list[SimilarityMatch]: ...
    def delete_candidate_embedding(self, candidate_id: str) -> None: ...


class ChromaVectorStore:
    def __init__(self, persist_dir: str):
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def upsert_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None:
        self._collection.upsert(ids=[candidate_id], embeddings=[embedding])

    def find_similar_candidates(self, embedding: list[float], n_results: int) -> list[SimilarityMatch]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, self._collection.count()),
        )
        ids = result["ids"][0]
        distances = result["distances"][0]
        return [{"candidate_id": cid, "distance": dist} for cid, dist in zip(ids, distances)]

    def delete_candidate_embedding(self, candidate_id: str) -> None:
        self._collection.delete(ids=[candidate_id])


_store_instance: ChromaVectorStore | None = None


def get_vector_store() -> VectorStore:
    """FastAPI dependency. Singleton per-process — ChromaDB's PersistentClient
    manages its own file locking, but there's no reason to re-open it per request."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ChromaVectorStore(settings.chroma_persist_dir)
    return _store_instance
