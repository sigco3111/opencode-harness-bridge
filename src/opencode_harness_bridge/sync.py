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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def maintain(*, plan: object, target_dir: Path) -> MaintenanceReport:
    """Report-only drift detection between source plan and target_dir.

    Implementation deferred to T1.3 (GREEN phase). This stub raises
    NotImplementedError so the module is importable for T1.2 RED tests.
    """
    raise NotImplementedError("maintain() will be implemented in T1.3")
