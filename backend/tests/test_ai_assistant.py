from app.database.models.rbac import Permission, Role
from app.database.models.user import User
from app.security.password import hash_password
from app.services.llm_client import get_llm_client
from app.services.vector_store import get_document_vector_store


class FakeLLMClient:
    """Deterministic fake: embed() returns a vector based on text content so
    similar text -> similar vector, and generate() returns a scripted answer."""

    def __init__(self, answer: str = "Based on the policy, you get 12 days of casual leave per year."):
        self.answer = answer
        self.generate_calls: list[str] = []
        self.embed_calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self.answer

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        # crude but deterministic: embedding derived from word overlap with "leave" and "casual"
        has_leave = 1.0 if "leave" in text.lower() else 0.0
        has_casual = 1.0 if "casual" in text.lower() else 0.0
        return [has_leave, has_casual, float(len(text) % 10)]


class FakeDocumentVectorStore:
    def __init__(self):
        self.chunks: dict[str, dict] = {}

    def upsert_chunk(self, chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self.chunks[chunk_id] = {"text": text, "embedding": embedding, "metadata": metadata}

    def find_relevant_chunks(self, embedding: list[float], n_results: int):
        def dist(e):
            return sum((a - b) ** 2 for a, b in zip(e, embedding))
        ranked = sorted(self.chunks.items(), key=lambda kv: dist(kv[1]["embedding"]))[:n_results]
        return [{"chunk_id": cid, "text": c["text"], "metadata": c["metadata"], "distance": dist(c["embedding"])} for cid, c in ranked]

    def delete_document_chunks(self, document_id: str) -> None:
        self.chunks = {k: v for k, v in self.chunks.items() if v["metadata"]["document_id"] != document_id}


def _make_hr_user(db_session) -> None:
    perm = Permission(code="ai_assistant:manage")
    db_session.add(perm)
    role = Role(name="hr_manager", permissions=[perm])
    db_session.add(role)
    user = User(email="hr@example.com", hashed_password=hash_password("supersecret1"), full_name="HR Person", roles=[role])
    db_session.add(user)
    db_session.commit()


def _make_employee_user(db_session, email="employee@example.com") -> None:
    user = User(email=email, hashed_password=hash_password("supersecret1"), full_name="Employee")
    db_session.add(user)
    db_session.commit()


def _login(client, email, password="supersecret1") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _override_ai_deps(app, llm, vector_store):
    app.dependency_overrides[get_llm_client] = lambda: llm
    app.dependency_overrides[get_document_vector_store] = lambda: vector_store


def _clear_ai_deps(app):
    del app.dependency_overrides[get_llm_client]
    del app.dependency_overrides[get_document_vector_store]


def test_upload_policy_document_requires_permission(client, db_session):
    _make_employee_user(db_session)
    headers = _login(client, "employee@example.com")
    resp = client.post("/api/v1/ai-assistant/policies", json={"title": "Leave Policy", "content": "Employees get 12 days of casual leave."}, headers=headers)
    assert resp.status_code == 403


def test_upload_policy_document_chunks_and_embeds(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient()
    fake_store = FakeDocumentVectorStore()
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_hr_user(db_session)
        headers = _login(client, "hr@example.com")
        resp = client.post("/api/v1/ai-assistant/policies", json={"title": "Leave Policy", "content": "Employees get 12 days of casual leave per year.\n\nUnused leave does not carry over."}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["chunk_count"] >= 1
        assert len(fake_store.chunks) == resp.json()["chunk_count"]
        assert len(fake_llm.embed_calls) == resp.json()["chunk_count"]
    finally:
        _clear_ai_deps(app)


def test_chat_creates_new_session_and_retrieves_relevant_policy(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient(answer="You get 12 days of casual leave per year.")
    fake_store = FakeDocumentVectorStore()
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_hr_user(db_session)
        hr_headers = _login(client, "hr@example.com")
        client.post("/api/v1/ai-assistant/policies", json={"title": "Leave Policy", "content": "Employees get 12 days of casual leave per year."}, headers=hr_headers)
        client.post("/api/v1/ai-assistant/policies", json={"title": "Dress Code", "content": "Business casual attire is expected in the office."}, headers=hr_headers)

        _make_employee_user(db_session)
        emp_headers = _login(client, "employee@example.com")

        resp = client.post("/api/v1/ai-assistant/chat", json={"question": "How many days of casual leave do I get?"}, headers=emp_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"]["role"] == "assistant"
        assert body["message"]["content"] == "You get 12 days of casual leave per year."
        assert "Leave Policy" in body["message"]["source_documents"]
        assert body["session_id"]

        # confirm the retrieved context (not the dress code doc) made it into the actual prompt
        assert "12 days of casual leave" in fake_llm.generate_calls[0]
        assert "How many days of casual leave" in fake_llm.generate_calls[0]
    finally:
        _clear_ai_deps(app)


def test_chat_continues_existing_session(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient()
    fake_store = FakeDocumentVectorStore()
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_employee_user(db_session)
        headers = _login(client, "employee@example.com")

        first = client.post("/api/v1/ai-assistant/chat", json={"question": "What is our leave policy?"}, headers=headers)
        session_id = first.json()["session_id"]

        second = client.post("/api/v1/ai-assistant/chat", json={"question": "What about sick leave?", "session_id": session_id}, headers=headers)
        assert second.status_code == 200
        assert second.json()["session_id"] == session_id

        messages = client.get(f"/api/v1/ai-assistant/sessions/{session_id}/messages", headers=headers).json()
        assert len(messages) == 4  # 2 questions + 2 answers
    finally:
        _clear_ai_deps(app)


def test_chat_no_relevant_policy_still_answers_gracefully(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient(answer="This isn't covered in the available policy documents. Please contact HR directly.")
    fake_store = FakeDocumentVectorStore()  # empty -- no policies uploaded at all
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_employee_user(db_session)
        headers = _login(client, "employee@example.com")
        resp = client.post("/api/v1/ai-assistant/chat", json={"question": "What is the parking policy?"}, headers=headers)
        assert resp.status_code == 200
        assert "not covered" in resp.json()["message"]["content"].lower() or "contact hr" in resp.json()["message"]["content"].lower()
        assert resp.json()["message"]["source_documents"] is None
        # confirm the prompt correctly signaled no context was found
        assert "no relevant policy documents found" in fake_llm.generate_calls[0]
    finally:
        _clear_ai_deps(app)


def test_user_cannot_access_another_users_session(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient()
    fake_store = FakeDocumentVectorStore()
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_employee_user(db_session, email="emp1@example.com")
        _make_employee_user(db_session, email="emp2@example.com")
        headers1 = _login(client, "emp1@example.com")
        headers2 = _login(client, "emp2@example.com")

        resp = client.post("/api/v1/ai-assistant/chat", json={"question": "test"}, headers=headers1)
        session_id = resp.json()["session_id"]

        forbidden = client.get(f"/api/v1/ai-assistant/sessions/{session_id}/messages", headers=headers2)
        assert forbidden.status_code == 404  # not 403 -- deliberately doesn't confirm the session exists to another user
    finally:
        _clear_ai_deps(app)


def test_my_sessions_lists_only_own_sessions(client, db_session):
    from app.main import app
    fake_llm = FakeLLMClient()
    fake_store = FakeDocumentVectorStore()
    _override_ai_deps(app, fake_llm, fake_store)
    try:
        _make_employee_user(db_session, email="emp1@example.com")
        _make_employee_user(db_session, email="emp2@example.com")
        headers1 = _login(client, "emp1@example.com")
        headers2 = _login(client, "emp2@example.com")

        client.post("/api/v1/ai-assistant/chat", json={"question": "q1"}, headers=headers1)
        client.post("/api/v1/ai-assistant/chat", json={"question": "q2"}, headers=headers2)

        sessions1 = client.get("/api/v1/ai-assistant/sessions/me", headers=headers1).json()
        assert len(sessions1) == 1
        assert sessions1[0]["title"] == "q1"
    finally:
        _clear_ai_deps(app)
