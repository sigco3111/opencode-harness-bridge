"""Classify inventory results into SafetyTier groups.

Implementation note (for other-PC worker)
----------------------------------------
v0.1.0 stub: returns an empty MigrationPlan. v0.2.0:

1. Call :func:`audit.inventory.scan` to discover raw assets
2. For each asset, assign a tier via :func:`safety.tiers.classify_asset`
3. Build a MigrationPlan with the workspace + source + target

The high-level :func:`migrate` function is the public entry point.
"""
from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.audit.inventory import scan
from opencode_harness_bridge.exceptions import InvalidSourceError, InvalidTargetError
from opencode_harness_bridge.models import MigrationPlan

#: Supported source formats (v0.1.0: claude-code; v0.3.0+: codex)
SOURCES: tuple[str, ...] = ("claude-code", "codex")

#: Supported target formats (v0.1.0: only opencode)
TARGETS: tuple[str, ...] = ("opencode",)


def migrate(
    *,
    source: str,
    target: str,
    workspace: Path | str,
) -> MigrationPlan:
    """High-level orchestrator: discover + classify → MigrationPlan.

    Parameters
    ----------
    source : str
        Source harness format. Must be one of :data:`SOURCES`.
    target : str
        Target harness format. Must be one of :data:`TARGETS` (only
        ``"opencode"`` in v0.1.0).
    workspace : Path | str
        Project workspace root to scan.

    Returns
    -------
    MigrationPlan
        Plan with discovered assets, tiers, and counts.

    Raises
    ------
    InvalidSourceError
        If ``source`` is not in :data:`SOURCES`.
    InvalidTargetError
        If ``target`` is not in :data:`TARGETS`.
    """
    if source not in SOURCES:
        raise InvalidSourceError(
            f"unsupported source: {source!r} (supported: {', '.join(SOURCES)})"
        )
    if target not in TARGETS:
        raise InvalidTargetError(
            f"unsupported target: {target!r} (supported: {', '.join(TARGETS)})"
        )

    ws = Path(workspace).expanduser().resolve()
    assets = scan(source, ws)
    return MigrationPlan(source=source, target=target, workspace=ws, assets=assets)
