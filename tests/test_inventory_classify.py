"""Smoke tests for the inventory scanner (v0.2.0 real scanner)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.audit.inventory import scan
from opencode_harness_bridge.exceptions import InvalidSourceError, InvalidTargetError


def test_scan_claude_code_discovers_assets(tmp_claude_workspace: Path) -> None:
    """v0.2.0 real scanner: discovers at least the CLAUDE.md in tmp workspace."""
    assets = scan("claude-code", tmp_claude_workspace)
    assert len(assets) >= 1
    assert any(a.kind == "instruction" and a.path.name == "CLAUDE.md" for a in assets)


def test_scan_codex_stub_returns_empty(tmp_codex_workspace: Path) -> None:
    """v0.3.0+ stub: codex scanner still returns empty tuple."""
    assets = scan("codex", tmp_codex_workspace)
    assert assets == ()


def test_scan_rejects_unknown_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported source"):
        scan("made-up-source", tmp_path)


def test_migrate_builds_plan_for_claude(tmp_claude_workspace: Path) -> None:
    plan = migrate(source="claude-code", target="opencode", workspace=tmp_claude_workspace)
    assert plan.source == "claude-code"
    assert plan.target == "opencode"
    assert len(plan.assets) >= 1


def test_migrate_rejects_invalid_source(tmp_path: Path) -> None:
    with pytest.raises(InvalidSourceError, match="unsupported source"):
        migrate(source="vscode", target="opencode", workspace=tmp_path)


def test_migrate_rejects_invalid_target(tmp_path: Path) -> None:
    with pytest.raises(InvalidTargetError, match="unsupported target"):
        migrate(source="claude-code", target="vscode", workspace=tmp_path)


def test_migrate_accepts_string_workspace(tmp_claude_workspace: Path) -> None:
    plan = migrate(source="claude-code", target="opencode", workspace=str(tmp_claude_workspace))
    assert plan.workspace == tmp_claude_workspace.resolve()
