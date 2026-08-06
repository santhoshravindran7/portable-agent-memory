"""Hybrid retrieval: dense embeddings blended with BM25 lexical scoring.

The contract only asks us to return a relevance-ordered ``data`` array per
``user_id``. We combine two complementary signals:

* **Dense** — sentence-transformer cosine similarity (semantic recall).
* **Lexical** — BM25 Okapi over tokenized memories (exact-term precision).

Both are min-max normalized per query and blended by ``alpha``. If the
embedding model cannot be loaded (offline build, missing dependency), the
retriever degrades gracefully to BM25-only so the contract always holds.
"""

from __future__ import annotations

import re
import threading

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _minmax(scores: list[float]) -> list[float]:
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-12:
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


class HybridRetriever:
    """Per-user hybrid retriever with strict ``user_id`` isolation."""

    def __init__(
        self,
        use_embeddings: bool = True,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        alpha: float = 0.6,
    ) -> None:
        self.alpha = alpha
        self._lock = threading.RLock()
        # user_id -> {"docs": [...], "ids": set(), "bm25": obj|None, "dirty": bool}
        self._users: dict[str, dict] = {}
        self._model = None
        self._model_name = model_name
        if use_embeddings:
            self._try_load_model()

    @property
    def embeddings_enabled(self) -> bool:
        return self._model is not None

    def _try_load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        except Exception:  # noqa: BLE001 - any load failure -> lexical fallback
            self._model = None

    def add(self, user_id: str, doc_id: str, content: str, created_at: str) -> None:
        with self._lock:
            user = self._users.setdefault(
                user_id, {"docs": [], "ids": set(), "bm25": None, "dirty": True}
            )
            if doc_id in user["ids"]:
                return
            emb = None
            if self._model is not None:
                emb = self._model.encode([content], normalize_embeddings=True)[0]
            user["docs"].append(
                {
                    "id": doc_id,
                    "content": content,
                    "created_at": created_at,
                    "tokens": _tokenize(content),
                    "emb": emb,
                }
            )
            user["ids"].add(doc_id)
            user["dirty"] = True

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int,
        options: list[str] | None = None,
    ) -> list[dict]:
        with self._lock:
            user = self._users.get(user_id)
            if not user or not user["docs"]:
                return []
            docs = user["docs"]

            # Options bias retrieval only (never the answer); the query text is
            # preserved as required, we just widen recall for choice questions.
            retrieval_query = query
            if options:
                retrieval_query = f"{query} " + " ".join(options)

            bm25_norm = _minmax(self._bm25_scores(user, _tokenize(retrieval_query)))
            dense = self._dense_scores(docs, retrieval_query)
            if dense is not None:
                dense_norm = _minmax(dense)
                final = [
                    self.alpha * d + (1 - self.alpha) * b
                    for d, b in zip(dense_norm, bm25_norm)
                ]
            else:
                final = bm25_norm

            ranked = sorted(zip(docs, final), key=lambda pair: pair[1], reverse=True)
            top = ranked[: max(0, top_k)]
            return [
                {
                    "id": doc["id"],
                    "content": doc["content"],
                    "score": round(float(score), 6),
                    "created_at": doc["created_at"],
                }
                for doc, score in top
            ]

    def _bm25_scores(self, user: dict, query_tokens: list[str]) -> list[float]:
        try:
            from rank_bm25 import BM25Okapi
        except Exception:  # noqa: BLE001
            return [0.0] * len(user["docs"])
        if user["dirty"] or user["bm25"] is None:
            corpus = [doc["tokens"] for doc in user["docs"]]
            user["bm25"] = BM25Okapi(corpus)
            user["dirty"] = False
        if not query_tokens:
            return [0.0] * len(user["docs"])
        return list(user["bm25"].get_scores(query_tokens))

    def _dense_scores(self, docs: list[dict], query: str) -> list[float] | None:
        if self._model is None:
            return None
        import numpy as np

        q = self._model.encode([query], normalize_embeddings=True)[0]
        return [float(np.dot(q, doc["emb"])) for doc in docs]
