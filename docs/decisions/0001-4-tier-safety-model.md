# ADR 0001: 4-tier safety model (vs upstream's 3-tier)

## Status

Accepted — 2026-06-17 (v0.1.0)

## Context

`danyuchn/claude-codex-harness-sync` (MIT) defines a 3-tier safety policy:

1. `auto-apply-after-confirmation` — low risk, apply after user confirms
2. `model-assisted-manual` — semantic translation needed
3. `user-owned-secret-step` — secrets handled by user only

The OpenCode target introduces a new class of item: **things that simply
cannot be auto-converted to OpenCode** (e.g. Claude Code's `mcp__*` tool
allowlists, which have no direct OpenCode equivalent and require manual
model + tools remapping in `opencode.json`).

Failing to distinguish these from "safe to auto-apply" would mean either
silently dropping them (data loss) or blindly copying them (broken
config). Both are unacceptable.

## Decision

Add a **4th tier**: `opencode-incompatible` for assets that need manual
work to migrate to OpenCode. Default for any unclassified asset kind is
also `opencode-incompatible` (fail-safe).

The 3 upstream tiers are kept as-is to maintain conceptual alignment
with `claude-codex-harness-sync`.

## Consequences

- Users see a clear 4-tier breakdown in `MigrationPlan.summary()`
- Default to the most conservative tier prevents silent data loss
- Future source formats (e.g. Aider, Continue) get their own tier
  classifications without colliding with the Claude/Codex split
- 9 secret patterns cover common providers (OpenAI, Anthropic, GitHub,
  AWS, Google, PEM keys) — false-negative preferred over false-positive

## Alternatives considered

- **3-tier only**: rejected — silent dropping of incompatible items
- **5+ tiers** (split MODEL_ASSISTED into semantic/config): rejected —
  unnecessary complexity for v0.1.0; revisit in v0.3.0+
- **Per-vendor tier customization**: rejected — adds config burden; a
  static map is enough for v0.1.0
