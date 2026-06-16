"""pytest fixtures for opencode-harness-bridge.

Implementation note (for other-PC worker)
----------------------------------------
Builds a minimal Claude Code harness skeleton in tmp_path. Tests use
this to exercise the inventory + classify path without touching the
real filesystem.

v0.2.0+: generate a more realistic fixture (with actual CLAUDE.md
content, multiple agent files, MCP server entries, etc.) under
``tests/fixtures/sample-claude-harness/`` and check it in.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_claude_workspace(tmp_path: Path) -> Path:
    """Build a minimal Claude Code harness skeleton in tmp_path."""
    ws = tmp_path / "claude-workspace"
    ws.mkdir()
    (ws / "CLAUDE.md").write_text("# My Project\n\nUse pytest. Always type-hint.\n")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "agents").mkdir()
    (ws / ".claude" / "skills").mkdir()
    (ws / ".claude" / "rules").mkdir()
    return ws


@pytest.fixture
def tmp_codex_workspace(tmp_path: Path) -> Path:
    """Build a minimal Codex harness skeleton in tmp_path."""
    ws = tmp_path / "codex-workspace"
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# My Project\n\nUse pytest. Always type-hint.\n")
    (ws / ".codex").mkdir()
    (ws / ".codex" / "agents").mkdir()
    (ws / ".codex" / "hooks").mkdir()
    return ws
