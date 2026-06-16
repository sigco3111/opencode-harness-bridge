"""Converters: source harness format → OpenCode.

Implementation note (for other-PC worker)
----------------------------------------
v0.1.0 stubs only. v0.2.0 implements claude_code_to_opencode in full:

1. Parse CLAUDE.md into a structured instruction set
2. Read .claude/agents/*.md → emit opencode.json `agent` objects
3. Read .claude/settings.json `mcpServers` → emit opencode.json `mcp` block
4. Read .claude/skills/*/SKILL.md → emit .opencode/skills/* and
   ~/.config/opencode/command/*.md
5. Translate .claude/hooks/ → opencode.json `hooks` (model-assisted tier)

For v0.3.0+, codex_to_opencode is a thinner mapping (Codex and OpenCode
are conceptually closer — both use AGENTS.md layering).

Trade-off: shared utilities
---------------------------
Common helpers (TOML/JSON parsing, Markdown frontmatter) live in
:mod:`converters.shared`. v0.2.0 will build that module first.
"""
from __future__ import annotations

from pathlib import Path

from opencode_harness_bridge.models import HarnessAsset, MigrationPlan

__all__ = ["convert_claude_code_to_opencode", "convert_codex_to_opencode"]


def convert_claude_code_to_opencode(plan: MigrationPlan) -> dict:
    """Convert a Claude Code MigrationPlan into OpenCode config fragments.

    v0.1.0 stub: returns an empty dict. v0.2.0 produces:

    >>> {
    ...     "opencode_json_blocks": {...},   # merge into ~/.config/opencode/opencode.json
    ...     "agents_md_blocks": [...],       # for AGENTS.md layering
    ...     "skills": [...],                 # for .opencode/skills/*
    ...     "commands": [...],               # for ~/.config/opencode/command/*
    ...     "manual_steps": [...],           # for model-assisted / user-owned items
    ... }
    """
    _ = plan
    return {}


def convert_codex_to_opencode(plan: MigrationPlan) -> dict:
    """Convert a Codex MigrationPlan into OpenCode config fragments.

    v0.1.0 stub. v0.3.0+ implements real conversion. Many maps with
    :func:`opencode_trading.convert_workspace` (sister project).
    """
    _ = plan
    return {}
