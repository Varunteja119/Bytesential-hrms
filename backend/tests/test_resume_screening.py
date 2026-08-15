import io

import pytest
from docx import Document

from app.core.dependencies import get_current_user
from app.database.models.rbac import Permission, Role
from app.database.models.user import User
from app.security.password import hash_password
from app.services.llm_client import get_llm_client
from app.services.storage import get_storage_client
from app.services.vector_store import get_vector_store


# --- Fakes standing in for Ollama / MinIO / ChromaDB ---

class FakeLLMClient:
    """Returns a scripted response instead of calling a real Ollama server."""

    def __init__(self, response_text: str = '{"score": 88, "summary": "Strong match for the role."}'):
        self.response_text = response_text
        self.generate_calls: list[str] = []
        self.embed_calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.generate_calls.append(prompt)
        return self.response_text

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        # Deterministic fake embedding derived from text length, so tests can
        # assert on it without needing a real embedding model.
        return [float(len(text) % 10), 0.0, 0.0]


class FakeStorageClient:
    """In-memory dict standing in for MinIO."""

    def __init__(self):
        self.files: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    def download(self, key: str) -> bytes:
        return self.files[key]


class FakeVectorStore:
    """In-memory dict standing in for ChromaDB, with the same 'closest first' contract."""

    def __init__(self):
        self.embeddings: dict[str, list[float]] = {}

    def upsert_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None:
        self.embeddings[candidate_id] = embedding

    def find_similar_candidates(self, embedding, n_results: int):
        def dist(e):
            return sum((a - b) ** 2 for a, b in zip(e, embedding))

        ranked = sorted(self.embeddings.items(), key=lambda kv: dist(kv[1]))[:n_results]
        return [{"candidate_id": cid, "distance": dist(emb)} for cid, emb in ranked]

    def delete_candidate_embedding(self, candidate_id: str) -> None:
        self.embeddings.pop(candidate_id, None)


def _make_docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_recruiter(db_session) -> None:
    perm = Permission(code="recruitment:manage")
    db_session.add(perm)
    role = Role(name="recruiter", permissions=[perm])
    db_session.add(role)
    user = User(
        email="recruiter@example.com",
        hashed_password=hash_password("supersecret1"),
        full_name="Recruiter",
        roles=[role],
    )
    db_session.add(user)
    db_session.commit()


def _auth_headers(client) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "recruiter@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_job(client, headers, requirements="5+ years Python, FastAPI, PostgreSQL") -> str:
    resp = client.post(
        "/api/v1/recruitment/jobs",
        json={"title": "Backend Engineer", "department": "Engineering", "description": "Build things.", "requirements": requirements},
        headers=headers,
    )
    return resp.json()["id"]


def _create_candidate(client, headers, job_id) -> str:
    resp = client.post(
        "/api/v1/recruitment/candidates",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "job_id": job_id},
        headers=headers,
    )
    return resp.json()["id"]


@pytest.fixture()
def fakes():
    return {"llm": FakeLLMClient(), "storage": FakeStorageClient(), "vector_store": FakeVectorStore()}


@pytest.fixture()
def client_with_fakes(client, fakes):
    """Overrides the AI service dependencies with fakes for the duration of a test."""
    from app.main import app

    app.dependency_overrides[get_llm_client] = lambda: fakes["llm"]
    app.dependency_overrides[get_storage_client] = lambda: fakes["storage"]
    app.dependency_overrides[get_vector_store] = lambda: fakes["vector_store"]
    yield client
    del app.dependency_overrides[get_llm_client]
    del app.dependency_overrides[get_storage_client]
    del app.dependency_overrides[get_vector_store]


def test_upload_resume_extracts_and_caches_text(client_with_fakes, db_session, fakes):
    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    docx_bytes = _make_docx_bytes("Experienced Python developer, 6 years, FastAPI expert.")
    resp = client_with_fakes.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/resume",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Python developer" in body["resume_text"]
    assert body["resume_storage_key"] == f"resumes/{candidate_id}/resume.docx"
    assert fakes["storage"].files[body["resume_storage_key"]] == docx_bytes


def test_upload_unsupported_file_type_rejected(client_with_fakes, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    resp = client_with_fakes.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/resume",
        files={"file": ("resume.txt", b"plain text resume", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_screen_without_resume_rejected(client_with_fakes, db_session):
    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    resp = client_with_fakes.post(f"/api/v1/recruitment/candidates/{candidate_id}/screen", headers=headers)
    assert resp.status_code == 400


def test_screen_candidate_end_to_end(client_with_fakes, db_session, fakes):
    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers, requirements="5+ years Python, FastAPI, PostgreSQL")
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    docx_bytes = _make_docx_bytes("Experienced Python developer, 6 years, FastAPI expert.")
    client_with_fakes.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/resume",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers,
    )

    resp = client_with_fakes.post(f"/api/v1/recruitment/candidates/{candidate_id}/screen", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_score"] == 88.0
    assert body["ai_summary"] == "Strong match for the role."
    assert body["status"] == "screening"  # auto-advanced from "applied"

    # confirm the prompt actually included the job requirements and resume text
    assert "FastAPI, PostgreSQL" in fakes["llm"].generate_calls[0]
    assert "Python developer" in fakes["llm"].generate_calls[0]

    # confirm the embedding got indexed
    assert candidate_id in fakes["vector_store"].embeddings


def test_screening_handles_messy_llm_response(client_with_fakes, db_session, fakes):
    """LLM wraps its JSON in markdown fences -- the parser should still recover it."""
    fakes["llm"].response_text = '```json\n{"score": 42, "summary": "Partial match."}\n```'

    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    docx_bytes = _make_docx_bytes("Some resume content.")
    client_with_fakes.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/resume",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers,
    )
    resp = client_with_fakes.post(f"/api/v1/recruitment/candidates/{candidate_id}/screen", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ai_score"] == 42.0


def test_screening_502s_on_unparseable_llm_response(client_with_fakes, db_session, fakes):
    fakes["llm"].response_text = "I refuse to assess this resume."

    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)
    candidate_id = _create_candidate(client_with_fakes, headers, job_id)

    docx_bytes = _make_docx_bytes("Some resume content.")
    client_with_fakes.post(
        f"/api/v1/recruitment/candidates/{candidate_id}/resume",
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers,
    )
    resp = client_with_fakes.post(f"/api/v1/recruitment/candidates/{candidate_id}/screen", headers=headers)
    assert resp.status_code == 502


def test_similar_candidates_ranking(client_with_fakes, db_session, fakes):
    _make_recruiter(db_session)
    headers = _auth_headers(client_with_fakes)
    job_id = _create_job(client_with_fakes, headers)

    # Two candidates, screened with different resume text -> different fake embeddings
    c1 = _create_candidate(client_with_fakes, headers, job_id)
    c2 = _create_candidate(client_with_fakes, headers, job_id)

    for cid, text in [(c1, "short resume"), (c2, "a much longer and more detailed resume text here")]:
        docx_bytes = _make_docx_bytes(text)
        client_with_fakes.post(
            f"/api/v1/recruitment/candidates/{cid}/resume",
            files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers,
        )
        client_with_fakes.post(f"/api/v1/recruitment/candidates/{cid}/screen", headers=headers)

    resp = client_with_fakes.get(f"/api/v1/recruitment/jobs/{job_id}/similar-candidates?limit=2", headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert {r["candidate"]["id"] for r in results} == {c1, c2}
