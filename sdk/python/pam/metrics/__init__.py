"""Evaluation metrics for Portable Agent Memory transfers (spec §10).

Quantifies how faithfully a target agent reproduces a source agent's behavior
after re-hydrating exported memory:

* :func:`transfer_continuity_score` (TCS) — task-completion continuity.
* :func:`rehydration_fidelity` (RHF) — semantic similarity of responses.

High-level helpers run the full evaluation protocol against agent callables and
emit a standardized :class:`EvaluationReport`.
"""

from .evaluation import (
    Embedder,
    cosine_similarity,
    interpret_rhf,
    interpret_tcs,
    rehydration_fidelity,
    semantic_similarity,
    task_success_rate,
    transfer_continuity_score,
)
from .probe import (
    AgentFn,
    Grader,
    ProbeCategory,
    ProbeTask,
    collect_responses,
    default_grader,
    run_probe_tasks,
)
from .report import (
    AgentDescriptor,
    EvaluationReport,
    Metrics,
    RehydrationConfigSummary,
    evaluate_transfer,
)

__all__ = [
    "AgentDescriptor",
    "AgentFn",
    "Embedder",
    "EvaluationReport",
    "Grader",
    "Metrics",
    "ProbeCategory",
    "ProbeTask",
    "RehydrationConfigSummary",
    "collect_responses",
    "cosine_similarity",
    "default_grader",
    "evaluate_transfer",
    "interpret_rhf",
    "interpret_tcs",
    "rehydration_fidelity",
    "run_probe_tasks",
    "semantic_similarity",
    "task_success_rate",
    "transfer_continuity_score",
]
