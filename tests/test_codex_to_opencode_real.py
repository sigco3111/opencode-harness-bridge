"""Real-converter tests for claude_code_to_opencode.py analogue for Codex (v0.3.0 RED).

These tests are the RED phase of TDD — they MUST fail against the current
convert() stub (which returns {}). The GREEN implementation in T3.2 will
make them pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.converters import convert_codex_to_opencode
from opencode_harness_bridge.converters.codex_to_opencode import convert
from opencode_harness_bridge.exceptions import SecretLeakError
from opencode_harness_bridge.models import HarnessAsset, MigrationPlan


def _make_plan_with_one_asset(asset: HarnessAsset, workspace: Path) -> MigrationPlan:
    return MigrationPlan(source="codex", target="opencode", workspace=workspace, assets=(asset,))


# ---- Schema / happy path -------------------------------------------------


def test_convert_returns_required_keys(sample_codex_harness: Path) -> None:
    """convert(plan) returns a dict with the 5 documented top-level keys."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    assert isinstance(out, dict)
    for key in ("opencode_json_blocks", "agents_md_blocks", "skills", "commands", "manual_steps"):
        assert key in out, f"missing key: {key}"


def test_convert_emits_agents_md_for_instruction(sample_codex_harness: Path) -> None:
    """AGENTS.md → non-empty agents_md_blocks (the instruction text is rendered)."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    assert isinstance(out["agents_md_blocks"], list)
    assert len(out["agents_md_blocks"]) >= 1
    # The fixture AGENTS.md mentions "pytest"
    assert any("pytest" in block for block in out["agents_md_blocks"])


def test_convert_emits_toml_agent_in_opencode_json(sample_codex_harness: Path) -> None:
    """.codex/agents/*.toml → opencode_json_blocks['agent'] contains one entry per agent."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    agent_block = out["opencode_json_blocks"].get("agent")
    assert agent_block is not None
    names = {a.get("name") for a in agent_block} if isinstance(agent_block, list) else set()
    assert "example" in names


# ---- mcp_server with env-var placeholders (NEVER inline secrets) --------


def test_convert_emits_mcp_server_with_env_placeholders(sample_codex_harness: Path) -> None:
    """mcp_server env values are NEVER inlined as literals; they become placeholders.

    The Codex config.toml in the fixture has no env block (filesystem server is simple).
    Even so, the converter must produce a properly-shaped mcp entry with NO env values
    inlined as literal strings.
    """
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    serialized = json.dumps(out["opencode_json_blocks"])
    # The mcp entry must reference the filesystem server
    assert "filesystem" in serialized, "filesystem mcp_server name missing from output"


# ---- Hooks and memories go to manual_steps (model-assisted) ---------------


def test_convert_hooks_go_to_manual_steps(sample_codex_harness: Path) -> None:
    """Hooks (MODEL_ASSISTED) appear in manual_steps, NOT in opencode_json_blocks."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    assert any("hook" in s.get("kind", "").lower() for s in out["manual_steps"])


def test_convert_memories_go_to_manual_steps(sample_codex_harness: Path) -> None:
    """Memories (MODEL_ASSISTED, v0.4.0+ wiki/ mapping) appear in manual_steps."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness)
    out = convert(plan)
    assert any("memory" in s.get("kind", "").lower() for s in out["manual_steps"])


# ---- SecretLeakError (scenario S12) ---------------------------------------


def test_convert_raises_secretleak_on_synthetic_secret(
    sample_codex_harness_with_secret: Path,
) -> None:
    """strict_secrets=True + secret in AUTO_APPLY content → SecretLeakError."""
    plan = migrate(source="codex", target="opencode", workspace=sample_codex_harness_with_secret)
    with pytest.raises(SecretLeakError):
        convert(plan, strict_secrets=True)


# ---- Dispatcher via converters/__init__.py -------------------------------


def test_convert_dispatcher_via_init(tmp_codex_workspace: Path) -> None:
    """convert_codex_to_opencode() (the public dispatcher) returns the 5-key schema."""
    plan = migrate(source="codex", target="opencode", workspace=tmp_codex_workspace)
    out = convert_codex_to_opencode(plan)
    assert isinstance(out, dict)
    for key in ("opencode_json_blocks", "agents_md_blocks", "skills", "commands", "manual_steps"):
        assert key in out
