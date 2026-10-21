"""Test login (JWT), protected endpoints and streaming, with fake agents."""
from fastapi.testclient import TestClient

from querymesh import api, cache
from querymesh.cache import cache_key
from tests.test_graph import fake_skills

client = TestClient(api.app)


def token() -> str:
    response = client.post("/token", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_wrong_password():
    assert client.post("/token", data={"username": "admin", "password": "x"}).status_code == 401


def test_ask_needs_token():
    assert client.post("/ask", json={"question": "What is RRF?"}).status_code == 401


def test_ask_and_stream(monkeypatch):
    fake_skills(monkeypatch, grounded_sequence=(True, True))
    monkeypatch.setattr(cache, "get", lambda q: None)
    monkeypatch.setattr(cache, "put", lambda q, r: None)
    headers = {"Authorization": f"Bearer {token()}"}
    answer = client.post("/ask", json={"question": "What is RRF?"}, headers=headers).json()
    assert answer["grounded"] is True and answer["cached"] is False
    stream = client.post("/ask/stream", json={"question": "What is RRF?"}, headers=headers).text
    assert "event: step" in stream and "event: final" in stream


def test_cache_key_ignores_case_and_spaces():
    assert cache_key("What is  RAG?") == cache_key("  what is rag? ")
    assert cache_key("What is RAG?") != cache_key("What is RRF?")
