"""Real-converter tests for claude_code_to_opencode.py (v0.2.0)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.converters.claude_code_to_opencode import convert
from opencode_harness_bridge.exceptions import SecretLeakError
from opencode_harness_bridge.models import HarnessAsset, MigrationPlan, SafetyTier


def _make_plan_with_one_asset(asset: HarnessAsset, workspace: Path) -> MigrationPlan:
    return MigrationPlan(
        source="claude-code", target="opencode", workspace=workspace, assets=(asset,)
    )


# ---- Schema / happy path -------------------------------------------------


def test_convert_returns_required_keys(sample_claude_harness: Path) -> None:
    """convert(plan) returns a dict with the 5 documented top-level keys."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    out = convert(plan)
    assert isinstance(out, dict)
    for key in ("opencode_json_blocks", "agents_md_blocks", "skills", "commands", "manual_steps"):
        assert key in out, f"missing key: {key}"


def test_convert_emits_agents_md_for_instruction(sample_claude_harness: Path) -> None:
    """CLAUDE.md → non-empty agents_md_blocks (the instruction text is rendered)."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    out = convert(plan)
    assert isinstance(out["agents_md_blocks"], list)
    assert len(out["agents_md_blocks"]) >= 1
    # The first block should mention 'pytest' (from the CLAUDE.md body)
    assert any("pytest" in block for block in out["agents_md_blocks"])


def test_convert_emits_opencode_json_agents(sample_claude_harness: Path) -> None:
    """.claude/agents/*.md → opencode_json_blocks['agent'] contains one entry per agent."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    out = convert(plan)
    agent_block = out["opencode_json_blocks"].get("agent")
    assert agent_block is not None
    # The fixture has 2 agents (qa-reviewer, refactor-planner)
    names = {a.get("name") for a in agent_block} if isinstance(agent_block, list) else set()
    assert "qa-reviewer" in names
    assert "refactor-planner" in names


# ---- mcp_server with env-var placeholders (NEVER inline secrets) --------


def test_convert_emits_mcp_with_env_placeholders(sample_claude_harness: Path) -> None:
    """mcp_server env values are NEVER inlined as literals. They become placeholders.

    The fixture's settings.json has GITHUB_TOKEN="ghp_xxxxxxxx..." which is a secret-like
    placeholder string. The literal value MUST NOT appear in the converter output.
    The env-var name should be referenced as a placeholder.
    """
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    out = convert(plan)
    serialized = json.dumps(out["opencode_json_blocks"])
    # The literal fake secret value MUST NOT appear in the output
    assert "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" not in serialized, (
        "Literal secret value was inlined in opencode_json_blocks"
    )
    # The env-var name SHOULD appear (placeholder reference)
    assert "GITHUB_TOKEN" in serialized, "GITHUB_TOKEN env-var name not referenced"


def test_convert_hooks_go_to_manual_steps_model_assisted(sample_claude_harness: Path) -> None:
    """Hooks (MODEL_ASSISTED) appear in manual_steps, NOT in opencode_json_blocks."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    out = convert(plan)
    # manual_steps has hook entries
    assert any("hook" in s.get("kind", "").lower() for s in out["manual_steps"])
    # And the opencode_json_blocks must NOT contain a top-level "hooks" key
    assert "hooks" not in out["opencode_json_blocks"]


# ---- SecretLeakError (scenario S6) ---------------------------------------


def test_convert_raises_secretleak_on_synthetic_secret(sample_claude_harness: Path) -> None:
    """strict_secrets=True + secret in AUTO_APPLY content → SecretLeakError.

    Construct a synthetic plan with one instruction asset whose content_preview
    contains the synthetic sk-... key. This bypasses the file system.
    """
    secret_text = (
        "# Instructions\n\n"
        "My OpenAI key: sk-abcdef1234567890abcdef1234567890\n"
        "Do not commit this.\n"
    )
    asset = HarnessAsset(
        path=sample_claude_harness / "CLAUDE.md",
        kind="instruction",
        source="claude-code",
        tier=SafetyTier.AUTO_APPLY,
        description="synthetic",
        content_preview=secret_text[:200],
    )
    plan = _make_plan_with_one_asset(asset, sample_claude_harness)
    with pytest.raises(SecretLeakError):
        convert(plan, strict_secrets=True)
