"""Inventory: scan a source harness directory and list discovered assets.

Implementation note (for other-PC worker)
----------------------------------------
v0.1.0 stub: returns an empty tuple. v0.2.0 implements real scanning:

1. Walk ``workspace`` for known Claude Code paths:
   - ``CLAUDE.md``, ``CLAUDE.local.md`` → kind="instruction"
   - ``.claude/agents/*.md`` → kind="agent"
   - ``.claude/skills/*/SKILL.md`` → kind="skill"
   - ``.claude/settings*.json`` → kind="hook" + "mcp_server"
   - ``.claude/rules/*.md`` → kind="rule"
   - ``~/.claude/`` mirrors for global variants

2. Walk for known Codex paths (v0.3.0+):
   - ``AGENTS.md`` → kind="instruction"
   - ``.codex/agents/*.toml`` → kind="agent"
   - ``.codex/hooks/*.py`` → kind="hook"
   - ``.codex/config.toml`` → kind="mcp_server"

3. Skip heavy directories: ``.git``, ``node_modules``, ``Library``,
   ``.Trash``, ``dist``, ``build``, ``vendor`` (per
   claude-codex-harness-sync layer-map.md).

4. Read first 200 chars of each asset for ``content_preview`` (helps
   humans review the report).

Performance note
----------------
For v0.2.0+, walking the whole filesystem can be slow. Use
``os.scandir()`` + early-exit when the target signature is found.
For 1k+ project workspaces, consider caching results in a
``.migration-cache/`` directory (already in .gitignore).
"""
from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.models import HarnessAsset, SafetyTier
from opencode_harness_bridge.safety.tiers import classify_asset

# v0.1.0 only: Claude Code signature files (recognized by name only)
_CLAUDE_CODE_SIGNATURES: tuple[str, ...] = (
    "CLAUDE.md",
    "CLAUDE.local.md",
    ".claude/CLAUDE.md",
)


def scan_claude_code(workspace: Path) -> tuple[HarnessAsset, ...]:
    """Discover Claude Code harness assets in ``workspace``.

    v0.1.0 stub: returns an empty tuple (full implementation in v0.2.0).

    Returns
    -------
    tuple[HarnessAsset, ...]
        Discovered assets. Each carries its kind, source, and tier
        (assigned via :func:`safety.tiers.classify_asset`).
    """
    _ = (workspace, _CLAUDE_CODE_SIGNATURES, classify_asset, HarnessAsset, SafetyTier)
    return ()


def scan_codex(workspace: Path) -> tuple[HarnessAsset, ...]:
    """Discover Codex harness assets in ``workspace``.

    v0.1.0 stub: returns an empty tuple (full implementation in v0.3.0).
    """
    return ()


# Public dispatcher
SCANNERS = {
    "claude-code": scan_claude_code,
    "codex": scan_codex,
}


def scan(source: str, workspace: Path) -> tuple[HarnessAsset, ...]:
    """Dispatch to the right scanner based on ``source``."""
    scanner = SCANNERS.get(source)
    if scanner is None:
        raise ValueError(f"unsupported source format: {source!r}")
    return scanner(workspace)
