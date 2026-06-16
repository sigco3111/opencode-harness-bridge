"""Smoke tests for domain models (v0.1.0)."""
from __future__ import annotations

import dataclasses
from pathlib import Path

from opencode_harness_bridge.models import (
    HarnessAsset,
    MigrationPlan,
    SafetyTier,
)


def test_safety_tier_is_str_enum() -> None:
    """SafetyTier values are strings (JSON-serializable)."""
    assert SafetyTier.AUTO_APPLY == "auto-apply-after-confirmation"
    assert SafetyTier.MODEL_ASSISTED == "model-assisted-manual"
    assert SafetyTier.USER_OWNED == "user-owned-secret-step"
    assert SafetyTier.OPENCODE_INCOMPATIBLE == "opencode-incompatible"


def test_safety_tier_count() -> None:
    """Exactly 4 tiers (3 inherited + 1 new for OpenCode)."""
    assert len(SafetyTier) == 4


def test_harness_asset_is_frozen() -> None:
    asset = HarnessAsset(
        path=Path("/tmp/CLAUDE.md"),
        kind="instruction",
        source="claude-code",
        tier=SafetyTier.AUTO_APPLY,
        description="Project instructions",
        content_preview="# My Project",
    )
    try:
        asset.kind = "other"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("HarnessAsset should be frozen")


def test_harness_asset_to_dict() -> None:
    asset = HarnessAsset(
        path=Path("/tmp/CLAUDE.md"),
        kind="instruction",
        source="claude-code",
        tier=SafetyTier.AUTO_APPLY,
    )
    d = asset.to_dict()
    assert d["path"] == "/tmp/CLAUDE.md"
    assert d["kind"] == "instruction"
    assert d["tier"] == "auto-apply-after-confirmation"


def test_migration_plan_to_dict() -> None:
    plan = MigrationPlan(
        source="claude-code",
        target="opencode",
        workspace=Path("/tmp/proj"),
    )
    d = plan.to_dict()
    assert d["source"] == "claude-code"
    assert d["target"] == "opencode"
    assert d["workspace"] == "/tmp/proj"
    assert d["summary"]["total"] == 0


def test_migration_plan_summary_counts_tiers() -> None:
    plan = MigrationPlan(
        source="claude-code",
        target="opencode",
        workspace=Path("/tmp/proj"),
        assets=(
            HarnessAsset(path=Path("a"), kind="instruction", source="claude-code", tier=SafetyTier.AUTO_APPLY),
            HarnessAsset(path=Path("b"), kind="instruction", source="claude-code", tier=SafetyTier.AUTO_APPLY),
            HarnessAsset(path=Path("c"), kind="hook", source="claude-code", tier=SafetyTier.MODEL_ASSISTED),
            HarnessAsset(path=Path("d"), kind="secret", source="claude-code", tier=SafetyTier.USER_OWNED),
        ),
    )
    s = plan.summary()
    assert s["total"] == 4
    assert s["auto-apply-after-confirmation"] == 2
    assert s["model-assisted-manual"] == 1
    assert s["user-owned-secret-step"] == 1
    assert s["opencode-incompatible"] == 0
