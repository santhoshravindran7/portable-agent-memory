"""FastAPI application implementing the Agent Memory Leaderboard Add/Search contract.

Endpoints
---------
* ``GET  /health`` — unauthenticated liveness check (any 2xx == healthy).
* ``POST /add``    — synchronous ingest; returns 200 only after the messages are
  persisted **and** searchable.
* ``POST /search`` — per-question retrieval scoped strictly to ``user_id``.

Authentication (optional): when ``MEMORY_API_KEY`` is set, ``/add`` and
``/search`` require it via ``X-Api-Key``, ``Authorization: Bearer <key>`` or
``Authorization: Token <key>``. ``/health`` is always open.
"""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .config import Settings
from .retriever import HybridRetriever
from .store import MemoryStore

settings = Settings()
store = MemoryStore()
retriever = HybridRetriever(
    use_embeddings=settings.use_embeddings,
    model_name=settings.embedding_model,
    alpha=settings.hybrid_alpha,
)

app = FastAPI(title="PAM Agent Memory Leaderboard Adapter", version="0.1.0")


# --------------------------------------------------------------------------- #
# Request / response schemas (mirrors the fixed platform contract)
# --------------------------------------------------------------------------- #
class AddMessage(BaseModel):
    role: str
    content: str
    timestamp: int | None = None


class AddRequest(BaseModel):
    request_id: str
    messages: list[AddMessage]
    user_id: str
    session_id: str


class SearchRequest(BaseModel):
    query: str
    options: list[str] | None = None
    user_id: str
    top_k: int = 100


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def _check_auth(x_api_key: str | None, authorization: str | None) -> None:
    key = settings.api_key
    if not key:
        return
    provided: str | None = None
    if x_api_key:
        provided = x_api_key.strip()
    elif authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() in ("bearer", "token"):
            provided = parts[1].strip()
        else:
            provided = authorization.strip()
    if provided != key:
        raise HTTPException(status_code=401, detail={"reason": "invalid or missing API key"})


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "embeddings": retriever.embeddings_enabled,
        "users": len(store.stats()),
    }


@app.post("/add")
def add(
    req: AddRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    authorization: str | None = Header(default=None),
) -> dict:
    _check_auth(x_api_key, authorization)
    if not req.messages:
        raise HTTPException(status_code=422, detail={"reason": "messages must be non-empty"})

    for message in req.messages:
        if not message.content or not message.content.strip():
            raise HTTPException(
                status_code=422, detail={"reason": "message content must be non-empty"}
            )
        # Synchronous: persist to PAM, then index — both complete before we return.
        record = store.add_message(
            user_id=req.user_id,
            session_id=req.session_id,
            role=message.role,
            content=message.content,
            timestamp_ms=message.timestamp,
        )
        retriever.add(req.user_id, record.id, record.content, record.created_at)

    return {
        "success": True,
        "request_id": req.request_id,
        "user_id": req.user_id,
        "session_id": req.session_id,
    }


@app.post("/search")
def search(
    req: SearchRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    authorization: str | None = Header(default=None),
) -> dict:
    _check_auth(x_api_key, authorization)
    results = retriever.search(
        user_id=req.user_id,
        query=req.query,
        top_k=req.top_k,
        options=req.options,
    )

    # Portable Agent Memory guarantee: re-verify each returned memory's BLAKE3
    # content hash before it reaches the answer model. Tampered entries are dropped.
    if settings.verify_on_search and results:
        results = [r for r in results if store.verify_entry(req.user_id, r["id"])]

    return {"data": results}
