"""Evaluation metrics for Portable Agent Memory transfers.

Implements the two metrics defined in §10 of the PAM specification:

* **Transfer Continuity Score (TCS)** — does the target agent complete the
  source agent's tasks as effectively after re-hydration?
* **Re-Hydration Fidelity (RHF)** — how semantically similar are the target
  agent's responses to the source agent's on an aligned probe set?

The spec describes RHF in terms of text embeddings (e.g. ``text-embedding-3-large``)
and cosine similarity. Embedding models are an optional, heavyweight dependency,
so this module is **embedding-agnostic**: pass any ``embed_fn`` that maps text to a
vector and similarity is computed with cosine distance. When no ``embed_fn`` is
supplied, a dependency-free lexical embedder (bag-of-words term frequencies) is
used so the metric works out of the box for tests, demos, and CI.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Callable, Sequence

# An embedder maps a string to a dense or sparse numeric vector.
Embedder = Callable[[str], Sequence[float]]

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ----------------------------------------------------------------------
# Similarity primitives
# ----------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric tokenization used by the default lexical embedder."""
    return _TOKEN_RE.findall(text.lower())


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two equal-length numeric vectors.

    Returns a value in ``[-1.0, 1.0]`` (``0.0`` if either vector is all zeros).
    """
    if len(a) != len(b):
        raise ValueError(f"Vectors must be the same length (got {len(a)} and {len(b)})")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _lexical_cosine(a: str, b: str) -> float:
    """Cosine similarity over bag-of-words term-frequency vectors.

    Dependency-free fallback for when no embedding model is available. Operates
    on the shared vocabulary of the two texts so no fixed dimensionality is
    required.
    """
    counts_a = Counter(_tokenize(a))
    counts_b = Counter(_tokenize(b))
    if not counts_a or not counts_b:
        return 0.0
    vocab = set(counts_a) | set(counts_b)
    vec_a = [counts_a.get(t, 0) for t in vocab]
    vec_b = [counts_b.get(t, 0) for t in vocab]
    return cosine_similarity(vec_a, vec_b)


def semantic_similarity(
    response_a: str,
    response_b: str,
    embed_fn: Embedder | None = None,
) -> float:
    """Semantic similarity between two responses, in ``[0.0, 1.0]``.

    Args:
        response_a: First response text.
        response_b: Second response text.
        embed_fn: Optional embedder mapping text to a vector. When provided,
            similarity is the cosine similarity of the two embeddings. When
            omitted, a dependency-free lexical (bag-of-words) similarity is used.

    The result is clamped to ``[0.0, 1.0]`` so it reads as a fidelity fraction
    (negative cosine values and floating-point overshoot above ``1.0`` are
    both bounded).
    """
    if embed_fn is not None:
        sim = cosine_similarity(embed_fn(response_a), embed_fn(response_b))
    else:
        sim = _lexical_cosine(response_a, response_b)
    return min(1.0, max(0.0, sim))


# ----------------------------------------------------------------------
# Transfer Continuity Score (§10.1)
# ----------------------------------------------------------------------


def task_success_rate(results: Sequence[bool]) -> float:
    """Proportion of probe tasks that succeeded.

    Raises:
        ValueError: if ``results`` is empty.
    """
    if not results:
        raise ValueError("results must be a non-empty sequence")
    return sum(1 for r in results if r) / len(results)


def transfer_continuity_score(
    source_results: Sequence[bool],
    target_results: Sequence[bool],
) -> float:
    """Transfer Continuity Score (TCS) — spec §10.1.

    ``TCS = task_success_rate(target_after) / task_success_rate(source_before)``

    Args:
        source_results: Per-task success/failure for the source agent using its
            full, native memory.
        target_results: Per-task success/failure for the target agent after
            re-hydrating the source agent's exported memory. Must align 1:1 with
            ``source_results`` (same probe tasks, same order).

    Returns:
        The continuity ratio. ``>= 1.0`` means the target matched or exceeded the
        source; lower values indicate degradation (see :func:`interpret_tcs`).

    Raises:
        ValueError: if the result lists differ in length, are empty, or the
            source completed no tasks (ratio undefined).
    """
    if len(source_results) != len(target_results):
        raise ValueError(
            "source_results and target_results must align 1:1 "
            f"(got {len(source_results)} and {len(target_results)})"
        )
    source_rate = task_success_rate(source_results)
    target_rate = task_success_rate(target_results)
    if source_rate == 0.0:
        raise ValueError(
            "Source agent completed no probe tasks; TCS is undefined "
            "(cannot measure continuity against a zero baseline)"
        )
    return target_rate / source_rate


def interpret_tcs(score: float) -> str:
    """Human-readable interpretation band for a TCS value (spec §10.1)."""
    if score >= 1.0:
        return "Target matches or exceeds source performance."
    if score >= 0.8:
        return "Minor performance degradation; acceptable for most use cases."
    if score >= 0.5:
        return "Significant degradation; re-hydration parameters should be tuned."
    return "Severe degradation; investigate compatibility issues."


# ----------------------------------------------------------------------
# Re-Hydration Fidelity (§10.2)
# ----------------------------------------------------------------------


def rehydration_fidelity(
    source_responses: Sequence[str],
    target_responses: Sequence[str],
    embed_fn: Embedder | None = None,
) -> float:
    """Re-Hydration Fidelity (RHF) — spec §10.2.

    ``RHF = mean(semantic_similarity(target_i, source_i))`` over an aligned probe set.

    Args:
        source_responses: Responses from the source agent (full memory).
        target_responses: Responses from the target agent (re-hydrated memory),
            aligned 1:1 with ``source_responses``.
        embed_fn: Optional embedder (see :func:`semantic_similarity`).

    Returns:
        Mean pairwise similarity in ``[0.0, 1.0]`` (see :func:`interpret_rhf`).

    Raises:
        ValueError: if the response lists differ in length or are empty.
    """
    if len(source_responses) != len(target_responses):
        raise ValueError(
            "source_responses and target_responses must align 1:1 "
            f"(got {len(source_responses)} and {len(target_responses)})"
        )
    if not source_responses:
        raise ValueError("response lists must be non-empty")
    sims = [
        semantic_similarity(t, s, embed_fn)
        for s, t in zip(source_responses, target_responses)
    ]
    return sum(sims) / len(sims)


def interpret_rhf(score: float) -> str:
    """Human-readable interpretation band for an RHF value (spec §10.2)."""
    if score >= 0.9:
        return "High fidelity; responses are semantically near-identical."
    if score >= 0.7:
        return "Good fidelity; key information preserved, phrasing varies."
    if score >= 0.5:
        return "Moderate fidelity; some information loss or drift."
    return "Low fidelity; significant information loss."
