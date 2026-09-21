"""
AI HR Assistant (RAG chatbot) schema.

Per SRS Employee Self-Service: "Chat with AI assistant". Design: HR
uploads PolicyDocument rows (plain text policy content); each gets
chunked and embedded into the document vector store (see
services/vector_store.py). When an employee asks a question, the
relevant chunks are retrieved and given to the LLM as context -- this
is retrieval-augmented generation, not the LLM answering from its own
training data, which matters because company-specific policy questions
need company-specific answers, not generic HR knowledge.

ChatSession/ChatMessage give the assistant actual conversation history
(so a follow-up question like "what about sick leave?" has context from
the prior message) rather than being a single stateless Q&A per request.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection.database import Base
from app.database.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class PolicyDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "policy_documents"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # full raw text, chunked separately into the vector store
    uploaded_by_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    chunk_count: Mapped[int] = mapped_column(default=0)  # how many chunks this doc was split into, for visibility


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))  # derived from the first question, for a session list UI

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Titles of policy documents whose chunks were used to answer -- surfaced
    # to the user for transparency ("this answer is based on: Leave Policy").
    source_documents: Mapped[str | None] = mapped_column(Text)  # comma-separated titles; simple by design, not a join table
