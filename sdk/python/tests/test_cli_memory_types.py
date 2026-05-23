"""CLI tests covering all Portable Agent Memory entry types."""

import json
import sys

import pytest

from pam import cli


EXPECTED_STATUS = {
    "total": 5,
    "episodic": 1,
    "semantic": 1,
    "procedural": 1,
    "working": 1,
    "identity": 1,
}


@pytest.fixture
def isolated_cli_storage(monkeypatch, tmp_path):
    pam_dir = tmp_path / ".pam"
    monkeypatch.setattr(cli, "PAM_DIR", pam_dir)
    monkeypatch.setattr(cli, "KEYS_DIR", pam_dir / "keys")
    monkeypatch.setattr(cli, "MEMORIES_DIR", pam_dir / "memories")
    monkeypatch.setattr(cli, "CURRENT_ARTIFACT", pam_dir / "memories" / "current.pam")
    return pam_dir


def _run_cli(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["pam", *[str(arg) for arg in args]])
    capsys.readouterr()
    try:
        cli.main()
    except SystemExit as exc:  # pragma: no cover - successful commands should not exit
        if exc.code not in (0, None):
            raise
    return capsys.readouterr()


def _remember_all_memory_types(monkeypatch, capsys):
    _run_cli(monkeypatch, capsys, "remember", "Retrospective captured the API latency spike")
    _run_cli(monkeypatch, capsys, "remember", "--fact", "project", "uses", "TypeScript")
    _run_cli(
        monkeypatch,
        capsys,
        "remember",
        "--skill",
        "deploy",
        "Deploy production rollout",
        "kubectl apply -f deploy.yaml",
    )
    _run_cli(monkeypatch, capsys, "remember", "--preference", "editor=vim")
    _run_cli(
        monkeypatch,
        capsys,
        "remember",
        "--working",
        "Ship migration",
        "Validate telemetry",
        "--scratch",
        "Prepare rollback checklist",
    )


class TestCLIMemoryTypes:
    def test_remember_recall_status_and_search_all_memory_types(self, isolated_cli_storage, monkeypatch, capsys):
        _remember_all_memory_types(monkeypatch, capsys)

        recall = json.loads(_run_cli(monkeypatch, capsys, "recall", "--json").out)
        assert len(recall) == 5

        by_type = {item["type"]: item for item in recall}
        assert set(by_type) == {"episodic", "semantic", "procedural", "identity", "working"}
        assert by_type["episodic"]["content"] == "Retrospective captured the API latency spike"
        assert by_type["semantic"]["subject"] == "project"
        assert by_type["semantic"]["object"] == "TypeScript"
        assert by_type["procedural"]["name"] == "deploy"
        assert by_type["procedural"]["body"] == "kubectl apply -f deploy.yaml"
        assert by_type["identity"]["preferences"] == {"editor": "vim"}
        assert by_type["working"]["goals"] == ["Ship migration", "Validate telemetry"]
        assert by_type["working"]["scratch"] == "Prepare rollback checklist"

        status = json.loads(_run_cli(monkeypatch, capsys, "status", "--json").out)
        assert status == EXPECTED_STATUS

        search_cases = [
            ("retrospective", "episodic"),
            ("typescript", "semantic"),
            ("kubectl", "procedural"),
            ("vim", "identity"),
            ("rollback", "working"),
        ]
        for query, expected_type in search_cases:
            matches = json.loads(_run_cli(monkeypatch, capsys, "recall", "--json", "--search", query).out)
            assert len(matches) == 1
            assert matches[0]["type"] == expected_type

    def test_verify_and_clear_current_artifact(self, isolated_cli_storage, monkeypatch, capsys):
        _remember_all_memory_types(monkeypatch, capsys)

        verify_output = _run_cli(monkeypatch, capsys, "verify").out
        assert str(cli.CURRENT_ARTIFACT) in verify_output
        assert "Integrity: PASS" in verify_output

        _run_cli(monkeypatch, capsys, "clear", "--force")
        assert not cli.CURRENT_ARTIFACT.exists()
        assert json.loads(_run_cli(monkeypatch, capsys, "status", "--json").out) == {
            "total": 0,
            "episodic": 0,
            "semantic": 0,
            "procedural": 0,
            "working": 0,
            "identity": 0,
        }
        assert json.loads(_run_cli(monkeypatch, capsys, "recall", "--json").out) == []

    def test_export_and_import_preserve_all_memory_types(self, isolated_cli_storage, monkeypatch, capsys, tmp_path):
        _remember_all_memory_types(monkeypatch, capsys)

        export_path = tmp_path / "memory-types-export.pam"
        export_output = _run_cli(monkeypatch, capsys, "export", export_path).out
        assert export_path.exists()
        assert "Exported 5 entries" in export_output

        _run_cli(monkeypatch, capsys, "clear", "--force")
        import_output = _run_cli(monkeypatch, capsys, "import", export_path).out
        assert "Imported 5 new entries" in import_output

        status = json.loads(_run_cli(monkeypatch, capsys, "status", "--json").out)
        assert status == EXPECTED_STATUS

        recall = json.loads(_run_cli(monkeypatch, capsys, "recall", "--json").out)
        assert {item["type"] for item in recall} == {"episodic", "semantic", "procedural", "identity", "working"}
