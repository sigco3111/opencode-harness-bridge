"""Smoke tests for the converters (v0.1.0 stub)."""
from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.converters import (
    convert_claude_code_to_opencode,
    convert_codex_to_opencode,
)


def test_claude_code_converter_stub_returns_empty_dict(tmp_claude_workspace: Path) -> None:
    plan = migrate(source="claude-code", target="opencode", workspace=tmp_claude_workspace)
    result = convert_claude_code_to_opencode(plan)
    assert result == {}


def test_codex_converter_stub_returns_empty_dict(tmp_codex_workspace: Path) -> None:
    plan = migrate(source="codex", target="opencode", workspace=tmp_codex_workspace)
    result = convert_codex_to_opencode(plan)
    assert result == {}
