"""In-process contract tests (no network, no embedding model needed).

Runs against the FastAPI app with embeddings disabled so the BM25 fallback is
exercised deterministically in CI.
"""

import os

os.environ.setdefault("USE_EMBEDDINGS", "0")

from fastapi.testclient import TestClient  # noqa: E402

from server.app import app  # noqa: E402

client = TestClient(app)

RUN = "run_test"
USER = f"eval:{RUN}:locomo:conv-0"
SESSION = f"eval:{RUN}:sample:0"


def _add(chunk: int, content: str, user: str = USER):
    req_id = f"eval:{RUN}:locomo_refined:conv-0:chunk-{chunk}"
    return client.post(
        "/add",
        json={
            "request_id": req_id,
            "messages": [{"role": "user", "timestamp": 1704067200000, "content": content}],
            "user_id": user,
            "session_id": SESSION,
        },
    )


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_add_echoes_contract_fields():
    resp = _add(0, "The Eiffel Tower is located in Paris, France.")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["request_id"] == f"eval:{RUN}:locomo_refined:conv-0:chunk-0"
    assert body["user_id"] == USER
    assert body["session_id"] == SESSION


def test_add_rejects_empty_content():
    resp = client.post(
        "/add",
        json={
            "request_id": "x",
            "messages": [{"role": "user", "content": "   "}],
            "user_id": USER,
            "session_id": SESSION,
        },
    )
    assert resp.status_code == 422


def test_search_returns_ranked_data():
    _add(1, "Marie Curie won the Nobel Prize in Physics in 1903.")
    _add(2, "The capital of Japan is Tokyo.")
    resp = client.post(
        "/search",
        json={"query": "Who won the Nobel Prize in Physics?", "user_id": USER, "top_k": 100},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list) and data
    assert all(item["id"] and item["content"] for item in data)
    assert len(data) <= 100
    # Most relevant memory should mention Marie Curie / Nobel.
    assert "curie" in data[0]["content"].lower() or "nobel" in data[0]["content"].lower()


def test_search_respects_top_k():
    for i in range(5):
        _add(10 + i, f"Fact number {i}: the sky appears blue due to Rayleigh scattering.")
    resp = client.post(
        "/search",
        json={"query": "why is the sky blue", "user_id": USER, "top_k": 2},
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) <= 2


def test_user_id_isolation():
    other = f"eval:{RUN}:locomo:conv-99"
    _add(0, "Secret memory that belongs only to the other user.", user=other)
    resp = client.post(
        "/search",
        json={"query": "secret memory", "user_id": f"eval:{RUN}:locomo:conv-empty", "top_k": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_empty_user_returns_empty_array():
    resp = client.post(
        "/search",
        json={"query": "anything", "user_id": "eval:none:locomo:conv-x", "top_k": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
