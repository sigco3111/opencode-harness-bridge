"""Sync: bidirectional drift detection between source workspace and target OpenCode directory.

v0.4.0: REPORT-ONLY ``maintain`` subcommand. Detects what changed in the
source workspace since the last apply, and what exists in the target that
is no longer in the source. Does NOT apply changes — the user reviews
the report and re-runs ``convert --apply-safe`` manually.

Implementation note (for other-PC worker)
----------------------------------------
This module is content-only, report-only, zero-runtime-deps (per
ADR-0002). It reuses the converter's ``_build_opencode_json`` and
``_build_manual_steps`` helpers via lazy import to avoid duplicating
the per-asset-kind rendering logic.

Two-tier diff strategy
----------------------
1. **Surface set diff** (cheap, high-level): compare the *set* of asset
   identifiers (agent names, skill names, mcp server names) in source
   vs target. Catches obvious adds/removes.

2. **Signature diff** (precise, content-based): for matched identifiers,
   compare the sha256 of the rendered asset content. Catches drift
   (e.g., user edited the source and the target is now stale).

The :func:`maintain` function combines both tiers into a single
:class:`MaintenanceReport`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opencode_harness_bridge.exceptions import InvalidSourceError, InvalidTargetError
from opencode_harness_bridge.models import MigrationPlan

__all__ = ["MaintenanceItem", "MaintenanceReport", "maintain"]


@dataclass(frozen=True)
class MaintenanceItem:
    """A single asset diff entry in a :class:`MaintenanceReport`.

    Attributes
    ----------
    kind : str
        The asset kind (e.g., ``"agent"``, ``"skill"``, ``"mcp_server"``,
        ``"hook"``, ``"memory"``, ``"rule"``, ``"instruction"``).
    path : Path
        Absolute path to the source asset (or the path that was
        used to derive this entry, for removed items).
    target_subpath : str
        Path (or JSON-pointer) within the target OpenCode directory.
        Examples: ``"opencode.json#agent.qa-reviewer"``,
        ``"AGENTS.md"``, ``"skills/commit-helper.md"``.
    description : str
        Human-readable description of the asset.
    tier : str
        The :class:`SafetyTier` value (e.g., ``"auto-apply-after-confirmation"``).
    action : str
        One of ``"added"``, ``"modified"``, ``"removed"``,
        ``"manual"`` (model-assisted / user-owned — needs human action).
    """

    kind: str
    path: Path
    target_subpath: str
    description: str
    tier: str
    action: str


@dataclass(frozen=True)
class MaintenanceReport:
    """Report-only output of :func:`maintain`.

    Attributes
    ----------
    source : str
        Source harness format (``"claude-code"`` or ``"codex"``).
    target_dir : Path
        Target OpenCode directory that was diffed against.
    added : tuple[MaintenanceItem, ...]
        Assets present in the source but missing from the target.
    modified : tuple[MaintenanceItem, ...]
        Assets present in both but with content drift (sha256 mismatch).
    removed : tuple[MaintenanceItem, ...]
        Assets present in the target but no longer in the source.
    unchanged_count : int
        Number of source assets that matched the target exactly.
    manual_steps : tuple[dict[str, Any], ...]
        Non-AUTO_APPLY assets (hooks, memories, secrets, etc.) that
        require user action. Each dict has keys ``kind``, ``path``,
        ``tier``, ``description``, ``action``.
    """

    source: str
    target_dir: Path
    added: tuple[MaintenanceItem, ...]
    modified: tuple[MaintenanceItem, ...]
    removed: tuple[MaintenanceItem, ...]
    unchanged_count: int
    manual_steps: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict (Path → str)."""
        return {
            "source": self.source,
            "target_dir": str(self.target_dir),
            "added": [_item_to_dict(i) for i in self.added],
            "modified": [_item_to_dict(i) for i in self.modified],
            "removed": [_item_to_dict(i) for i in self.removed],
            "unchanged_count": self.unchanged_count,
            "manual_steps": list(self.manual_steps),
        }

    def to_markdown(self) -> str:
        """Render a human-readable markdown report.

        Stub for v0.4.0 step T1.1 — T2.3 will implement the full
        rendering (header line, sections, item tables).
        """
        return ""


def _item_to_dict(item: MaintenanceItem) -> dict[str, Any]:
    """Helper: convert a single :class:`MaintenanceItem` to a dict."""
    return {
        "kind": item.kind,
        "path": str(item.path),
        "target_subpath": item.target_subpath,
        "description": item.description,
        "tier": item.tier,
        "action": item.action,
    }


