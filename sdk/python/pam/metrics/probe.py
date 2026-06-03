"""Probe-task harness for the PAM evaluation protocol (spec §10).

A :class:`ProbeTask` is a single unit of the evaluation suite. The spec
recommends at least 30 tasks spanning three categories — ``recall`` (fact
retrieval), ``reasoning`` (multi-step inference), and ``procedural`` (workflow
execution).

The harness is agnostic to how an agent is invoked: an *agent function* is any
callable that takes a prompt string and returns a response string. That lets the
same code drive a live LLM, a local model, or a deterministic mock in tests.
"""

from __future__ import annotations

from typing import Callable, Literal, Sequence

from pydantic import BaseModel, ConfigDict

# An agent function maps a prompt to a response string.
AgentFn = Callable[[str], str]

ProbeCategory = Literal["recall", "reasoning", "procedural"]


class ProbeTask(BaseModel):
    """A single probe task in an evaluation suite.

    Success is graded either by ``expect_substring`` (case-insensitive substring
    match against the agent's response) or, for richer checks, by passing a
    ``grader`` callable to the run functions.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str
    prompt: str
    category: ProbeCategory = "recall"
    expect_substring: str | None = None


# A grader decides whether a response satisfies a task.
Grader = Callable[[ProbeTask, str], bool]


def default_grader(task: ProbeTask, response: str) -> bool:
    """Grade a response by case-insensitive substring containment.

    A task with no ``expect_substring`` is treated as ungradable and counted as a
    failure (a probe you cannot score did not pass).
    """
    if not task.expect_substring:
        return False
    return task.expect_substring.lower() in response.lower()


def run_probe_tasks(
    agent_fn: AgentFn,
    tasks: Sequence[ProbeTask],
    grader: Grader = default_grader,
) -> list[bool]:
    """Run each task against ``agent_fn`` and return per-task success flags.

    The returned list aligns 1:1 with ``tasks`` and is suitable as input to
    :func:`pam.metrics.evaluation.transfer_continuity_score`.
    """
    return [grader(task, agent_fn(task.prompt)) for task in tasks]


def collect_responses(
    agent_fn: AgentFn,
    prompts: Sequence[str],
) -> list[str]:
    """Collect an agent's responses to an aligned probe set (for RHF)."""
    return [agent_fn(prompt) for prompt in prompts]
