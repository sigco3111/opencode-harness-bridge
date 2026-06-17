"""Inventory: scan a source harness directory and list discovered assets.

v0.2.0: real Claude Code scanner. Discovers 6 asset kinds:
- ``instruction`` from CLAUDE.md, CLAUDE.local.md
- ``agent`` from .claude/agents/*.md
- ``skill`` from .claude/skills/*/SKILL.md
- ``rule`` from .claude/rules/*.md
- ``mcp_server`` from .claude/settings*.json -> mcpServers
- ``hook`` from .claude/settings*.json -> hooks events

v0.3.0: real Codex scanner. Discovers 5 asset kinds:
- ``instruction`` from top-level AGENTS.md
- ``agent`` from .codex/agents/*.toml
- ``mcp_server`` from .codex/config.toml + .codex/settings.toml -> [mcp_servers.*]
- ``hook`` from .codex/hooks/*.py
- ``memory`` from .codex/memories/*

Heavy directories are pruned: .git, node_modules, __pycache__, dist,
build, venv, .venv, vendor, .opencode-migration, .migration-cache.

Malformed settings.json / config.toml files are skipped silently (no crash).
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


def _emit_codex_instruction(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="instruction",
        source="codex",
        tier=classify_asset("codex", "instruction"),
        description=f"Project instructions ({path.name})",
        content_preview=_read_preview(path),
    )


def _emit_codex_agent(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="agent",
        source="codex",
        tier=classify_asset("codex", "agent"),
        description=f"Agent ({path.stem})",
        content_preview=_read_preview(path),
    )


def _emit_codex_hook(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="hook",
        source="codex",
        tier=classify_asset("codex", "hook"),
        description=f"Hook ({path.name})",
        content_preview=_read_preview(path),
    )


def _emit_codex_memory(workspace: Path, path: Path) -> HarnessAsset:
    return HarnessAsset(
        path=path,
        kind="memory",
        source="codex",
        tier=classify_asset("codex", "memory"),
        description=f"Memory ({path.name})",
        content_preview=_read_preview(path),
    )


def _emit_codex_from_config(workspace: Path, config_path: Path) -> tuple[HarnessAsset, ...]:
    """Parse .codex/config.toml (or settings.toml) and emit mcp_server assets. Graceful on parse error."""
    import tomllib

    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8", errors="replace"))
    except (tomllib.TOMLDecodeError, OSError):
        return ()
    if not isinstance(data, dict):
        return ()
    out: list[HarnessAsset] = []
    mcp_servers = data.get("mcp_servers", {})
    if isinstance(mcp_servers, dict):
        for name in mcp_servers:
            if isinstance(name, str):
                out.append(
                    HarnessAsset(
                        path=config_path,
                        kind="mcp_server",
                        source="codex",
                        tier=classify_asset("codex", "mcp_server"),
                        description=f"MCP server ({name})",
                        content_preview="",
                    )
                )
    return tuple(out)


def scan_codex(workspace: Path) -> tuple[HarnessAsset, ...]:
    """Discover Codex harness assets in ``workspace``.

    Discovers:
    - top-level AGENTS.md -> kind="instruction"
    - .codex/agents/*.toml -> kind="agent"
    - .codex/config.toml + .codex/settings.toml -> one mcp_server per [mcp_servers.*] entry
    - .codex/hooks/*.py -> kind="hook" (1 per file)
    - .codex/memories/* -> kind="memory" (1 per file)

    Heavy directories are pruned; malformed config.toml files are skipped silently.
    """
    if not workspace.is_dir():
        return ()
    assets: list[HarnessAsset] = []
    config_paths: list[Path] = []
    for path, is_dir in _walk(workspace):
        if is_dir:
            continue
        rel = path.relative_to(workspace)
        parts = rel.parts
        name = path.name
        if len(parts) == 1 and name == "AGENTS.md":
            assets.append(_emit_codex_instruction(workspace, path))
        elif (
            len(parts) == 3
            and parts[0] == ".codex"
            and parts[1] == "agents"
            and name.endswith(".toml")
        ):
            assets.append(_emit_codex_agent(workspace, path))
        elif (
            len(parts) == 3
            and parts[0] == ".codex"
            and parts[1] == "hooks"
            and name.endswith(".py")
        ):
            assets.append(_emit_codex_hook(workspace, path))
        elif len(parts) >= 3 and parts[0] == ".codex" and parts[1] == "memories":
            assets.append(_emit_codex_memory(workspace, path))
        elif (
            len(parts) == 2
            and parts[0] == ".codex"
            and (name == "config.toml" or name == "settings.toml")
        ):
            config_paths.append(path)
    for cfg in config_paths:
        assets.extend(_emit_codex_from_config(workspace, cfg))
    return tuple(assets)


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