def maintain(*, plan: MigrationPlan, target_dir: Path) -> MaintenanceReport:
    """Report-only drift detection between source plan and target_dir.

    Content-only diff: per-block JSON canonicalization for opencode.json
    sections, exact-match for AGENTS.md and skill files. Ignores
    permissions, ownership, symlinks (Q1: content-only).

    NO file writes — this is REPORT-ONLY (Q2). The user reviews the
    report and re-runs ``convert --apply-safe`` manually.

    Algorithm (two-tier)
    -------------------
    1. Per-block comparison: for each source asset, check if the
       rendered content matches the corresponding section in
       target opencode.json (or the AGENTS.md / skills/<name>.md file).
       Categorize as added / modified / unchanged.
       Mcp blocks are excluded from this tier — they are
       MODEL_ASSISTED (not AUTO_APPLY) and are surfaced via
       ``manual_steps`` and the missing-section detector only.
    2. Removed detection: for each agent/skill in target that has no
       match in source, emit a removed item.
    3. Missing-section detection: if target opencode.json exists but is
       missing a top-level key that source expects (e.g., target has
       ``agent`` but no ``mcp``), emit one ``modified`` item for the
       missing key (signals "re-run convert to populate this section").
    4. Manual steps: non-AUTO_APPLY assets (hooks/memories/rules/secrets/mcps)
       are listed in ``manual_steps`` for user action — they cannot be
       auto-converted to OpenCode.

    Raises ``InvalidTargetError`` if ``target_dir`` is not a directory.
    """
    from opencode_harness_bridge.converters import (
        convert_claude_code_to_opencode,
        convert_codex_to_opencode,
    )

    target_dir = Path(target_dir).expanduser().resolve()
    if not target_dir.is_dir():
        raise InvalidTargetError(
            f"target directory does not exist or is not a directory: {target_dir}"
        )

    source = plan.source
    if source == "claude-code":
        fragments = convert_claude_code_to_opencode(plan, strict_secrets=False)
    elif source == "codex":
        fragments = convert_codex_to_opencode(plan, strict_secrets=False)
    else:
        raise InvalidSourceError(f"unsupported source: {source!r}")

    target_json_path = target_dir / "opencode.json"
    target_agents_md_path = target_dir / "AGENTS.md"
    target_skills_dir = target_dir / "skills"

    target_json_data: dict = {}
    target_json_exists = target_json_path.is_file()
    if target_json_exists:
        try:
            target_json_data = json.loads(target_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            target_json_data = {}
    target_agents_md_text = (
        target_agents_md_path.read_text(encoding="utf-8")
        if target_agents_md_path.is_file()
        else ""
    )
    target_skill_names: set[str] = set()
    if target_skills_dir.is_dir():
        for p in target_skills_dir.iterdir():
            if p.is_file() and p.suffix == ".md":
                target_skill_names.add(p.stem)

    expected_agents: list[dict] = (
        fragments.get("opencode_json_blocks", {}).get("agent", []) or []
    )
    expected_mcp: list[dict] = (
        fragments.get("opencode_json_blocks", {}).get("mcp", []) or []
    )
    expected_agents_md_blocks: list[str] = (
        fragments.get("agents_md_blocks", []) or []
    )
    expected_skills: list[dict] = fragments.get("skills", []) or []
    expected_agents_md = (
        "\n\n---\n\n".join(expected_agents_md_blocks)
        if expected_agents_md_blocks
        else ""
    )

    expected_agent_names = {a.get("name", "") for a in expected_agents}
    expected_mcp_names = {m.get("name", "") for m in expected_mcp}
    expected_skill_names = {s.get("name", "") for s in expected_skills}

    target_agent_dict: dict[str, dict] = {
        a.get("name", ""): a
        for a in (target_json_data.get("agent", []) or [])
        if a.get("name", "")
    }
    target_mcp_dict: dict[str, dict] = {
        m.get("name", ""): m
        for m in (target_json_data.get("mcp", []) or [])
        if m.get("name", "")
    }

    added: list[MaintenanceItem] = []
    modified: list[MaintenanceItem] = []
    unchanged_count = 0

    for agent in expected_agents:
        name = agent.get("name", "")
        if not name:
            continue
        expected_block = json.dumps(agent, sort_keys=True, ensure_ascii=False)
        target_block_raw = target_agent_dict.get(name)
        if target_block_raw is None:
            added.append(MaintenanceItem(
                kind="agent",
                path=plan.workspace / ".claude" / "agents" / f"{name}.md",
                target_subpath=f"opencode.json#agent.{name}",
                description=agent.get("description", f"Agent {name}"),
                tier="auto-apply-after-confirmation",
                action="added",
            ))
        else:
            target_block = json.dumps(target_block_raw, sort_keys=True, ensure_ascii=False)
            if expected_block == target_block:
                unchanged_count += 1
            else:
                modified.append(MaintenanceItem(
                    kind="agent",
                    path=plan.workspace / ".claude" / "agents" / f"{name}.md",
                    target_subpath=f"opencode.json#agent.{name}",
                    description=agent.get("description", f"Agent {name}"),
                    tier="auto-apply-after-confirmation",
                    action="modified",
                ))

    # Mcp blocks are NOT iterated here: they are MODEL_ASSISTED tier and
    # are surfaced via ``manual_steps`` and the missing-section detector.

    if expected_agents_md:
        if not target_agents_md_text:
            added.append(MaintenanceItem(
                kind="instruction",
                path=(
                    plan.workspace / "CLAUDE.md"
                    if source == "claude-code"
                    else plan.workspace / "AGENTS.md"
                ),
                target_subpath="AGENTS.md",
                description="Project instructions",
                tier="auto-apply-after-confirmation",
                action="added",
            ))
        elif expected_agents_md == target_agents_md_text:
            unchanged_count += 1
        else:
            modified.append(MaintenanceItem(
                kind="instruction",
                path=(
                    plan.workspace / "CLAUDE.md"
                    if source == "claude-code"
                    else plan.workspace / "AGENTS.md"
                ),
                target_subpath="AGENTS.md",
                description="Project instructions",
                tier="auto-apply-after-confirmation",
                action="modified",
            ))

    for skill in expected_skills:
        name = skill.get("name", "")
        if not name:
            continue
        expected_body = skill.get("body", "")
        target_skill_path = target_skills_dir / f"{name}.md"
        if name not in target_skill_names:
            added.append(MaintenanceItem(
                kind="skill",
                path=(
                    plan.workspace / ".claude" / "skills" / name / "SKILL.md"
                    if source == "claude-code"
                    else plan.workspace / ".codex" / "skills" / name / "SKILL.md"
                ),
                target_subpath=f"skills/{name}.md",
                description=skill.get("description", f"Skill {name}"),
                tier="auto-apply-after-confirmation",
                action="added",
            ))
        else:
            try:
                target_body = target_skill_path.read_text(encoding="utf-8")
            except OSError:
                target_body = ""
            if expected_body == target_body:
                unchanged_count += 1
            else:
                modified.append(MaintenanceItem(
                    kind="skill",
                    path=(
                        plan.workspace / ".claude" / "skills" / name / "SKILL.md"
                        if source == "claude-code"
                        else plan.workspace / ".codex" / "skills" / name / "SKILL.md"
                    ),
                    target_subpath=f"skills/{name}.md",
                    description=skill.get("description", f"Skill {name}"),
                    tier="auto-apply-after-confirmation",
                    action="modified",
                ))

    if target_json_exists and expected_mcp and "mcp" not in target_json_data:
        modified.append(MaintenanceItem(
            kind="mcp_server",
            path=target_json_path,
            target_subpath="opencode.json#mcp",
            description="mcp section missing from target opencode.json",
            tier="model-assisted-manual",
            action="modified",
        ))
    if target_json_exists and expected_agents and "agent" not in target_json_data:
        modified.append(MaintenanceItem(
            kind="agent",
            path=target_json_path,
            target_subpath="opencode.json#agent",
            description="agent section missing from target opencode.json",
            tier="auto-apply-after-confirmation",
            action="modified",
        ))

    removed: list[MaintenanceItem] = []
    for name in target_agent_dict:
        if name and name not in expected_agent_names:
            removed.append(MaintenanceItem(
                kind="agent",
                path=target_dir / "opencode.json",
                target_subpath=f"opencode.json#agent.{name}",
                description=f"Agent {name} (target-only)",
                tier="auto-apply-after-confirmation",
                action="removed",
            ))
    for name in target_skill_names:
        if name not in expected_skill_names:
            removed.append(MaintenanceItem(
                kind="skill",
                path=target_dir / "skills" / f"{name}.md",
                target_subpath=f"skills/{name}.md",
                description=f"Skill {name} (target-only)",
                tier="auto-apply-after-confirmation",
                action="removed",
            ))

    manual_steps: list[dict] = []
    for asset in plan.assets:
        if asset.tier.value == "auto-apply-after-confirmation":
            continue
        action_text = "review manually"
        if asset.kind == "hook":
            action_text = "wrap Python hook as shell-callable for OpenCode"
        elif asset.kind == "memory":
            action_text = "v0.4.0+ will add wiki/ mapping for Codex memories"
        manual_steps.append({
            "kind": asset.kind,
            "path": str(asset.path),
            "tier": asset.tier.value,
            "description": asset.description,
            "action": action_text,
        })

    return MaintenanceReport(
        source=source,
        target_dir=target_dir,
        added=tuple(added),
        modified=tuple(modified),
        removed=tuple(removed),
        unchanged_count=unchanged_count,
        manual_steps=tuple(manual_steps),
    )
