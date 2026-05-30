"""Tests for the Portable Agent Memory evaluation metrics (spec §10)."""

import json
import sys

import pytest

from pam import cli

from pam.metrics import (
    AgentDescriptor,
    EvaluationReport,
    ProbeTask,
    RehydrationConfigSummary,
    cosine_similarity,
    evaluate_transfer,
    interpret_rhf,
    interpret_tcs,
    rehydration_fidelity,
    run_probe_tasks,
    semantic_similarity,
    task_success_rate,
    transfer_continuity_score,
)
from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import SemanticEntry

# ----------------------------------------------------------------------
# Similarity primitives
# ----------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            cosine_similarity([1.0], [1.0, 2.0])


class TestSemanticSimilarity:
    def test_identical_text_is_one(self):
        assert semantic_similarity("the cat sat", "the cat sat") == pytest.approx(1.0)

    def test_result_never_exceeds_one(self):
        # Float rounding must not push the documented [0.0, 1.0] range above 1.0.
        assert semantic_similarity("the cat sat", "the cat sat") <= 1.0

    def test_disjoint_text_is_zero(self):
        assert semantic_similarity("alpha beta", "gamma delta") == pytest.approx(0.0)

    def test_partial_overlap_between_zero_and_one(self):
        sim = semantic_similarity("deploy the canary release", "deploy the release now")
        assert 0.0 < sim < 1.0

    def test_empty_text_is_zero(self):
        assert semantic_similarity("", "anything") == 0.0

    def test_clamps_negative_to_zero(self):
        # An embedder that produces opposed vectors -> negative cosine -> clamped.
        def embed(t):
            return [1.0, 0.0] if t == "a" else [-1.0, 0.0]

        assert semantic_similarity("a", "b", embed_fn=embed) == 0.0

    def test_custom_embedder_used(self):
        def embed(t):  # everything identical
            return [1.0, 1.0]

        assert semantic_similarity("x", "y", embed_fn=embed) == pytest.approx(1.0)

    def test_tokenization_is_case_insensitive(self):
        assert semantic_similarity("Hello World", "hello world") == pytest.approx(1.0)


# ----------------------------------------------------------------------
# Transfer Continuity Score
# ----------------------------------------------------------------------


class TestTaskSuccessRate:
    def test_all_success(self):
        assert task_success_rate([True, True, True]) == 1.0

    def test_half_success(self):
        assert task_success_rate([True, False]) == 0.5

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            task_success_rate([])


class TestTransferContinuityScore:
    def test_perfect_continuity(self):
        src = [True, True, False, True]
        tgt = [True, True, False, True]
        assert transfer_continuity_score(src, tgt) == pytest.approx(1.0)

    def test_degraded_continuity(self):
        src = [True, True, True, True]
        tgt = [True, True, False, False]
        assert transfer_continuity_score(src, tgt) == pytest.approx(0.5)

    def test_target_exceeds_source(self):
        src = [True, False]
        tgt = [True, True]
        assert transfer_continuity_score(src, tgt) == pytest.approx(2.0)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            transfer_continuity_score([True], [True, False])

    def test_zero_source_baseline_raises(self):
        with pytest.raises(ValueError):
            transfer_continuity_score([False, False], [True, False])


class TestInterpretTcs:
    @pytest.mark.parametrize(
        "score,fragment",
        [
            (1.2, "exceeds"),
            (1.0, "exceeds"),
            (0.85, "Minor"),
            (0.6, "Significant"),
            (0.3, "Severe"),
        ],
    )
    def test_bands(self, score, fragment):
        assert fragment.lower() in interpret_tcs(score).lower()


# ----------------------------------------------------------------------
# Re-Hydration Fidelity
# ----------------------------------------------------------------------


