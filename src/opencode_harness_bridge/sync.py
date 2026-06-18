"""Sync: bidirectional drift detection between source workspace and target OpenCode directory.

v0.4.0: REPORT-ONLY ``maintain`` subcommand. Detects what changed in the
source workspace since the last apply, and what exists in the target that
is no longer in the source. Does NOT apply changes — the user reviews
the report and re-runs ``convert --apply-safe`` manually.

Implementation note (for other-PC worker)
----------------------------------------
This module is content-only, report-only, zero-runtime-deps (per
ADR-0002). It reuses the converter's per-block rendering by calling
``convert_claude_code_to_opencode`` / ``convert_codex_to_opencode``
once and then diffing the resulting fragments against the target tree.

Two-tier diff strategy
----------------------
1. **Surface set diff** (cheap, high-level): compare the *set* of asset
   identifiers (agent names, skill names) in source vs target. Catches
   obvious adds/removes.

2. **Signature diff** (precise, content-based): for matched identifiers,
   compare the canonicalized content of the rendered asset. Catches
   drift (e.g., user edited the source and the target is now stale).

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


def _source_path_for(kind: str, name: str, workspace: Path, source: str) -> Path:
    """Resolve the source filesystem path for a given asset kind.

    Mirrors the convention used by the converters: agents live under
    ``.claude/agents/<name>.md`` (or ``.codex/agents/<name>.toml`` for
    codex), skills under ``.claude/skills/<name>/SKILL.md``, and
    instructions at the workspace root as ``CLAUDE.md`` or ``AGENTS.md``.
    """
    if kind == "agent":
        if source == "claude-code":
            return workspace / ".claude" / "agents" / f"{name}.md"
        return workspace / ".codex" / "agents" / f"{name}.toml"
    if kind == "skill":
        if source == "claude-code":
            return workspace / ".claude" / "skills" / name / "SKILL.md"
        return workspace / ".codex" / "skills" / name / "SKILL.md"
    if kind == "instruction":
        return workspace / "CLAUDE.md" if source == "claude-code" else workspace / "AGENTS.md"
    return workspace


def _expected_content_for(asset_kind: str, asset_data: Any, fragments: dict) -> str:
    """Return the canonical expected content for drift comparison.

    For ``"agent"`` and ``"mcp"`` (opencode.json blocks), returns the
    JSON-canonicalized string of the block (sorted keys, no ASCII
    escaping). For ``"skill"``, returns the skill body string. For
    ``"instruction"``, returns the joined AGENTS.md markdown text.

    This helper centralizes the "how to canonicalize each asset kind"
    logic so the per-kind diff functions stay focused on comparison.
    """
    if asset_kind in ("agent", "mcp"):
        return json.dumps(asset_data, sort_keys=True, ensure_ascii=False)
    if asset_kind == "skill":
        return asset_data.get("body", "")
    if asset_kind == "instruction":
        blocks = fragments.get("agents_md_blocks", []) or []
        return "\n\n---\n\n".join(blocks) if blocks else ""
    return ""


def _read_target_state(target_dir: Path) -> dict[str, Any]:
    """Snapshot the target directory's current state.

    Returns a dict with keys:
    - ``json_path``: Path to opencode.json
    - ``json_exists``: bool
    - ``json_data``: parsed opencode.json content (empty dict if missing/invalid)
    - ``agents_md_text``: string content of AGENTS.md (empty if missing)
    - ``skills_dir``: Path to skills/
    - ``skill_names``: set of skill basenames present in target skills/
    - ``agent_dict``: {name: block} dict from target opencode.json agent section
    """
    json_path = target_dir / "opencode.json"
    agents_md_path = target_dir / "AGENTS.md"
    skills_dir = target_dir / "skills"

    json_exists = json_path.is_file()
    json_data: dict = {}
    if json_exists:
        try:
            json_data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            json_data = {}

    agents_md_text = agents_md_path.read_text(encoding="utf-8") if agents_md_path.is_file() else ""

    skill_names: set[str] = set()
    if skills_dir.is_dir():
        for p in skills_dir.iterdir():
            if p.is_file() and p.suffix == ".md":
                skill_names.add(p.stem)

    agent_dict: dict[str, dict] = {
        a.get("name", ""): a for a in (json_data.get("agent", []) or []) if a.get("name", "")
    }

    return {
        "json_path": json_path,
        "json_exists": json_exists,
        "json_data": json_data,
        "agents_md_text": agents_md_text,
        "skills_dir": skills_dir,
        "skill_names": skill_names,
        "agent_dict": agent_dict,
    }


def _diff_agents(
    expected_agents: list[dict],
    target_agent_dict: dict[str, dict],
    workspace: Path,
    source: str,
) -> tuple[list[MaintenanceItem], list[MaintenanceItem], int]:
    """Compare expected agents against target agent dict.

    Returns (added, modified, unchanged_count).
    """
    added: list[MaintenanceItem] = []
    modified: list[MaintenanceItem] = []
    unchanged_count = 0

    for agent in expected_agents:
        name = agent.get("name", "")
        if not name:
            continue
        expected_block = _expected_content_for("agent", agent, {})
        target_block_raw = target_agent_dict.get(name)
        src_path = _source_path_for("agent", name, workspace, source)
        if target_block_raw is None:
            added.append(
                MaintenanceItem(
                    kind="agent",
                    path=src_path,
                    target_subpath=f"opencode.json#agent.{name}",
                    description=agent.get("description", f"Agent {name}"),
                    tier="auto-apply-after-confirmation",
                    action="added",
                )
            )
        else:
            target_block = _expected_content_for("agent", target_block_raw, {})
            if expected_block == target_block:
                unchanged_count += 1
            else:
                modified.append(
                    MaintenanceItem(
                        kind="agent",
                        path=src_path,
                        target_subpath=f"opencode.json#agent.{name}",
                        description=agent.get("description", f"Agent {name}"),
                        tier="auto-apply-after-confirmation",
                        action="modified",
                    )
                )

    return added, modified, unchanged_count


def _diff_instruction(
    expected_text: str,
    target_text: str,
    workspace: Path,
    source: str,
) -> tuple[list[MaintenanceItem], list[MaintenanceItem], int]:
    """Compare expected instruction text against target AGENTS.md.

    Returns (added, modified, unchanged_count). If expected_text is
    empty, returns ([], [], 0) — nothing to compare.
    """
    if not expected_text:
        return [], [], 0

    added: list[MaintenanceItem] = []
    modified: list[MaintenanceItem] = []
    src_path = _source_path_for("instruction", "", workspace, source)
    if not target_text:
        added.append(
            MaintenanceItem(
                kind="instruction",
                path=src_path,
                target_subpath="AGENTS.md",
                description="Project instructions",
                tier="auto-apply-after-confirmation",
                action="added",
            )
        )
    elif expected_text == target_text:
        return [], [], 1
    else:
        modified.append(
            MaintenanceItem(
                kind="instruction",
                path=src_path,
                target_subpath="AGENTS.md",
                description="Project instructions",
                tier="auto-apply-after-confirmation",
                action="modified",
            )
        )

    return added, modified, 0


def _diff_skills(
    expected_skills: list[dict],
    target_skill_names: set[str],
    target_skills_dir: Path,
    workspace: Path,
    source: str,
) -> tuple[list[MaintenanceItem], list[MaintenanceItem], int]:
    """Compare expected skills against target skills/ directory.

    Returns (added, modified, unchanged_count).
    """
    added: list[MaintenanceItem] = []
    modified: list[MaintenanceItem] = []
    unchanged_count = 0

    for skill in expected_skills:
        name = skill.get("name", "")
        if not name:
            continue
        expected_body = _expected_content_for("skill", skill, {})
        target_skill_path = target_skills_dir / f"{name}.md"
        src_path = _source_path_for("skill", name, workspace, source)
        if name not in target_skill_names:
            added.append(
                MaintenanceItem(
                    kind="skill",
                    path=src_path,
                    target_subpath=f"skills/{name}.md",
                    description=skill.get("description", f"Skill {name}"),
                    tier="auto-apply-after-confirmation",
                    action="added",
                )
            )
        else:
            try:
                target_body = target_skill_path.read_text(encoding="utf-8")
            except OSError:
                target_body = ""
            if expected_body == target_body:
                unchanged_count += 1
            else:
                modified.append(
                    MaintenanceItem(
                        kind="skill",
                        path=src_path,
                        target_subpath=f"skills/{name}.md",
                        description=skill.get("description", f"Skill {name}"),
                        tier="auto-apply-after-confirmation",
                        action="modified",
                    )
                )

    return added, modified, unchanged_count


def _diff_missing_sections(
    target_json_exists: bool,
    target_json_data: dict,
    expected_mcp: list[dict],
    expected_agents: list[dict],
    target_json_path: Path,
) -> list[MaintenanceItem]:
    """Emit one ``modified`` item per top-level key missing from target.

    Signals "re-run convert to populate this section" to the user.
    """
    missing: list[MaintenanceItem] = []
    if target_json_exists and expected_mcp and "mcp" not in target_json_data:
        missing.append(
            MaintenanceItem(
                kind="mcp_server",
                path=target_json_path,
                target_subpath="opencode.json#mcp",
                description="mcp section missing from target opencode.json",
                tier="model-assisted-manual",
                action="modified",
            )
        )
    if target_json_exists and expected_agents and "agent" not in target_json_data:
        missing.append(
            MaintenanceItem(
                kind="agent",
                path=target_json_path,
                target_subpath="opencode.json#agent",
                description="agent section missing from target opencode.json",
                tier="auto-apply-after-confirmation",
                action="modified",
            )
        )
    return missing


def _diff_removed(
    target_agent_dict: dict[str, dict],
    target_skill_names: set[str],
    expected_agent_names: set[str],
    expected_skill_names: set[str],
    target_dir: Path,
) -> list[MaintenanceItem]:
    """Emit one ``removed`` item per target asset with no source match."""
    removed: list[MaintenanceItem] = []
    for name in target_agent_dict:
        if name and name not in expected_agent_names:
            removed.append(
                MaintenanceItem(
                    kind="agent",
                    path=target_dir / "opencode.json",
                    target_subpath=f"opencode.json#agent.{name}",
                    description=f"Agent {name} (target-only)",
                    tier="auto-apply-after-confirmation",
                    action="removed",
                )
            )
    for name in target_skill_names:
        if name not in expected_skill_names:
            removed.append(
                MaintenanceItem(
                    kind="skill",
                    path=target_dir / "skills" / f"{name}.md",
                    target_subpath=f"skills/{name}.md",
                    description=f"Skill {name} (target-only)",
                    tier="auto-apply-after-confirmation",
                    action="removed",
                )
            )
    return removed


def _build_manual_steps(plan: MigrationPlan) -> list[dict[str, Any]]:
    """Surface non-AUTO_APPLY assets as manual steps for user action."""
    manual_steps: list[dict[str, Any]] = []
    for asset in plan.assets:
        if asset.tier.value == "auto-apply-after-confirmation":
            continue
        action_text = "review manually"
        if asset.kind == "hook":
            action_text = "wrap Python hook as shell-callable for OpenCode"
        elif asset.kind == "memory":
            action_text = "v0.4.0+ will add wiki/ mapping for Codex memories"
        manual_steps.append(
            {
                "kind": asset.kind,
                "path": str(asset.path),
                "tier": asset.tier.value,
                "description": asset.description,
                "action": action_text,
            }
        )
    return manual_steps


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

    state = _read_target_state(target_dir)

    expected_agents: list[dict] = fragments.get("opencode_json_blocks", {}).get("agent", []) or []
    expected_mcp: list[dict] = fragments.get("opencode_json_blocks", {}).get("mcp", []) or []
    expected_skills: list[dict] = fragments.get("skills", []) or []
    expected_agents_md = _expected_content_for("instruction", None, fragments)

    expected_agent_names = {a.get("name", "") for a in expected_agents}
    expected_skill_names = {s.get("name", "") for s in expected_skills}

    added: list[MaintenanceItem] = []
    modified: list[MaintenanceItem] = []
    unchanged_count = 0

    a, m, u = _diff_agents(expected_agents, state["agent_dict"], plan.workspace, source)
    added.extend(a)
    modified.extend(m)
    unchanged_count += u

    a, m, u = _diff_instruction(expected_agents_md, state["agents_md_text"], plan.workspace, source)
    added.extend(a)
    modified.extend(m)
    unchanged_count += u

    a, m, u = _diff_skills(
        expected_skills,
        state["skill_names"],
        state["skills_dir"],
        plan.workspace,
        source,
    )
    added.extend(a)
    modified.extend(m)
    unchanged_count += u

    modified.extend(
        _diff_missing_sections(
            state["json_exists"],
            state["json_data"],
            expected_mcp,
            expected_agents,
            state["json_path"],
        )
    )

    removed = _diff_removed(
        state["agent_dict"],
        state["skill_names"],
        expected_agent_names,
        expected_skill_names,
        target_dir,
    )

    manual_steps = _build_manual_steps(plan)

    return MaintenanceReport(
        source=source,
        target_dir=target_dir,
        added=tuple(added),
        modified=tuple(modified),
        removed=tuple(removed),
        unchanged_count=unchanged_count,
        manual_steps=tuple(manual_steps),
    )
