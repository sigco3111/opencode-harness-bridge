"""Real-converter tests for the public dispatchers in converters/__init__.py (v0.2.0)."""

from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.converters import (
    convert_claude_code_to_opencode,
    convert_codex_to_opencode,
)


def test_claude_code_converter_returns_full_schema(sample_claude_harness: Path) -> None:
    """v0.2.0: real converter returns the 5-key schema, not an empty dict."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    result = convert_claude_code_to_opencode(plan)
    assert isinstance(result, dict)
    for key in ("opencode_json_blocks", "agents_md_blocks", "skills", "commands", "manual_steps"):
        assert key in result, f"missing key: {key}"
    assert result != {}, "Real converter returned an empty dict (looks like a stub)"


def test_codex_converter_returns_full_schema(tmp_codex_workspace: Path) -> None:
    """v0.3.0: real codex converter returns the 5-key schema, not an empty dict."""
    plan = migrate(source="codex", target="opencode", workspace=tmp_codex_workspace)
    result = convert_codex_to_opencode(plan)
    assert isinstance(result, dict)
    for key in ("opencode_json_blocks", "agents_md_blocks", "skills", "commands", "manual_steps"):
        assert key in result, f"missing key: {key}"
    assert result != {}, "Real converter returned an empty dict (looks like a stub)"
