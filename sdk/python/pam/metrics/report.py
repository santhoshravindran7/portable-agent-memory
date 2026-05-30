"""Standardized evaluation report (spec §10.3) and a high-level orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..models.artifact import MemoryArtifact
from .evaluation import (
    Embedder,
    interpret_rhf,
    interpret_tcs,
    rehydration_fidelity,
    transfer_continuity_score,
)
from .probe import (
    AgentFn,
    Grader,
    ProbeTask,
    collect_responses,
    default_grader,
    run_probe_tasks,
)


class AgentDescriptor(BaseModel):
    """Minimal identifying info for an agent in a report."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = ""
    model_family: str = ""


class RehydrationConfigSummary(BaseModel):
    """Re-hydration parameters that were in effect during evaluation."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    token_budget: int = 0
    relevance_threshold: float = 0.0
    format_style: str = ""


class Metrics(BaseModel):
    """Computed metric values for a transfer."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    tcs: float | None = None
    rhf: float | None = None
    probe_task_count: int = 0
    probe_question_count: int = 0


class EvaluationReport(BaseModel):
    """A standardized PAM evaluation report (spec §10.3).

    Serializes to the JSON shape documented in the specification.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    evaluation_id: str = ""
    source_agent: AgentDescriptor = Field(default_factory=AgentDescriptor)
    target_agent: AgentDescriptor = Field(default_factory=AgentDescriptor)
    artifact_id: str = ""
    rehydration_config: RehydrationConfigSummary = Field(
        default_factory=RehydrationConfigSummary
    )
    metrics: Metrics = Field(default_factory=Metrics)
    timestamp: str = ""

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON (pretty by default)."""
        data = self.model_dump(mode="json")
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str | bytes) -> "EvaluationReport":
        """Deserialize from JSON."""
        return cls.model_validate_json(data)

    def summary(self) -> str:
        """Human-readable interpretation of the metrics (spec §10.1/§10.2 bands)."""
        lines: list[str] = []
        if self.metrics.tcs is not None:
            lines.append(
                f"TCS {self.metrics.tcs:.2f} — {interpret_tcs(self.metrics.tcs)}"
            )
        if self.metrics.rhf is not None:
            lines.append(
                f"RHF {self.metrics.rhf:.2f} — {interpret_rhf(self.metrics.rhf)}"
            )
        return "\n".join(lines)


def evaluate_transfer(
    *,
    source_agent_fn: AgentFn,
    target_agent_fn: AgentFn,
    tasks: Sequence[ProbeTask] = (),
    questions: Sequence[str] = (),
    grader: Grader = default_grader,
    embed_fn: Embedder | None = None,
    artifact: MemoryArtifact | None = None,
    source_descriptor: AgentDescriptor | None = None,
    target_descriptor: AgentDescriptor | None = None,
    rehydration_config: RehydrationConfigSummary | None = None,
    evaluation_id: str = "",
    timestamp: str | None = None,
) -> EvaluationReport:
    """Run the full §10 evaluation protocol and assemble a report.

    Executes the probe ``tasks`` against both agents to compute TCS, and collects
    aligned responses to ``questions`` to compute RHF. Either probe set may be
    empty, in which case the corresponding metric is left ``None``.

    Args:
        source_agent_fn: Callable producing source-agent responses (full memory).
        target_agent_fn: Callable producing target-agent responses (re-hydrated).
        tasks: Probe tasks for TCS (success/failure graded).
        questions: Aligned prompts for RHF (semantic-similarity scored).
        grader: How to grade probe-task success (default: substring match).
        embed_fn: Optional embedder for RHF similarity.
        artifact: Optional source artifact; its ``root_hash`` populates
            ``artifact_id`` and its agent metadata fills missing descriptors.
        source_descriptor / target_descriptor: Optional explicit agent info.
        rehydration_config: Optional config summary recorded in the report.
        evaluation_id: Optional identifier for the report.
        timestamp: ISO-8601 timestamp; defaults to ``now`` (UTC).

    Returns:
        A populated :class:`EvaluationReport`.
    """
    metrics = Metrics()

    if tasks:
        source_results = run_probe_tasks(source_agent_fn, tasks, grader)
        target_results = run_probe_tasks(target_agent_fn, tasks, grader)
        metrics.tcs = transfer_continuity_score(source_results, target_results)
        metrics.probe_task_count = len(tasks)

    if questions:
        source_responses = collect_responses(source_agent_fn, questions)
        target_responses = collect_responses(target_agent_fn, questions)
        metrics.rhf = rehydration_fidelity(source_responses, target_responses, embed_fn)
        metrics.probe_question_count = len(questions)

    src = source_descriptor or AgentDescriptor()
    tgt = target_descriptor or AgentDescriptor()
    artifact_id = ""
    if artifact is not None:
        artifact_id = artifact.root_hash or artifact.compute_root_hash()
        if not src.name:
            src = AgentDescriptor(
                name=artifact.source_agent.name,
                model_family=artifact.source_agent.model_family,
            )

    return EvaluationReport(
        evaluation_id=evaluation_id,
        source_agent=src,
        target_agent=tgt,
        artifact_id=artifact_id,
        rehydration_config=rehydration_config or RehydrationConfigSummary(),
        metrics=metrics,
        timestamp=(
            timestamp
            if timestamp is not None
            else datetime.now(timezone.utc).isoformat()
        ),
    )