class TestRehydrationFidelity:
    def test_identical_responses(self):
        src = ["the answer is 42", "deploy to prod"]
        tgt = ["the answer is 42", "deploy to prod"]
        assert rehydration_fidelity(src, tgt) == pytest.approx(1.0)

    def test_disjoint_responses(self):
        assert rehydration_fidelity(["alpha"], ["omega"]) == pytest.approx(0.0)

    def test_mean_of_pairs(self):
        # pair 1: identical (1.0); pair 2: disjoint (0.0) -> mean 0.5
        src = ["same words here", "alpha beta"]
        tgt = ["same words here", "gamma delta"]
        assert rehydration_fidelity(src, tgt) == pytest.approx(0.5)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            rehydration_fidelity(["a"], ["a", "b"])

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            rehydration_fidelity([], [])

    def test_custom_embedder(self):
        def embed(t):
            return [1.0, 0.0]

        assert rehydration_fidelity(["a"], ["b"], embed_fn=embed) == pytest.approx(1.0)


class TestInterpretRhf:
    @pytest.mark.parametrize(
        "score,fragment",
        [
            (0.95, "High"),
            (0.8, "Good"),
            (0.6, "Moderate"),
            (0.3, "Low"),
        ],
    )
    def test_bands(self, score, fragment):
        assert fragment.lower() in interpret_rhf(score).lower()


# ----------------------------------------------------------------------
# Probe harness
# ----------------------------------------------------------------------


class TestProbeHarness:
    def test_run_probe_tasks_substring_grading(self):
        tasks = [
            ProbeTask(id="t1", prompt="What port?", expect_substring="5433"),
            ProbeTask(id="t2", prompt="What region?", expect_substring="us-central1"),
        ]

        # Agent that only knows the port.
        def agent(prompt):
            return "It runs on port 5433." if "port" in prompt else "Not sure."

        results = run_probe_tasks(agent, tasks)
        assert results == [True, False]

    def test_task_without_expectation_fails(self):
        tasks = [ProbeTask(id="t1", prompt="anything")]
        assert run_probe_tasks(lambda p: "whatever", tasks) == [False]

    def test_custom_grader(self):
        tasks = [ProbeTask(id="t1", prompt="echo")]

        def grader(task, response):
            return len(response) > 3

        assert run_probe_tasks(lambda p: "long answer", tasks, grader) == [True]


# ----------------------------------------------------------------------
# End-to-end report assembly
# ----------------------------------------------------------------------


def _artifact() -> MemoryArtifact:
    return MemoryArtifact(
        source_agent=SourceAgent(
            name="research-bot-alpha", model_family="gpt-4", runtime="python"
        ),
        semantic=[
            SemanticEntry(subject="db", predicate="port", object="5433", confidence=1.0)
        ],
    )


class TestEvaluateTransfer:
    def test_full_report(self):
        tasks = [ProbeTask(id="t1", prompt="db port?", expect_substring="5433")]
        questions = ["What database port do we use?"]

        # Source remembers the fact; target re-hydrated also remembers it.
        def source(p):
            return "The database port is 5433."

        def target(p):
            return "The database port is 5433."

        report = evaluate_transfer(
            source_agent_fn=source,
            target_agent_fn=target,
            tasks=tasks,
            questions=questions,
            artifact=_artifact(),
            target_descriptor=AgentDescriptor(name="beta", model_family="claude-3"),
            rehydration_config=RehydrationConfigSummary(
                token_budget=4096, relevance_threshold=0.3, format_style="xml"
            ),
            evaluation_id="eval:test-001",
            timestamp="2026-01-15T12:00:00Z",
        )

        assert report.metrics.tcs == pytest.approx(1.0)
        assert report.metrics.rhf == pytest.approx(1.0)
        assert report.metrics.probe_task_count == 1
        assert report.metrics.probe_question_count == 1
        # artifact metadata populates the source descriptor + artifact id
        assert report.source_agent.name == "research-bot-alpha"
        assert report.target_agent.name == "beta"
        assert report.artifact_id.startswith("blake3:")
        assert report.timestamp == "2026-01-15T12:00:00Z"

    def test_degraded_target_lowers_metrics(self):
        tasks = [
            ProbeTask(id="t1", prompt="port?", expect_substring="5433"),
            ProbeTask(id="t2", prompt="region?", expect_substring="us-central1"),
        ]

        def source(p):
            return "port 5433 region us-central1"

        # Target forgot everything after a lossy transfer.
        def target(p):
            return "I don't have that information."

        report = evaluate_transfer(
            source_agent_fn=source, target_agent_fn=target, tasks=tasks
        )
        assert report.metrics.tcs == pytest.approx(0.0)
        assert "Severe" in report.summary()

    def test_metrics_optional_when_no_probes(self):
        report = evaluate_transfer(
            source_agent_fn=lambda p: "", target_agent_fn=lambda p: ""
        )
        assert report.metrics.tcs is None
        assert report.metrics.rhf is None


