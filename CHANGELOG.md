# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-17

## [0.2.0] - 2026-06-17

## [0.3.0] - 2026-06-17

### Added
- Real Codex inventory scanner (`audit/inventory.py:scan_codex`) — discovers 5 asset kinds: instruction (AGENTS.md), agent (.codex/agents/*.toml), mcp_server (.codex/config.toml), hook (.codex/hooks/*.py), memory (.codex/memories/*)
- Real Codex → OpenCode converter (`converters/codex_to_opencode.py:convert`) — produces the 5-key schema mirroring the Claude converter
- `convert_codex_to_opencode()` dispatcher wired in `converters/__init__.py` (parity with Claude)
- Codex mcp_server env-var placeholders (`${KEY}`) — NEVER inline literal values, same safety as Claude path
- Codex hooks (Python files) → `manual_steps` with action "wrap Python hook as shell-callable for OpenCode"
- Codex memories → `manual_steps` with action "v0.4.0+ will add wiki/ mapping for Codex memories"
- 2 new checked-in Codex fixtures: `sample-codex-harness-with-secret/` (S12), `sample-codex-harness-malformed-toml/` (S14)
- 4 new test modules: `test_inventory_codex.py` (8 tests), `test_codex_to_opencode_real.py` (8 tests), updated `test_inventory_classify.py` and `test_converters.py`
- 3 new conftest fixtures: `sample_codex_harness`, `sample_codex_harness_with_secret`, `sample_codex_harness_malformed_toml`

### Changed
- `tmp_codex_workspace` fixture now includes a sample hook file (`.codex/hooks/pre-tool-use.py`) so hook discovery tests have something to find
- Test count: 59 → 75 (+16 new tests, 2 existing rewritten for real behavior)

### Notes
- All 7 new manual scenarios (S8-S14) verified PASS
- v0.3.0 retains zero runtime dependencies (stdlib only: pathlib, json, tomllib, re, dataclasses, enum, argparse)
- Codex hooks remain model-assisted tier (Python files cannot be auto-converted to OpenCode's shell-callable format in v0.3.0)
- Memories → `manual_steps` only; the wiki/ mapping is planned for v0.4.0

### Added
- Real Claude Code inventory scanner (`audit/inventory.py`)
- Real Claude Code → OpenCode converter (`converters/claude_code_to_opencode.py`)
- Shared converter helpers: parse_frontmatter, toml_to_dict, merge_opencode_json, render_agents_md (`converters/shared.py`)
- Real CLI handlers: `inventory` / `classify` / `convert` (with `--dry-run` and `--apply-safe`) / `validate` (`cli.py`)
- `--apply-safe` writes OpenCode artifacts to `workspace/.opencode-out/` (preserves source workspace)
- Converter `strict_secrets=True` default — raises `SecretLeakError` on secret in `AUTO_APPLY` asset
- 3 new test modules: `test_converters_shared.py`, `test_inventory_real.py`, `test_claude_to_opencode_real.py`, `test_cli_real.py`
- 3 checked-in Claude harness fixtures under `tests/fixtures/`
- 1 checked-in Codex placeholder fixture (v0.3.0+ target)

### Changed
- `tests/test_inventory_classify.py`, `tests/test_converters.py`, `tests/test_cli.py`: dropped "v0.1.0 stub" assertions, now assert real behavior
- `src/opencode_harness_bridge/__main__.py`: add `sys.exit(main())` so non-zero exit codes propagate
- `.gitignore`: add `.opencode-out/` to prevent committing test artifacts
- Test count: 31 → 59 (+28 new tests, 6 existing rewritten)
- All 7 manual scenarios (S1-S7) verified PASS

### Notes
- Strict-mode secret detection is the default. `--allow-secret-escalation` flag is reserved for a future minor release.
- `--apply-safe` refuses to touch `MODEL_ASSISTED` / `USER_OWNED` / `OPENCODE_INCOMPATIBLE` assets — those are listed as `manual_steps` only.

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
