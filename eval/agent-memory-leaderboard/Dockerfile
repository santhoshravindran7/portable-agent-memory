# syntax=docker/dockerfile:1
#
# Build from the REPOSITORY ROOT so the PAM SDK is in context:
#   docker build -f eval/agent-memory-leaderboard/Dockerfile -t pam-memory-server .
#   docker run -p 8080:8080 pam-memory-server
#
# Lightweight (BM25-only, no torch) build:
#   docker build -f eval/agent-memory-leaderboard/Dockerfile \
#     --build-arg REQUIREMENTS=requirements-lite.txt --build-arg PREFETCH_MODEL=0 \
#     -t pam-memory-server:lite .
#   docker run -e USE_EMBEDDINGS=0 -p 8080:8080 pam-memory-server:lite

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 1) Install the Portable Agent Memory SDK from local source.
COPY sdk/python /app/pam-sdk
RUN pip install /app/pam-sdk

# 2) Install adapter dependencies (full by default, lite via build-arg).
ARG REQUIREMENTS=requirements.txt
COPY eval/agent-memory-leaderboard/${REQUIREMENTS} /app/requirements.txt
RUN pip install -r /app/requirements.txt

# 3) Pre-download the embedding model INTO the image so no runtime network is
#    required (the evaluation network may be restricted). Skip for lite builds.
ARG PREFETCH_MODEL=1
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}
RUN if [ "$PREFETCH_MODEL" = "1" ]; then \
        python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBEDDING_MODEL'])"; \
    fi

# 4) Copy the adapter source.
COPY eval/agent-memory-leaderboard/server /app/server
COPY eval/agent-memory-leaderboard/smoke /app/smoke

EXPOSE 8080

# Single worker: retrieval state is in-process and shared across requests.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
