"""opencode-harness-bridge: Safely migrate Claude Code/Codex harnesses to OpenCode.

This package implements a 3+1 tier safety policy (auto-apply, model-assisted,
user-owned, opencode-incompatible) for migrating agent harness configurations
from Claude Code or Codex to OpenCode.

Public API
----------
- :func:`migrate` — high-level orchestrator (zero-deps, in-process)
- :class:`HarnessAsset` — domain model for a discovered harness item
- :class:`MigrationPlan` — bundle of assets + tier classifications
- :enum:`SafetyTier` — 4-tier classification enum

Example
-------
    >>> from opencode_harness_bridge import migrate
    >>> plan = migrate(source="claude-code", target="opencode", workspace="~/proj")
    >>> for asset in plan.assets:
    ...     print(asset.path, asset.tier, asset.action)

Note
----
Zero-deps guarantee: this package does not import Claude Code, Codex, or
OpenCode. It reads files from disk and emits plan data structures. The
heavy lifting (actual file modifications) is left to v0.2.0+ where the
caller is responsible for invoking the model to apply model-assisted
changes.
"""

from __future__ import annotations

__version__ = "0.4.0"

__all__ = [
    "HarnessAsset",
    "MigrationPlan",
    "SafetyTier",
    "migrate",
]


def __getattr__(name: str):
    """Lazy import to avoid forcing heavy imports on simple usage."""
    if name in ("HarnessAsset", "MigrationPlan", "SafetyTier"):
        from .models import HarnessAsset, MigrationPlan, SafetyTier  # noqa: F401

        return locals()[name]
    if name == "migrate":
        from .audit.classify import migrate

        return migrate
    raise AttributeError(f"module 'opencode_harness_bridge' has no attribute {name!r}")
