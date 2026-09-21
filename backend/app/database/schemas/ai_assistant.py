import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.database.models.ai_assistant import MessageRole


class PolicyDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class PolicyDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    chunk_count: int


class ChatQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: uuid.UUID | None = None  # omit to start a new session


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    source_documents: str | None


class ChatAnswerResponse(BaseModel):
    session_id: uuid.UUID
    message: ChatMessageOut


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str | None
    message_count: int = 0

    @classmethod
    def from_orm_session(cls, session) -> "ChatSessionOut":
        return cls(id=session.id, title=session.title, message_count=len(session.messages))
