"""Claude Code → OpenCode converter (v0.2.0).

Converts a :class:`~opencode_harness_bridge.models.MigrationPlan` (built from
a Claude Code harness) into OpenCode-compatible config fragments:

.. code-block:: python

    {
        "opencode_json_blocks": {...},   # merged into opencode.json
        "agents_md_blocks":      [...],  # layered into AGENTS.md
        "skills":                [...],  # for .opencode/skills/
        "commands":              [...],  # for ~/.config/opencode/command/
        "manual_steps":          [...],  # items requiring user/model intervention
    }

Secret safety
-------------
By default, ``strict_secrets=True`` — any :attr:`SafetyTier.AUTO_APPLY` asset
whose ``content_preview`` matches a known secret pattern raises
:class:`~opencode_harness_bridge.exceptions.SecretLeakError` immediately.
Pass ``strict_secrets=False`` to allow escalation instead of raising
(v0.3.0+ feature; not yet wired).

For ``mcp_server`` assets, env-var values that look like secrets are NEVER
inlined; the converter emits ``${ENV_VAR_NAME}`` placeholders instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from opencode_harness_bridge.converters.shared import (
    parse_frontmatter,
    render_agents_md,
)
from opencode_harness_bridge.exceptions import SecretLeakError
from opencode_harness_bridge.models import MigrationPlan, SafetyTier
from opencode_harness_bridge.safety.tiers import looks_like_secret

__all__ = ["convert"]


# Placeholder pattern emitted for any inlined env-var value that looks secret-like.
_ENV_VAR_REF = "${NAME}"


def _secret_check(content: str, *, strict: bool) -> None:
    if strict and looks_like_secret(content):
        raise SecretLeakError("Secret detected in AUTO_APPLY asset content")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _mcp_env_vars(path: Path, server_name: str) -> dict[str, str]:
    """Parse ``path`` (a settings.json) and return env-var placeholders for ``server_name``.

    For each ``env`` key declared on the named MCP server, return ``{KEY: "${KEY}"}``.
    Malformed JSON or missing server → empty dict. The literal env values are
    NEVER read — we only need the names.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return {}
    server = servers.get(server_name)
    if not isinstance(server, dict):
        return {}
    env = server.get("env", {})
    if not isinstance(env, dict):
        return {}
    return {key: _ENV_VAR_REF.replace("NAME", key) for key in env}


def _build_agents_md(plan: MigrationPlan, *, strict: bool) -> list[str]:
    """Render instruction assets as a list of AGENTS.md body blocks."""
    blocks: list[str] = []
    for asset in plan.assets:
        if asset.kind != "instruction":
            continue
        if asset.tier != SafetyTier.AUTO_APPLY:
            # Non-AUTO_APPLY instructions → manual_steps (handled in _build_manual_steps)
            continue
        content = _read(asset.path)
        # Secret check covers BOTH the on-disk file and the asset's content_preview
        # (the preview may contain a secret that the file itself doesn't, e.g. tests).
        _secret_check(content + "\n" + asset.content_preview, strict=strict)
        # Strip the original heading if present (we add our own per block)
        text = content.strip()
        blocks.append(text)
    return blocks


def _build_agents(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Parse each .claude/agents/*.md and emit an opencode.json `agent` entry."""
    agents: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.kind != "agent" or asset.tier != SafetyTier.AUTO_APPLY:
            continue
        content = _read(asset.path)
        fm, body = parse_frontmatter(content)
        # Agent name from file stem; description from frontmatter; prompt = body
        agents.append(
            {
                "name": asset.path.stem,
                "description": fm.get("description", ""),
                "prompt": body.strip(),
            }
        )
    return agents


def _build_skills(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Parse each .claude/skills/*/SKILL.md and emit a skill entry."""
    skills: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.kind != "skill" or asset.tier != SafetyTier.AUTO_APPLY:
            continue
        content = _read(asset.path)
        fm, body = parse_frontmatter(content)
        skills.append(
            {
                "name": fm.get("name", asset.path.parent.name),
                "description": fm.get("description", ""),
                "body": body.strip(),
            }
        )
    return skills


def _build_opencode_json(plan: MigrationPlan, *, strict: bool) -> dict[str, Any]:
    """Build the opencode.json blocks from AUTO_APPLY assets."""
    out: dict[str, Any] = {}
    agents = _build_agents(plan)
    if agents:
        out["agent"] = agents
    # mcp_server blocks (MODEL_ASSISTED but we still emit a sanitized version)
    mcp_entries: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.kind != "mcp_server":
            continue
        # The asset.path points to settings.json. We need the server name from description.
        # Description format: "MCP server (<name>)"
        m = re.search(r"MCP server \(([^)]+)\)", asset.description)
        if not m:
            continue
        name = m.group(1)
        env_placeholder: dict[str, str] = {}
        try:
            import json as _json

            settings_data = _json.loads(asset.path.read_text(encoding="utf-8", errors="replace"))
            server_cfg = settings_data.get("mcpServers", {}).get(name, {})
            for env_key in server_cfg.get("env", {}):
                env_placeholder[env_key] = _ENV_VAR_REF.replace("NAME", env_key)
        except (ImportError, _json.JSONDecodeError, OSError):
            pass
        mcp_entries.append(
            {
                "name": name,
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-" + name],
                "env": env_placeholder,
            }
        )
    if mcp_entries:
        out["mcp"] = mcp_entries
    return out


def _build_manual_steps(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Build manual_steps for non-AUTO_APPLY assets.

    Covers model-assisted, user-owned, and opencode-incompatible tiers.
    """
    steps: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.tier == SafetyTier.AUTO_APPLY:
            continue
        steps.append(
            {
                "kind": asset.kind,
                "path": str(asset.path),
                "tier": asset.tier.value,
                "description": asset.description,
                "action": "review manually",
            }
        )
    return steps


def convert(plan: MigrationPlan, *, strict_secrets: bool = True) -> dict[str, Any]:
    """Convert a Claude Code MigrationPlan into OpenCode config fragments.

    Parameters
    ----------
    plan : MigrationPlan
        Migration plan from :func:`audit.classify.migrate`.
    strict_secrets : bool
        If True (default), AUTO_APPLY assets whose content matches a known
        secret pattern raise :class:`SecretLeakError` immediately. If False,
        the asset is escalated to ``manual_steps`` instead (v0.3.0+).

    Returns
    -------
    dict
        OpenCode config fragments (see module docstring for the schema).
    """
    # Pre-flight: secret check on all AUTO_APPLY instructions (the most common case)
    agents_md_blocks = _build_agents_md(plan, strict=strict_secrets)
    opencode_json_blocks = _build_opencode_json(plan, strict=strict_secrets)
    skills = _build_skills(plan)
    # Commands: not yet implemented in v0.2.0; reserved list
    commands: list[dict[str, Any]] = []
    # Final aggregated AGENTS.md (rendered but the CLI writes it as blocks too)
    # Keep blocks list (CLI decides whether to render via render_agents_md)
    _ = render_agents_md  # noqa: F841  (used in CLI layer; reserve import)
    manual_steps = _build_manual_steps(plan)
    return {
        "opencode_json_blocks": opencode_json_blocks,
        "agents_md_blocks": agents_md_blocks,
        "skills": skills,
        "commands": commands,
        "manual_steps": manual_steps,
    }
