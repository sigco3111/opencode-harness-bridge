"""Codex → OpenCode converter (v0.1.0 stub)."""

from __future__ import annotations

from opencode_harness_bridge.models import MigrationPlan

__all__ = ["convert"]


def convert(plan: MigrationPlan) -> dict:
    """Convert a Codex MigrationPlan into OpenCode config fragments.

    v0.1.0 stub: returns an empty dict. v0.3.0+ implements real conversion.
    Shares much of the logic with :mod:`opencode_trading` (sister project).
    """
    return {}


# Implementation note (for other-PC worker)
# -----------------------------------------
# v0.3.0+ should reuse code from sigco3111/opencode-trading:
#   - TOML → JSON agent mapping (TradingCodex uses .codex/agents/*.toml)
#   - hooks AST parsing (Codex hooks are Python files)
#   - MCP stdio registration
#
# Strategy: depend on opencode-trading as optional extra, or copy + adapt
# the converters. Keep zero-deps for now; revisit in v0.3.0 design.
