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
        self._client = chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def upsert_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None:
        self._collection.upsert(ids=[candidate_id], embeddings=[embedding])

    def find_similar_candidates(self, embedding: list[float], n_results: int) -> list[SimilarityMatch]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(query_embeddings=[embedding], n_results=min(n_results, self._collection.count()))
        return [{"candidate_id": cid, "distance": dist} for cid, dist in zip(result["ids"][0], result["distances"][0])]

    def delete_candidate_embedding(self, candidate_id: str) -> None:
        self._collection.delete(ids=[candidate_id])


_store_instance: ChromaVectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = ChromaVectorStore(settings.chroma_persist_dir)
    return _store_instance
