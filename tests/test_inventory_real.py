"""Real-inventory tests for audit/inventory.py using checked-in sample-claude-harness fixture."""

from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.audit.inventory import scan, scan_claude_code
from opencode_harness_bridge.models import SafetyTier


def test_scan_finds_project_claude_md(sample_claude_harness: Path) -> None:
    """CLAUDE.md is discovered as kind='instruction' with tier=AUTO_APPLY."""
    assets = scan_claude_code(sample_claude_harness)
    instructions = [a for a in assets if a.kind == "instruction"]
    assert len(instructions) >= 1
    proj = next((a for a in instructions if a.path.name == "CLAUDE.md"), None)
    assert proj is not None
    assert proj.source == "claude-code"
    assert proj.tier == SafetyTier.AUTO_APPLY
    assert "pytest" in proj.content_preview


def test_scan_finds_local_claude_md(sample_claude_harness: Path) -> None:
    """CLAUDE.local.md is also discovered as kind='instruction'."""
    assets = scan_claude_code(sample_claude_harness)
    locals_ = [a for a in assets if a.kind == "instruction" and a.path.name == "CLAUDE.local.md"]
    assert len(locals_) == 1
    assert locals_[0].tier == SafetyTier.AUTO_APPLY


def test_scan_finds_agent_files(sample_claude_harness: Path) -> None:
    """All files under .claude/agents/*.md are kind='agent', tier=AUTO_APPLY."""
    assets = scan_claude_code(sample_claude_harness)
    agents = [a for a in assets if a.kind == "agent"]
    names = {a.path.name for a in agents}
    assert "qa-reviewer.md" in names
    assert "refactor-planner.md" in names
    assert all(a.tier == SafetyTier.AUTO_APPLY for a in agents)


def test_scan_finds_skill_files(sample_claude_harness: Path) -> None:
    """SKILL.md under .claude/skills/*/ are kind='skill'."""
    assets = scan_claude_code(sample_claude_harness)
    skills = [a for a in assets if a.kind == "skill"]
    names = {a.path.parent.name for a in skills}
    assert "commit-helper" in names
    assert "test-runner" in names
    assert all(a.tier == SafetyTier.AUTO_APPLY for a in skills)


def test_scan_finds_rule_files(sample_claude_harness: Path) -> None:
    """Files under .claude/rules/*.md are kind='rule', tier=MODEL_ASSISTED."""
    assets = scan_claude_code(sample_claude_harness)
    rules = [a for a in assets if a.kind == "rule"]
    names = {a.path.name for a in rules}
    assert "no-print.md" in names
    assert "use-type-hints.md" in names
    assert all(a.tier == SafetyTier.MODEL_ASSISTED for a in rules)


def test_scan_finds_mcp_servers_and_hooks_from_settings(sample_claude_harness: Path) -> None:
    """settings.json produces 1 mcp_server per server and 1 hook per event in hooks block.

    The fixture has 2 mcpServers (github, filesystem) and 2 hooks (PreToolUse, PostToolUse).
    """
    assets = scan_claude_code(sample_claude_harness)
    mcp = [a for a in assets if a.kind == "mcp_server"]
    hooks = [a for a in assets if a.kind == "hook"]
    assert len(mcp) == 2
    assert len(hooks) == 2
    assert all(a.tier == SafetyTier.MODEL_ASSISTED for a in mcp)
    assert all(a.tier == SafetyTier.MODEL_ASSISTED for a in hooks)


def test_scan_skips_heavy_directories(tmp_path: Path) -> None:
    """CLAUDE.md inside .git/, node_modules/, __pycache__/ etc must NOT be discovered."""
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "CLAUDE.md").write_text("# Real one")
    heavy_dirs = [
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "venv",
        ".venv",
        "vendor",
    ]
    for heavy in heavy_dirs:
        d = ws / heavy
        d.mkdir()
        (d / "CLAUDE.md").write_text(f"# Should be skipped: {heavy}")
    assets = scan_claude_code(ws)
    paths = [a.path for a in assets]
    assert any(p.name == "CLAUDE.md" and p.parent == ws for p in paths)
    for heavy in heavy_dirs:
        assert not any(heavy in p.parts for p in paths), (
            f"{heavy}/CLAUDE.md was incorrectly discovered"
        )


def test_scan_handles_malformed_settings_gracefully(
    sample_claude_harness_malformed_settings: Path,
) -> None:
    """Invalid JSON in settings.json must NOT crash; other files still discovered."""
    assets = scan_claude_code(sample_claude_harness_malformed_settings)
    assert any(a.kind == "instruction" for a in assets)
    assert any(a.kind == "agent" for a in assets)
    mcp = [a for a in assets if a.kind == "mcp_server"]
    hooks = [a for a in assets if a.kind == "hook"]
    assert mcp == []
    assert hooks == []


def test_scan_dispatch_returns_claude_results(sample_claude_harness: Path) -> None:
    """The public scan() function still dispatches to scan_claude_code for source='claude-code'."""
    assets = scan("claude-code", sample_claude_harness)
    assert len(assets) >= 5
