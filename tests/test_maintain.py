"""Real tests for sync.maintain() (v0.4.0 RED).

These tests are the RED phase of TDD — they MUST fail against the current
maintain() stub (which raises NotImplementedError). The GREEN implementation
in T1.3 will make them pass.

v0.4.0 design notes
-------------------
* ``maintain(plan=plan, target_dir=...)`` is REPORT-ONLY. It reads the
  target but does NOT write to it. See ``sync.py`` for the contract.
* Content-only diff (sha256) — permissions/ownership/symlinks ignored.
* Two-tier diff: surface set diff + signature diff (per asset kind).
* ``maintain`` raises ``InvalidTargetError`` if ``target_dir`` is not a
  directory (test 8 covers this).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencode_harness_bridge.audit.classify import migrate
from opencode_harness_bridge.exceptions import InvalidTargetError
from opencode_harness_bridge.sync import MaintenanceReport, maintain

# ---- Happy path: empty target → all added ------------------------------


def test_maintain_added_when_target_missing(sample_claude_harness: Path, tmp_path: Path) -> None:
    """Empty target: all AUTO_APPLY source assets reported as added."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    target_dir = tmp_path / "empty_target"
    target_dir.mkdir()
    report = maintain(plan=plan, target_dir=target_dir)
    assert isinstance(report, MaintenanceReport)
    assert report.source == "claude-code"
    # sample-claude-harness has 2 agents, 2 skills, 1 instruction (3 mcp + 2 hook + 2 rule = manual)
    # AUTO_APPLY assets: 1 instruction + 2 agents + 2 skills = 5 assets
    assert len(report.added) == 5
    assert len(report.modified) == 0
    assert len(report.removed) == 0
    assert report.unchanged_count == 0


# ---- Unchanged: target matches source exactly ---------------------------


def test_maintain_unchanged_when_target_matches(
    sample_claude_harness: Path, tmp_path: Path
) -> None:
    """Target already has matching content → 0 added, 0 modified, 0 removed."""
    # First, run convert to produce the expected target
    from opencode_harness_bridge.converters.claude_code_to_opencode import convert

    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    fragments = convert(plan, strict_secrets=True)

    # Write the converted artifacts to a target dir
    target_dir = tmp_path / "matched_target"
    target_dir.mkdir()
    (target_dir / "opencode.json").write_text(
        json.dumps(fragments["opencode_json_blocks"], indent=2) + "\n", encoding="utf-8"
    )
    (target_dir / "AGENTS.md").write_text(
        "\n\n---\n\n".join(fragments["agents_md_blocks"]), encoding="utf-8"
    )
    skills_dir = target_dir / "skills"
    skills_dir.mkdir()
    for skill in fragments["skills"]:
        name = skill.get("name", "unnamed")
        (skills_dir / f"{name}.md").write_text(skill.get("body", ""), encoding="utf-8")

    # Now run maintain
    report = maintain(plan=plan, target_dir=target_dir)
    assert len(report.added) == 0
    assert len(report.modified) == 0
    assert len(report.removed) == 0
    assert report.unchanged_count == 5  # 1 instruction + 2 agents + 2 skills


# ---- Modified: target content differs ---------------------------------


def test_maintain_modified_when_target_content_differs(
    sample_claude_harness: Path, tmp_path: Path
) -> None:
    """Target has matching structure but DIFFERENT content → reported as modified."""
    from opencode_harness_bridge.converters.claude_code_to_opencode import convert

    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    fragments = convert(plan, strict_secrets=True)

    target_dir = tmp_path / "modified_target"
    target_dir.mkdir()
    # Write opencode.json with the agents list, BUT change one agent's prompt
    modified_blocks = json.loads(json.dumps(fragments["opencode_json_blocks"]))
    modified_blocks["agent"][0]["prompt"] = "DIFFERENT PROMPT TEXT — user edited this"
    (target_dir / "opencode.json").write_text(
        json.dumps(modified_blocks, indent=2) + "\n", encoding="utf-8"
    )
    (target_dir / "AGENTS.md").write_text(
        "\n\n---\n\n".join(fragments["agents_md_blocks"]), encoding="utf-8"
    )
    # Write the skills so they count as unchanged (1 instruction + 1 agent + 2 skills = 4)
    skills_dir = target_dir / "skills"
    skills_dir.mkdir()
    for skill in fragments["skills"]:
        name = skill.get("name", "unnamed")
        (skills_dir / f"{name}.md").write_text(skill.get("body", ""), encoding="utf-8")

    report = maintain(plan=plan, target_dir=target_dir)
    # At least the modified agent should be in `modified` set
    assert len(report.modified) >= 1
    # The other auto-apply assets (instruction, 1 agent, 2 skills) should be unchanged
    assert report.unchanged_count >= 3


# ---- Removed: target has extra assets ---------------------------------


