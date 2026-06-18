---
name: opencode-harness-bridge
description: Migrate Claude Code / Codex harness to OpenCode (inventory, classify, convert, validate, maintain).
license: MIT
command: opencode-harness-bridge
args:
  - name: subcommand
    description: One of inventory | classify | convert | validate | maintain
    required: true
  - name: options
    description: Forwarded as-is to the CLI (e.g. --source claude-code --target opencode)
    required: false
---

# opencode-harness-bridge

Migrate Claude Code (`.claude/`, `CLAUDE.md`) or Codex (`.codex/`, `AGENTS.md`)
harnesses to OpenCode (`~/.config/opencode/`) with a 4-tier safety policy.

## 5-step migration pipeline

1. **Inventory** — list discovered assets
   ```bash
   opencode-harness-bridge inventory --source claude-code
   ```
2. **Classify** — assign a SafetyTier to each asset
   ```bash
   opencode-harness-bridge classify --source claude-code --target opencode
   ```
3. **Convert** — produce a migration plan (dry-run) or apply safe changes
   ```bash
   opencode-harness-bridge convert --source claude-code --target opencode --dry-run
   opencode-harness-bridge convert --source claude-code --target opencode --apply-safe
   ```
4. **Validate** — verify a target OpenCode config directory
   ```bash
   opencode-harness-bridge validate ~/.config/opencode/
   ```
5. **Maintain** — report-only drift detection (no apply)
   ```bash
   opencode-harness-bridge maintain --source claude-code
   ```

## 4-tier safety policy

| Tier | Behavior |
|---|---|
| `auto-apply-after-confirmation` | Applied by `--apply-safe` |
| `model-assisted-manual` | Listed in `manual_steps`; human + LLM reviews |
| `user-owned-secret-step` | Placeholder only; never literal values |
| `opencode-incompatible` | Listed in `manual_steps`; manual mapping required |

See the `harness-convert` skill for the full workflow.
