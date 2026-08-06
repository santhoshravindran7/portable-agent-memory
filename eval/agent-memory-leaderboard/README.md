# Portable Agent Memory — Agent Memory Leaderboard Adapter

A thin, self-contained **Add / Search** service that lets the
[Portable Agent Memory](https://github.com/santhoshravindran7/portable-agent-memory)
(PAM) protocol be evaluated on the Agent Memory Leaderboard via the
**code-submission route** — maintainers build the Docker image and run it on
their own infrastructure, so no public endpoint or API key is ever exposed by us.

## Why this is a natural fit

The leaderboard scores *retrieval-QA over per-user memory*. This adapter maps
that onto PAM's core guarantees:

| Leaderboard need | PAM mechanism used here |
| --- | --- |
| Store each conversation chunk under a `user_id` | Each message → a content-addressed `EpisodicEntry` in a per-user `MemoryArtifact` |
| Return only that user's memories | Strict `user_id` isolation in both store and retriever |
| Trustworthy retrieved evidence | Every returned memory's **BLAKE3 content hash is re-verified** before it reaches the answer model |
| Relevance-ranked results | Hybrid **dense (sentence-transformers) + lexical (BM25)** scoring |

## Architecture

```
                 POST /add                         POST /search
Platform ───────────────────────►  FastAPI app  ◄───────────────────────  Platform
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                        ▼
              MemoryStore (PAM)                        HybridRetriever
        EpisodicEntry + MemoryArtifact           dense (MiniLM) ⊕ BM25 Okapi
        BLAKE3 content-addressed, per-user        min-max blended, per-user
```

* `server/store.py` — PAM-backed, thread-safe, per-`user_id` artifact store.
* `server/retriever.py` — hybrid retriever; degrades to BM25-only if the
  embedding model is unavailable.
* `server/app.py` — the `/add`, `/search`, `/health` HTTP contract.

## Endpoints

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | none | any `2xx` == healthy |
| `POST` | `/add` | optional | **synchronous** — 200 only after messages are persisted *and* searchable |
| `POST` | `/search` | optional | returns `{"data": [...]}` ranked best-first, `≤ top_k`, scoped to `user_id` |

Authentication, when `MEMORY_API_KEY` is set, is accepted via `X-Api-Key`,
`Authorization: Bearer <key>`, or `Authorization: Token <key>`.

Request/response schemas follow the platform's fixed contract exactly
(`request_id` / `user_id` / `session_id` are echoed byte-for-byte on `/add`;
each `/search` item carries a non-empty `id` and `content`).

## Build & run (code-submission route)

Build **from the repository root** so the PAM SDK is in the Docker context:

```bash
docker build -f eval/agent-memory-leaderboard/Dockerfile -t pam-memory-server .
docker run -p 8080:8080 pam-memory-server
# optional auth:
docker run -e MEMORY_API_KEY=your-key -p 8080:8080 pam-memory-server
```

Documented entrypoint: `uvicorn server.app:app --host 0.0.0.0 --port 8080 --workers 1`
(single worker — retrieval state is in-process and shared across requests).

The embedding model is **pre-downloaded into the image at build time**, so no
runtime network access is required.

### Lightweight (offline / BM25-only) build

```bash
docker build -f eval/agent-memory-leaderboard/Dockerfile \
  --build-arg REQUIREMENTS=requirements-lite.txt --build-arg PREFETCH_MODEL=0 \
  -t pam-memory-server:lite .
docker run -e USE_EMBEDDINGS=0 -p 8080:8080 pam-memory-server:lite
```

## Configuration

| Env var | Default | Description |
| --- | --- | --- |
| `MEMORY_API_KEY` | *(unset)* | If set, required on `/add` and `/search` |
| `USE_EMBEDDINGS` | `1` | `0` → BM25-only retrieval |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Dense encoder |
| `HYBRID_ALPHA` | `0.6` | Blend weight: `final = alpha·dense + (1-alpha)·lexical` |
| `VERIFY_ON_SEARCH` | `1` | Re-verify BLAKE3 integrity of each returned memory |

## Local verification

Contract tests (no network, no model — exercises the BM25 fallback):

```bash
pip install ./sdk/python
pip install -r eval/agent-memory-leaderboard/requirements-lite.txt pytest
cd eval/agent-memory-leaderboard
USE_EMBEDDINGS=0 python -m pytest tests -q
```

End-to-end smoke against a running container (mimics the platform loop):

```bash
python eval/agent-memory-leaderboard/smoke/mock_platform.py http://localhost:8080
```

## Original-work disclosure

Per the leaderboard's code-review policy:

* **Original authors / method:** Portable Agent Memory protocol and SDK by
  **Santhosh Kumar Ravindran** (Apache-2.0). This adapter is original work by
  the same author; it does **not** reproduce any third-party paper or repository.
* **Method summary:** benchmark messages are stored as BLAKE3
  content-addressed PAM episodic entries; retrieval is a min-max-blended hybrid
  of sentence-transformer cosine similarity and BM25 Okapi, scoped per
  `user_id`; returned memories are integrity-verified before answering.
* **Third-party components:** `sentence-transformers` (all-MiniLM-L6-v2) and
  `rank-bm25`, used as standard off-the-shelf retrieval libraries.
* **Changes vs. the base PAM SDK:** none to the SDK itself — this adapter only
  *consumes* the public SDK API (`EpisodicEntry`, `MemoryArtifact`) and adds an
  HTTP contract + retrieval layer around it.

## Data handling

Evaluation data received via `/add` is held only in process memory for the
duration of the job and is used solely to answer that job's `/search` calls. It
is not persisted to disk, logged in full, or reused for any other purpose.
