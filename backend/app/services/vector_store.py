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


# --- Document/chunk store for RAG (policy assistant, Phase 4b) ---
# Separate class + collection from the candidate-resume store above --
# different semantics (arbitrary text chunks with metadata, not just an
# ID), so reusing ChromaVectorStore's candidate-specific interface would
# be the wrong abstraction. Same underlying ChromaDB persist_dir, distinct
# collection name, zero risk to the existing resume-screening code path.

DOCUMENT_COLLECTION_NAME = "policy_documents"


class DocumentChunkMatch(TypedDict):
    chunk_id: str
    text: str
    metadata: dict
    distance: float


class DocumentVectorStore(Protocol):
    def upsert_chunk(self, chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None: ...
    def find_relevant_chunks(self, embedding: list[float], n_results: int) -> list[DocumentChunkMatch]: ...
    def delete_document_chunks(self, document_id: str) -> None: ...


class ChromaDocumentStore:
    def __init__(self, persist_dir: str):
        self._client = chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(DOCUMENT_COLLECTION_NAME)

    def upsert_chunk(self, chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._collection.upsert(ids=[chunk_id], embeddings=[embedding], documents=[text], metadatas=[metadata])

    def find_relevant_chunks(self, embedding: list[float], n_results: int) -> list["DocumentChunkMatch"]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(query_embeddings=[embedding], n_results=min(n_results, self._collection.count()))
        return [
            {"chunk_id": result["ids"][0][i], "text": result["documents"][0][i], "metadata": result["metadatas"][0][i], "distance": result["distances"][0][i]}
            for i in range(len(result["ids"][0]))
        ]

    def delete_document_chunks(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})


_document_store_instance: ChromaDocumentStore | None = None


def get_document_vector_store() -> DocumentVectorStore:
    global _document_store_instance
    if _document_store_instance is None:
        _document_store_instance = ChromaDocumentStore(settings.chroma_persist_dir)
    return _document_store_instance
