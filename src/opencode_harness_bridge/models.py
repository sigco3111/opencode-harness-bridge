"""Domain models for harness migration.

Implementation note (for other-PC worker)
----------------------------------------
Frozen dataclasses + StrEnum give us immutability and JSON-serializable
shapes. Use :class:`HarnessAsset` for a single discovered item (a CLAUDE.md
file, a .claude/agents/foo.md agent, a hook, etc.) and :class:`MigrationPlan`
to bundle a set of assets with the target format and a timestamp.

The 4-tier safety model is encoded in :enum:`SafetyTier`. The mapping from
asset kind to tier is the core of v0.2.0+ — see :mod:`safety.tiers`.

Trade-off: StrEnum vs Literal
-----------------------------
We use StrEnum (Python 3.11+) for two reasons:
1. JSON-serializable out of the box (``json.dumps(plan)`` works)
2. Can be compared to plain strings (``tier == "auto-apply"`` works)
If you need older Python support, switch to ``class SafetyTier(str, Enum)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class SafetyTier(StrEnum):
    """4-tier safety classification for harness migration.

    The first 3 tiers are borrowed from
    `danyuchn/claude-codex-harness-sync` and adapted:
    - ``auto-apply-after-confirmation``: safe to apply after user OK
    - ``model-assisted-manual``: semantic translation needed (model explains + applies)
    - ``user-owned-secret-step``: secrets, user handles manually

    The 4th tier is new for the OpenCode target:
    - ``opencode-incompatible``: cannot auto-convert, manual work required
    """

    AUTO_APPLY = "auto-apply-after-confirmation"
    MODEL_ASSISTED = "model-assisted-manual"
    USER_OWNED = "user-owned-secret-step"
    OPENCODE_INCOMPATIBLE = "opencode-incompatible"


#: Allowed source harness formats (v0.1.0 supports the first; v0.3.0+ adds the second)
SourceFormat = str  # "claude-code" | "codex" — see classify.py for the literal list

#: Allowed target harness formats (v0.1.0: only "opencode")
TargetFormat = str  # "opencode" — see classify.py for the literal list


@dataclass(frozen=True)
class HarnessAsset:
    """A single discovered item in a source harness.

    Attributes
    ----------
    path : Path
        Absolute path to the asset on disk.
    kind : str
        What kind of asset (e.g. ``"instruction"``, ``"agent"``, ``"hook"``,
        ``"skill"``, ``"mcp_server"``, ``"memory"``, ``"rule"``, ``"secret"``).
    source : SourceFormat
        Which harness the asset came from (``"claude-code"`` or ``"codex"``).
    tier : SafetyTier
        Safety classification for migration to the target.
    description : str
        Human-readable description (e.g. ``"Project instructions (CLAUDE.md)"``).
    content_preview : str
        First ~200 chars of the file content (for human review in reports).
    """

    path: Path
    kind: str
    source: SourceFormat
    tier: SafetyTier
    description: str = ""
    content_preview: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict (Path → str, Enum → str)."""
        return {
            "path": str(self.path),
            "kind": self.kind,
            "source": self.source,
            "tier": self.tier.value,
            "description": self.description,
            "content_preview": self.content_preview,
        }


@dataclass(frozen=True)
class MigrationPlan:
    """Bundle of all assets discovered for a migration, with the target.

    Use :meth:`to_dict` for JSON serialization (reports, audit logs).
    Use :meth:`summary` for a human-readable tier breakdown.
    """

    source: SourceFormat
    target: TargetFormat
    workspace: Path
    assets: tuple[HarnessAsset, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "workspace": str(self.workspace),
            "created_at": self.created_at.isoformat(),
            "assets": [a.to_dict() for a in self.assets],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, int]:
        """Count assets per safety tier (and total)."""
        out: dict[str, int] = {"total": len(self.assets)}
        for tier in SafetyTier:
            out[tier.value] = sum(1 for a in self.assets if a.tier == tier)
        return out
