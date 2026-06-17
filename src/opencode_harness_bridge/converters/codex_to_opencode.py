"""Codex → OpenCode converter (v0.3.0).

Converts a :class:`~opencode_harness_bridge.models.MigrationPlan` (built from
a Codex harness) into OpenCode-compatible config fragments using the same
schema as the Claude converter:

.. code-block:: python

    {
        "opencode_json_blocks": {...},
        "agents_md_blocks":      [...],
        "skills":                [...],
        "commands":              [...],
        "manual_steps":          [...],
    }

Secret safety
-------------
Default ``strict_secrets=True`` — any :attr:`SafetyTier.AUTO_APPLY` asset
whose content matches a secret pattern raises
:class:`~opencode_harness_bridge.exceptions.SecretLeakError`.

For ``mcp_server`` assets, env-var names are extracted and emitted as
``${KEY}`` placeholders. Literal env values are NEVER inlined.

Implementation note (for other-PC worker)
----------------------------------------
Codex and OpenCode both use ``AGENTS.md`` layering, so the mapping is
simpler than the Claude → OpenCode path. The hooks are Python files
(Codex-specific), so they cannot be auto-converted — they go to
``manual_steps`` with a "wrap as shell-callable" action.

Memories (``.codex/memories/*``) also go to ``manual_steps`` because
mapping to OpenCode's ``wiki/`` is a v0.4.0+ feature.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from opencode_harness_bridge.converters.shared import toml_to_dict
from opencode_harness_bridge.exceptions import MigrationError, SecretLeakError
from opencode_harness_bridge.models import MigrationPlan, SafetyTier
from opencode_harness_bridge.safety.tiers import looks_like_secret

__all__ = ["convert"]


_ENV_VAR_REF = "${NAME}"


def _secret_check(content: str, *, strict: bool) -> None:
    if strict and looks_like_secret(content):
        raise SecretLeakError("Secret detected in AUTO_APPLY Codex asset content")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _build_agents_md(plan: MigrationPlan, *, strict: bool) -> list[str]:
    """Render Codex instruction assets as a list of AGENTS.md body blocks."""
    blocks: list[str] = []
    for asset in plan.assets:
        if asset.kind != "instruction" or asset.tier != SafetyTier.AUTO_APPLY:
            continue
        content = _read(asset.path)
        _secret_check(content, strict=strict)
        blocks.append(content.strip())
    return blocks


def _build_agents(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Parse each .codex/agents/*.toml and emit an opencode.json `agent` entry."""
    agents: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.kind != "agent" or asset.tier != SafetyTier.AUTO_APPLY:
            continue
        try:
            data = toml_to_dict(asset.path)
        except MigrationError:
            continue
        agent_section = data.get("agent", {}) if isinstance(data, dict) else {}
        if not isinstance(agent_section, dict):
            agent_section = {}
        behavior = data.get("behavior", {}) if isinstance(data, dict) else {}
        agents.append(
            {
                "name": agent_section.get("name", asset.path.stem),
                "description": agent_section.get("description", ""),
                "behavior": behavior if isinstance(behavior, dict) else {},
                "prompt": _render_agent_prompt(agent_section, behavior),
            }
        )
    return agents


def _render_agent_prompt(agent_section: dict[str, Any], behavior: dict[str, Any]) -> str:
    """Render an agent TOML as a prompt string for OpenCode."""
    lines: list[str] = []
    name = agent_section.get("name", "")
    description = agent_section.get("description", "")
    if name:
        lines.append(f"# {name}")
    if description:
        lines.append(description)
        lines.append("")
    tone = behavior.get("tone", "")
    if tone:
        lines.append(f"Tone: {tone}")
    constraints = behavior.get("constraints", [])
    if isinstance(constraints, list) and constraints:
        lines.append("Constraints:")
        for c in constraints:
            lines.append(f"- {c}")
    return "\n".join(lines).strip()


def _build_opencode_json(plan: MigrationPlan) -> dict[str, Any]:
    """Build the opencode.json blocks from AUTO_APPLY + MODEL_ASSISTED assets."""
    out: dict[str, Any] = {}
    agents = _build_agents(plan)
    if agents:
        out["agent"] = agents
    mcp_entries: list[dict[str, Any]] = []
    seen_mcp_paths: set[Path] = set()
    for asset in plan.assets:
        if asset.kind != "mcp_server":
            continue
        if asset.path in seen_mcp_paths:
            continue
        seen_mcp_paths.add(asset.path)
        try:
            data = toml_to_dict(asset.path)
        except MigrationError:
            continue
        m = re.search(r"MCP server \(([^)]+)\)", asset.description)
        if not m:
            continue
        name = m.group(1)
        server_cfg = data.get("mcp_servers", {}).get(name, {}) if isinstance(data, dict) else {}
        if not isinstance(server_cfg, dict):
            server_cfg = {}
        env_placeholder: dict[str, str] = {}
        for env_key in server_cfg.get("env", {}):
            if isinstance(env_key, str):
                env_placeholder[env_key] = _ENV_VAR_REF.replace("NAME", env_key)
        mcp_entries.append(
            {
                "name": name,
                "command": server_cfg.get("command", ""),
                "args": server_cfg.get("args", []),
                "env": env_placeholder,
            }
        )
    if mcp_entries:
        out["mcp"] = mcp_entries
    return out


def _build_manual_steps(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Build manual_steps for non-AUTO_APPLY Codex assets."""
    steps: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.tier == SafetyTier.AUTO_APPLY:
            continue
        action = "review manually"
        if asset.kind == "hook":
            action = "wrap Python hook as shell-callable for OpenCode"
        elif asset.kind == "memory":
            action = "v0.4.0+ will add wiki/ mapping for Codex memories"
        steps.append(
            {
                "kind": asset.kind,
                "path": str(asset.path),
                "tier": asset.tier.value,
                "description": asset.description,
                "action": action,
            }
        )
    return steps


def convert(plan: MigrationPlan, *, strict_secrets: bool = True) -> dict[str, Any]:
    """Convert a Codex MigrationPlan into OpenCode config fragments."""
    return {
        "opencode_json_blocks": _build_opencode_json(plan),
        "agents_md_blocks": _build_agents_md(plan, strict=strict_secrets),
        "skills": [],
        "commands": [],
        "manual_steps": _build_manual_steps(plan),
    }
