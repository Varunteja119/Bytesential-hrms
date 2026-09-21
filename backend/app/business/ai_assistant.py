"""
RAG pipeline for the AI HR Assistant.

Flow: ingest_policy_document() chunks + embeds a policy doc into the
document vector store. ask_assistant() embeds the user's question,
retrieves the most relevant chunks, and builds a prompt that instructs
the LLM to answer ONLY from that retrieved context -- not from its own
training knowledge. This matters: an HR chatbot confidently answering
"what's our leave policy" from generic training data instead of the
actual uploaded company policy would be actively wrong, not just
imprecise. The prompt explicitly tells the model to say so if the
context doesn't cover the question, rather than guessing.
"""
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database.models.ai_assistant import ChatMessage, ChatSession, MessageRole, PolicyDocument
from app.database.models.user import User
from app.services.llm_client import LLMClient
from app.services.vector_store import DocumentVectorStore

_CHUNK_SIZE = 800  # characters -- small enough for focused retrieval, large enough to keep a paragraph's context intact
_CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Simple fixed-size sliding-window chunking with overlap, splitting on
    paragraph boundaries where possible so a chunk doesn't cut a sentence
    in half more than necessary. Not semantic chunking -- fine for policy
    documents, which are usually short and structured; would need revisiting
    for much longer or less-structured source material."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying a small overlap from the end of the previous one
            overlap_text = current[-overlap:] if current and overlap < len(current) else ""
            current = f"{overlap_text}\n\n{para}".strip() if overlap_text else para
    if current:
        chunks.append(current)
    return chunks


def ingest_policy_document(db: Session, vector_store: DocumentVectorStore, llm: LLMClient, title: str, content: str, uploaded_by: User) -> PolicyDocument:
    chunks = chunk_text(content)
    if not chunks:
        raise AppError("Document content is empty after chunking.")

    document = PolicyDocument(title=title, content=content, uploaded_by_id=uploaded_by.id, chunk_count=len(chunks))
    db.add(document)
    db.commit()
    db.refresh(document)

    for i, chunk in enumerate(chunks):
        embedding = llm.embed(chunk)
        chunk_id = f"{document.id}:{i}"
        vector_store.upsert_chunk(chunk_id, chunk, embedding, {"document_id": str(document.id), "title": title, "chunk_index": i})

    return document


_RAG_PROMPT_TEMPLATE = """You are ByteSentinel's HR policy assistant. Answer the employee's question using ONLY \
the policy excerpts below. If the excerpts don't contain the answer, say clearly that this isn't covered in the \
available policy documents and suggest they contact HR directly -- do NOT guess or use general knowledge.

Policy excerpts:
{context}

Employee question: {question}

Answer concisely and directly."""


def build_rag_prompt(question: str, retrieved_chunks: list[dict]) -> str:
    if not retrieved_chunks:
        context = "(no relevant policy documents found)"
    else:
        context = "\n\n---\n\n".join(f"[From: {c['metadata']['title']}]\n{c['text']}" for c in retrieved_chunks)
    return _RAG_PROMPT_TEMPLATE.format(context=context, question=question)


def ask_assistant(db: Session, vector_store: DocumentVectorStore, llm: LLMClient, session: ChatSession, question: str) -> ChatMessage:
    embedding = llm.embed(question)
    retrieved = vector_store.find_relevant_chunks(embedding, n_results=3)

    prompt = build_rag_prompt(question, retrieved)
    answer = llm.generate(prompt)

    source_titles = sorted({c["metadata"]["title"] for c in retrieved}) if retrieved else []

    user_message = ChatMessage(session_id=session.id, role=MessageRole.USER, content=question)
    db.add(user_message)

    assistant_message = ChatMessage(session_id=session.id, role=MessageRole.ASSISTANT, content=answer, source_documents=", ".join(source_titles) or None)
    db.add(assistant_message)

    if session.title is None:
        session.title = question[:100]

    db.commit()
    db.refresh(assistant_message)
    return assistant_message
