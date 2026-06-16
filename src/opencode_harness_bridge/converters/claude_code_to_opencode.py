"""Claude Code → OpenCode converter (v0.1.0 stub)."""
from __future__ import annotations

from opencode_harness_bridge.models import MigrationPlan

__all__ = ["convert"]


def convert(plan: MigrationPlan) -> dict:
    """Convert a Claude Code MigrationPlan into OpenCode config fragments.

    v0.1.0 stub: returns an empty dict. v0.2.0 implements real conversion.
    See :mod:`converters` docstring for the planned output shape.
    """
    return {}


# Implementation note (for other-PC worker)
# -----------------------------------------
# v0.2.0 implementation order:
# 1. Extract CLAUDE.md / .claude/CLAUDE.md / CLAUDE.local.md content
#    → emit AGENTS.md body
# 2. Parse .claude/agents/*.md (frontmatter + body)
#    → emit opencode.json `agent` objects
# 3. Parse .claude/settings.json `mcpServers`
#    → emit opencode.json `mcp` block (NEVER inline secrets — use env vars)
# 4. Discover .claude/skills/*/SKILL.md
#    → emit ~/.config/opencode/command/*.md
# 5. Parse .claude/settings.json `hooks` (Claude format)
#    → translate to opencode.json `hooks` (mark as MODEL_ASSISTED tier)
# 6. ALWAYS scan for secrets in tier-1 assets before writing
