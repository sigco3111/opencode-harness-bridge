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


@pytest.fixture
def sample_claude_harness() -> Path:
    """Real, checked-in Claude Code harness fixture (10 files, 6 asset kinds).

    Use this in tests that need a stable, version-controlled Claude harness.
    Differs from `tmp_claude_workspace` (which is ephemeral) in that it
    survives the test run and can be inspected manually.
    """
    return Path(__file__).parent / "fixtures" / "sample-claude-harness"


@pytest.fixture
def sample_claude_harness_with_secret() -> Path:
    """Claude Code harness fixture containing a synthetic sk-... secret.

    Used in tests that exercise the SecretLeakError path (scenario S6).
    """
    return Path(__file__).parent / "fixtures" / "sample-claude-harness-with-secret"


@pytest.fixture
def sample_claude_harness_malformed_settings() -> Path:
    """Claude Code harness fixture with intentionally invalid settings.json.

    Used in tests that verify graceful handling of malformed settings files.
    """
    return Path(__file__).parent / "fixtures" / "sample-claude-harness-malformed-settings"


@pytest.fixture
def sample_codex_harness() -> Path:
    """Real, checked-in Codex harness fixture (5 files: instruction, agent, mcp_server, hook, memory).

    Used in tests that exercise the real Codex scanner + converter paths.
    """
    return Path(__file__).parent / "fixtures" / "sample-codex-harness"


@pytest.fixture
def sample_codex_harness_with_secret() -> Path:
    """Real, checked-in Codex harness fixture containing a synthetic sk-... secret.

    Used in tests that exercise the SecretLeakError path for the Codex
    converter (scenario S12).
    """
    return Path(__file__).parent / "fixtures" / "sample-codex-harness-with-secret"


@pytest.fixture
def sample_codex_harness_malformed_toml() -> Path:
    """Real, checked-in Codex harness fixture with intentionally invalid config.toml.

    Used in tests that verify graceful handling of malformed TOML
    in the Codex scanner (scenario S14).
    """
    return Path(__file__).parent / "fixtures" / "sample-codex-harness-malformed-toml"
