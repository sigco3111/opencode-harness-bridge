# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-17

### Added
- Initial project skeleton (Phase 0)
- 4-tier safety model: `auto-apply-after-confirmation`, `model-assisted-manual`, `user-owned-secret-step`, `opencode-incompatible` (new for OpenCode target)
- Domain models: `HarnessAsset`, `MigrationPlan`, `SafetyTier` (StrEnum)
- Exception hierarchy: `OpenCodeHarnessBridgeError`, `MigrationError`, `InvalidSourceError`, `InvalidTargetError`, `SecretLeakError`
- 5-subcommand CLI: `inventory`, `classify`, `convert`, `validate`, `--version`
- 6 sub-modules: `audit/{inventory,classify}`, `converters/{claude_code,codex,shared}`, `safety/tiers`
- Secret detection: 9 common patterns (OpenAI, Anthropic, GitHub, AWS, Google, PEM)
- 4-tier default classification map (24 entries)
- 18 unit + smoke tests across `test_models`, `test_safety_tiers`, `test_inventory`, `test_classify`, `test_claude_to_opencode`, `test_cli`
- GitHub Actions CI: Python 3.11/3.12/3.13 + ruff + mypy + pytest
- Korean/English bilingual README with decision-matrix, 5-phase plan, 4-step roadmap
- Zero runtime dependencies (stdlib only: `pathlib`, `json`, `tomllib`, `re`)

### Notes
- This is a Phase 0 release — skeleton + docs + design only.
- v0.2.0 will implement the Claude Code inventory scanner + converter in full.
- v0.3.0 will add the Codex → OpenCode path (sharing code with `opencode-trading`).
- v0.4.0 will add bidirectional `migrate maintain` (claude-codex-harness-sync parity).
- Adapted from `danyuchn/claude-codex-harness-sync` 3-tier model with one new tier for OpenCode incompatibilities.
