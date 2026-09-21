import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.business.ai_assistant import ask_assistant, ingest_policy_document
from app.database.connection.database import get_db
from app.database.models.ai_assistant import ChatSession, PolicyDocument
from app.database.models.user import User
from app.database.schemas.ai_assistant import (
    ChatAnswerResponse, ChatMessageOut, ChatQuestionRequest, ChatSessionOut, PolicyDocumentCreate, PolicyDocumentOut,
)
from app.dependencies.auth import get_current_user, require_permission
from app.services.llm_client import LLMClient, get_llm_client
from app.services.vector_store import DocumentVectorStore, get_document_vector_store

router = APIRouter(prefix="/ai-assistant", tags=["ai-assistant"])


@router.post("/policies", response_model=PolicyDocumentOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("ai_assistant:manage"))])
def upload_policy_document(
    payload: PolicyDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: DocumentVectorStore = Depends(get_document_vector_store),
):
    document = ingest_policy_document(db, vector_store, llm, payload.title, payload.content, current_user)
    return PolicyDocumentOut.model_validate(document)


@router.get("/policies", response_model=list[PolicyDocumentOut], dependencies=[Depends(require_permission("ai_assistant:manage"))])
def list_policy_documents(db: Session = Depends(get_db)):
    return [PolicyDocumentOut.model_validate(d) for d in db.query(PolicyDocument).all()]


@router.post("/chat", response_model=ChatAnswerResponse)
def chat(
    payload: ChatQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm: LLMClient = Depends(get_llm_client),
    vector_store: DocumentVectorStore = Depends(get_document_vector_store),
):
    """Self-service for any logged-in user -- no special permission needed,
    same as leave/attendance self-service actions."""
    if payload.session_id is not None:
        session = db.get(ChatSession, payload.session_id)
        if session is None or session.user_id != current_user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    else:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    message = ask_assistant(db, vector_store, llm, session, payload.question)
    return ChatAnswerResponse(session_id=session.id, message=ChatMessageOut.model_validate(message))


@router.get("/sessions/me", response_model=list[ChatSessionOut])
def get_my_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    return [ChatSessionOut.from_orm_session(s) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_session_messages(session_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found")
    return [ChatMessageOut.model_validate(m) for m in session.messages]