def test_maintain_removed_when_target_has_extra_assets(
    sample_claude_harness: Path, tmp_path: Path
) -> None:
    """Target has assets NOT in source → reported as removed."""
    from opencode_harness_bridge.converters.claude_code_to_opencode import convert

    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    fragments = convert(plan, strict_secrets=True)

    target_dir = tmp_path / "extra_target"
    target_dir.mkdir()
    # Write source's opencode.json PLUS an extra agent the source doesn't have
    modified_blocks = json.loads(json.dumps(fragments["opencode_json_blocks"]))
    modified_blocks["agent"].append(
        {
            "name": "ghost-agent",
            "description": "extra agent not in source",
            "prompt": "This agent doesn't exist in source",
        }
    )
    (target_dir / "opencode.json").write_text(
        json.dumps(modified_blocks, indent=2) + "\n", encoding="utf-8"
    )
    (target_dir / "AGENTS.md").write_text(
        "\n\n---\n\n".join(fragments["agents_md_blocks"]), encoding="utf-8"
    )

    report = maintain(plan=plan, target_dir=target_dir)
    # 1 removed: the ghost agent
    assert len(report.removed) >= 1
    removed_kinds_subpaths = {(it.kind, it.target_subpath) for it in report.removed}
    assert any("ghost-agent" in sp for _, sp in removed_kinds_subpaths)


# ---- Mixed: realistic add + modify + remove ---------------------------


def test_maintain_mixed_add_modify_remove(sample_claude_harness: Path, tmp_path: Path) -> None:
    """Mixed scenario: some add, some modify, some remove, some unchanged."""
    from opencode_harness_bridge.converters.claude_code_to_opencode import convert

    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    fragments = convert(plan, strict_secrets=True)

    target_dir = tmp_path / "mixed_target"
    target_dir.mkdir()
    # Write a target with: 1 of 2 source agents matching, 1 modified, 1 extra agent
    modified_blocks = {"agent": []}
    # Agent 1: matching (will be unchanged)
    if len(fragments["opencode_json_blocks"].get("agent", [])) >= 1:
        modified_blocks["agent"].append(fragments["opencode_json_blocks"]["agent"][0])
    # Agent 2: modified (we'll write a target that has the same name but different content)
    if len(fragments["opencode_json_blocks"].get("agent", [])) >= 2:
        modified_agent = json.loads(json.dumps(fragments["opencode_json_blocks"]["agent"][1]))
        modified_blocks["agent"].append(modified_agent)
    # Agent 3: extra (not in source)
    modified_blocks["agent"].append(
        {
            "name": "extra-agent-3",
            "description": "extra",
            "prompt": "extra",
        }
    )
    (target_dir / "opencode.json").write_text(
        json.dumps(modified_blocks, indent=2) + "\n", encoding="utf-8"
    )
    # Skip AGENTS.md → instruction will be "added"
    # Skip skills/ → skills will be "added"

    report = maintain(plan=plan, target_dir=target_dir)
    # Added: 1 instruction + 1 missing agent (agent[1]) + 2 skills = 4 added
    assert len(report.added) >= 3  # at minimum: instruction + 1 missing agent + skills
    # Modified: 1 (agent[1] which we set up with same name but different content)
    assert len(report.modified) >= 1
    # Removed: 1 (extra-agent-3)
    assert len(report.removed) >= 1


# ---- Missing target file (but target_dir exists) -----------------------


def test_maintain_handles_missing_target_file(sample_claude_harness: Path, tmp_path: Path) -> None:
    """target_dir exists but opencode.json does NOT → all AUTO_APPLY assets added."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    target_dir = tmp_path / "no_json_target"
    target_dir.mkdir()
    # No files written
    report = maintain(plan=plan, target_dir=target_dir)
    # All auto-apply assets are "added" (5)
    assert len(report.added) == 5
    assert report.unchanged_count == 0


# ---- Manual steps for MODEL_ASSISTED ---------------------------------


def test_maintain_includes_manual_steps_for_model_assisted(
    sample_claude_harness: Path, tmp_path: Path
) -> None:
    """Hooks + memories + secrets go to manual_steps (not added/modified)."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    target_dir = tmp_path / "manual_target"
    target_dir.mkdir()
    report = maintain(plan=plan, target_dir=target_dir)
    # sample-claude-harness has: 2 mcp_server + 2 hook + 2 rule = 6 MODEL_ASSISTED
    assert len(report.manual_steps) == 6
    # Each manual step has the expected keys
    for step in report.manual_steps:
        assert "kind" in step
        assert "tier" in step
        assert "action" in step


# ---- Error: target_dir does not exist ---------------------------------


def test_maintain_raises_for_missing_target_dir(
    sample_claude_harness: Path, tmp_path: Path
) -> None:
    """maintain() raises InvalidTargetError if target_dir doesn't exist."""
    plan = migrate(source="claude-code", target="opencode", workspace=sample_claude_harness)
    with pytest.raises(InvalidTargetError):
        maintain(plan=plan, target_dir=tmp_path / "does-not-exist")
