---
name: harness-convert
description: Convert Claude Code or Codex harness assets to OpenCode using the 4-tier safety policy. Use when user asks to migrate, sync, or inspect a coding-agent harness.
license: MIT
compatibility: opencode>=1.0
metadata:
  author: sigco3111
  version: 1.0.0
---

# Harness Convert

When the user wants to move a Claude Code (`~/.claude/`, `CLAUDE.md`) or Codex
(`~/.codex/`, `AGENTS.md`) harness to OpenCode (`~/.config/opencode/`):

1. **Inventory** — `opencode-harness-bridge inventory --source {claude-code|codex}`
2. **Classify** — `opencode-harness-bridge classify --source <s> --target opencode`
3. **Convert (dry-run)** — `opencode-harness-bridge convert --source <s> --target opencode --dry-run`
4. **Convert (apply safe)** — `opencode-harness-bridge convert --source <s> --target opencode --apply-safe`
5. **Validate** — `opencode-harness-bridge validate ~/.config/opencode/`
6. **Maintain** — `opencode-harness-bridge maintain --source <s>` (report-only drift)

## 4-Tier Safety Policy

| Tier | Action |
|---|---|
| `auto-apply-after-confirmation` | Auto-apply with `--apply-safe` |
| `model-assisted-manual` | Stays in `manual_steps`; human + LLM reviews |
| `user-owned-secret-step` | Placeholder only; never literal |
| `opencode-incompatible` | Listed in `manual_steps`; manual mapping required |

## Invocation

```bash
# full pipeline
opencode-harness-bridge inventory --source claude-code
opencode-harness-bridge classify --source claude-code --target opencode
opencode-harness-bridge convert --source claude-code --target opencode --dry-run
opencode-harness-bridge convert --source claude-code --target opencode --apply-safe
opencode-harness-bridge validate ~/.config/opencode/
```

## When NOT to use

- The user is not on Claude Code or Codex (e.g. already on OpenCode) — no migration needed.
- The user only wants to inspect a single asset — use `inventory` directly, not the full pipeline.
- The user is editing the OpenCode config directly — use OpenCode's built-in tools, not the bridge.
