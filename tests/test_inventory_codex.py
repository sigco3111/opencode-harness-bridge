"""Real-inventory tests for audit/inventory.py scan_codex (v0.3.0 RED).

These tests are the RED phase of TDD — they MUST fail against the current
scan_codex() stub (which returns ()). The GREEN implementation in T3.1
will make them pass.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opencode_harness_bridge.audit.inventory import scan
from opencode_harness_bridge.audit.inventory import scan_codex
from opencode_harness_bridge.models import SafetyTier


@pytest.fixture
def sample_codex_harness() -> Path:
    """Provide the checked-in sample-codex-harness fixture when conftest
    doesn't expose it directly in some environments.
    """
    return Path(__file__).parent / "fixtures" / "sample-codex-harness"


def test_scan_finds_agents_md(sample_codex_harness: Path) -> None:
    """Top-level AGENTS.md is discovered as kind='instruction', tier=AUTO_APPLY."""
    assets = scan_codex(sample_codex_harness)
    instructions = [a for a in assets if a.kind == "instruction"]
    assert len(instructions) >= 1
    proj = next((a for a in instructions if a.path.name == "AGENTS.md"), None)
    assert proj is not None
    assert proj.source == "codex"
    assert proj.tier == SafetyTier.AUTO_APPLY
    assert "pytest" in proj.content_preview  # fixture AGENTS.md mentions "pytest"


def test_scan_finds_toml_agents(sample_codex_harness: Path) -> None:
    """.codex/agents/*.toml are discovered as kind='agent', tier=AUTO_APPLY."""
    assets = scan_codex(sample_codex_harness)
    agents = [a for a in assets if a.kind == "agent"]
    names = {a.path.stem for a in agents}
    assert "example" in names
    assert all(a.tier == SafetyTier.AUTO_APPLY for a in agents)


def test_scan_finds_mcp_servers_from_config_toml(sample_codex_harness: Path) -> None:
    """[mcp_servers.<name>] entries in config.toml are kind='mcp_server', MODEL_ASSISTED.

    The fixture config.toml has 1 mcp_server named "filesystem".
    """
    assets = scan_codex(sample_codex_harness)
    mcp = [a for a in assets if a.kind == "mcp_server"]
    assert len(mcp) == 1
    assert "filesystem" in mcp[0].description
    assert mcp[0].tier == SafetyTier.MODEL_ASSISTED


def test_scan_finds_hook_python_files(sample_codex_harness: Path) -> None:
    """.codex/hooks/*.py files are kind='hook', MODEL_ASSISTED.

    The fixture has 1 Python hook (pre-tool-use.py).
    """
    assets = scan_codex(sample_codex_harness)
    hooks = [a for a in assets if a.kind == "hook"]
    assert len(hooks) == 1
    assert "pre-tool-use.py" in hooks[0].path.name
    assert hooks[0].tier == SafetyTier.MODEL_ASSISTED


def test_scan_finds_memory_files(sample_codex_harness: Path) -> None:
    """.codex/memories/* are kind='memory', MODEL_ASSISTED.

    The fixture has 1 memory file (notes.md).
    """
    assets = scan_codex(sample_codex_harness)
    memories = [a for a in assets if a.kind == "memory"]
    assert len(memories) == 1
    assert memories[0].tier == SafetyTier.MODEL_ASSISTED


def test_scan_handles_malformed_toml_gracefully(
    sample_codex_harness_malformed_toml: Path,
) -> None:
    """Invalid config.toml must NOT crash; the agent TOML is still discovered."""
    assets = scan_codex(sample_codex_harness_malformed_toml)
    # Should still discover the instruction and the healthy agent
    assert any(a.kind == "instruction" for a in assets)
    assert any(a.kind == "agent" and a.path.stem == "healthy-agent" for a in assets)
    # No mcp_server emitted (config.toml was malformed, silently skipped)
    mcp = [a for a in assets if a.kind == "mcp_server"]
    assert mcp == []


def test_scan_dispatch_returns_codex_results(sample_codex_harness: Path) -> None:
    """The public scan() function dispatches to scan_codex for source='codex'."""
    assets = scan("codex", sample_codex_harness)
    # The fixture has 5 assets: 1 instruction + 1 agent + 1 mcp_server + 1 hook + 1 memory
    assert len(assets) >= 4
    kinds = {a.kind for a in assets}
    assert {"instruction", "agent", "mcp_server", "hook"} <= kinds


def test_scan_skips_heavy_directories_in_codex(tmp_path: Path) -> None:
    """Codex AGENTS.md inside .git/, node_modules/ etc must NOT be discovered."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# Real one")
    for heavy in [".git", "node_modules", "__pycache__", "dist", "build", "venv"]:
        d = ws / heavy
        d.mkdir()
        (d / "AGENTS.md").write_text(f"# Should be skipped: {heavy}")
    assets = scan_codex(ws)
    paths = [a.path for a in assets]
    assert any(p.name == "AGENTS.md" and p.parent == ws for p in paths)
    for heavy in [".git", "node_modules", "__pycache__", "dist", "build", "venv"]:
        assert not any(heavy in p.parts for p in paths), f"{heavy}/AGENTS.md was incorrectly discovered"
