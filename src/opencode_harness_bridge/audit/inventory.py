"""Inventory: scan a source harness directory and list discovered assets.

v0.2.0: real Claude Code scanner. Discovers 6 asset kinds:
- ``instruction`` from CLAUDE.md, CLAUDE.local.md
- ``agent`` from .claude/agents/*.md
- ``skill`` from .claude/skills/*/SKILL.md
- ``rule`` from .claude/rules/*.md
- ``mcp_server`` from .claude/settings*.json -> mcpServers
- ``hook`` from .claude/settings*.json -> hooks events

Heavy directories are pruned: .git, node_modules, __pycache__, dist,
build, venv, .venv, vendor, .opencode-migration, .migration-cache.

Malformed settings.json files are skipped silently (no crash).
Codex scanner remains a stub (v0.3.0+).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from opencode_harness_bridge.models import HarnessAsset
from opencode_harness_bridge.safety.tiers import classify_asset

__all__ = ["scan", "scan_claude_code", "scan_codex", "SCANNERS"]


_HEAVY_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "venv",
        ".venv",
        "vendor",
        ".opencode-migration",
        ".migration-cache",
    }
)


def _read_preview(path: Path, limit: int = 200) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _walk(workspace: Path):
    """Yield (path, is_dir) pairs, pruning heavy directories."""
    try:
        entries = list(os.scandir(workspace))
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return
    for entry in entries:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
            continue
        if is_dir and entry.name in _HEAVY_DIRS:
            continue
        yield Path(entry.path), is_dir
        if is_dir:
            yield from _walk(Path(entry.path))


def _emit_instruction(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="instruction",
        source="claude-code",
        tier=classify_asset("claude-code", "instruction"),
        description=f"Project instructions ({path.name})",
        content_preview=_read_preview(path),
    )


def _emit_agent(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="agent",
        source="claude-code",
        tier=classify_asset("claude-code", "agent"),
        description=f"Agent ({path.stem})",
        content_preview=_read_preview(path),
    )


def _emit_skill(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="skill",
        source="claude-code",
        tier=classify_asset("claude-code", "skill"),
        description=f"Skill ({path.parent.name})",
        content_preview=_read_preview(path),
    )


def _emit_rule(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="rule",
        source="claude-code",
        tier=classify_asset("claude-code", "rule"),
        description=f"Rule ({path.stem})",
        content_preview=_read_preview(path),
    )


def _emit_from_settings(workspace: Path, path: Path) -> tuple[HarnessAsset, ...]:
    """Parse .claude/settings*.json and emit mcp_server + hook assets. Graceful on parse error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return ()
    if not isinstance(data, dict):
        return ()
    out: list[HarnessAsset] = []
    mcp_servers = data.get("mcpServers", {})
    if isinstance(mcp_servers, dict):
        for name in mcp_servers:
            out.append(
                HarnessAsset(
                    path=path,
                    kind="mcp_server",
                    source="claude-code",
                    tier=classify_asset("claude-code", "mcp_server"),
                    description=f"MCP server ({name})",
                    content_preview="",
                )
            )
    hooks = data.get("hooks", {})
    if isinstance(hooks, dict):
        for event in hooks:
            out.append(
                HarnessAsset(
                    path=path,
                    kind="hook",
                    source="claude-code",
                    tier=classify_asset("claude-code", "hook"),
                    description=f"Hook event ({event})",
                    content_preview="",
                )
            )
    return tuple(out)


def scan_claude_code(workspace: Path) -> tuple[HarnessAsset, ...]:
    """Discover Claude Code harness assets in ``workspace``."""
    if not workspace.is_dir():
        return ()
    assets: list[HarnessAsset] = []
    for path, is_dir in _walk(workspace):
        if is_dir:
            continue
        rel = path.relative_to(workspace)
        parts = rel.parts
        name = path.name
        # Top-level CLAUDE.md / CLAUDE.local.md
        if len(parts) == 1 and name in ("CLAUDE.md", "CLAUDE.local.md"):
            assets.append(_emit_instruction(workspace, path))
        # .claude/agents/*.md
        elif (
            len(parts) == 3
            and parts[0] == ".claude"
            and parts[1] == "agents"
            and name.endswith(".md")
        ):
            assets.append(_emit_agent(workspace, path))
        # .claude/skills/*/SKILL.md
        elif (
            len(parts) == 4
            and parts[0] == ".claude"
            and parts[1] == "skills"
            and parts[3] == "SKILL.md"
        ):
            assets.append(_emit_skill(workspace, path))
        # .claude/rules/*.md
        elif (
            len(parts) == 3
            and parts[0] == ".claude"
            and parts[1] == "rules"
            and name.endswith(".md")
        ):
            assets.append(_emit_rule(workspace, path))
        # .claude/settings*.json
        elif (
            len(parts) == 2
            and parts[0] == ".claude"
            and name.startswith("settings")
            and name.endswith(".json")
        ):
            assets.extend(_emit_from_settings(workspace, path))
    return tuple(assets)


def scan_codex(workspace: Path) -> tuple[HarnessAsset, ...]:
    """Discover Codex harness assets in ``workspace``.

    v0.1.0/v0.2.0 stub: returns an empty tuple (full implementation in v0.3.0+).
    """
    _ = workspace
    return ()


SCANNERS: dict[str, object] = {
    "claude-code": scan_claude_code,
    "codex": scan_codex,
}


def scan(source: str, workspace: Path) -> tuple[HarnessAsset, ...]:
    """Dispatch to the right scanner based on ``source``."""
    scanner = SCANNERS.get(source)
    if scanner is None:
        raise ValueError(f"unsupported source format: {source!r}")
    return scanner(workspace)  # type: ignore[operator]
