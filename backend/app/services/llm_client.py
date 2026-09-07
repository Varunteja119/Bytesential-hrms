from typing import Protocol

import httpx

from app.config.settings import settings
from app.core.exceptions import AppError


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...
    def embed(self, text: str) -> list[float]: ...


class OllamaClient:
    def __init__(self, base_url: str, model: str, embedding_model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        import logging
        logger = logging.getLogger("bytesentinel.llm")
        try:
            resp = httpx.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "stream": False}, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()["response"]
        except httpx.HTTPError as exc:
            logger.warning(f"Ollama generate failed ({exc}). Falling back to MockLLMClient.")
            return MockLLMClient().generate(prompt)

    def embed(self, text: str) -> list[float]:
        import logging
        logger = logging.getLogger("bytesentinel.llm")
        try:
            resp = httpx.post(f"{self.base_url}/api/embeddings", json={"model": self.embedding_model, "prompt": text}, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()["embedding"]
        except httpx.HTTPError as exc:
            logger.warning(f"Ollama embed failed ({exc}). Falling back to MockLLMClient.")
            return MockLLMClient().embed(text)


class MockLLMClient:
    def generate(self, prompt: str) -> str:
        return '{"score": 88, "summary": "Strong match for the role."}'

    def embed(self, text: str) -> list[float]:
        return [float(len(text) % 10), 0.0, 0.0]


def get_llm_client() -> LLMClient:
    """FastAPI dependency — override with a fake in tests or mock offline mode."""
    import os
    if os.getenv("MOCK_LLM") == "true":
        return MockLLMClient()
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        embedding_model=settings.ollama_embedding_model,
        timeout=20.0,
    )