class TestEvaluationReportSerialization:
    def test_round_trip_json(self):
        report = evaluate_transfer(
            source_agent_fn=lambda p: "5433",
            target_agent_fn=lambda p: "5433",
            tasks=[ProbeTask(id="t1", prompt="port?", expect_substring="5433")],
            evaluation_id="eval:rt",
            timestamp="2026-01-15T12:00:00Z",
        )
        restored = EvaluationReport.from_json(report.to_json())
        assert restored.evaluation_id == "eval:rt"
        assert restored.metrics.tcs == pytest.approx(1.0)

    def test_matches_spec_shape(self):
        report = evaluate_transfer(
            source_agent_fn=lambda p: "x",
            target_agent_fn=lambda p: "x",
            questions=["q"],
            timestamp="2026-01-15T12:00:00Z",
        )
        data = report.model_dump(mode="json")
        # Keys documented in spec §10.3
        for key in (
            "evaluation_id",
            "source_agent",
            "target_agent",
            "artifact_id",
            "rehydration_config",
            "metrics",
            "timestamp",
        ):
            assert key in data
        for key in ("tcs", "rhf", "probe_task_count", "probe_question_count"):
            assert key in data["metrics"]


# ----------------------------------------------------------------------
# CLI `evaluate` command
# ----------------------------------------------------------------------


def _run_cli(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["pam", *[str(a) for a in args]])
    capsys.readouterr()
    try:
        cli.main()
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    return capsys.readouterr()


_RESULTS = {
    "evaluation_id": "eval:cli-test",
    "source_agent": {"name": "alpha", "model_family": "gpt-4"},
    "target_agent": {"name": "beta", "model_family": "claude-3"},
    "rehydration_config": {
        "token_budget": 4096,
        "relevance_threshold": 0.3,
        "format_style": "xml",
    },
    "probe_tasks": [
        {"id": "t1", "source_success": True, "target_success": True},
        {"id": "t2", "source_success": True, "target_success": False},
    ],
    "probe_questions": [
        {"id": "q1", "source_response": "port 5433", "target_response": "port 5433"},
    ],
}


class TestEvaluateCli:
    def test_text_output(self, monkeypatch, capsys, tmp_path):
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(_RESULTS), encoding="utf-8")
        out = _run_cli(monkeypatch, capsys, "evaluate", results_file).out
        assert "TCS: 0.50" in out
        assert "RHF: 1.00" in out
        assert "eval:cli-test" in out

    def test_json_output_matches_spec(self, monkeypatch, capsys, tmp_path):
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(_RESULTS), encoding="utf-8")
        out = _run_cli(monkeypatch, capsys, "evaluate", results_file, "--json").out
        report = json.loads(out)
        assert report["metrics"]["tcs"] == pytest.approx(0.5)
        assert report["metrics"]["rhf"] == pytest.approx(1.0)
        assert report["metrics"]["probe_task_count"] == 2
        assert report["source_agent"]["name"] == "alpha"

    def test_writes_output_file(self, monkeypatch, capsys, tmp_path):
        results_file = tmp_path / "results.json"
        results_file.write_text(json.dumps(_RESULTS), encoding="utf-8")
        out_file = tmp_path / "report.json"
        _run_cli(monkeypatch, capsys, "evaluate", results_file, "--output", out_file)
        assert out_file.exists()
        report = json.loads(out_file.read_text(encoding="utf-8"))
        assert report["evaluation_id"] == "eval:cli-test"

    def test_missing_file_exits(self, monkeypatch, capsys, tmp_path):
        with pytest.raises(SystemExit):
            _run_cli(monkeypatch, capsys, "evaluate", tmp_path / "nope.json")
