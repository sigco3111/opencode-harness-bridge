# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-18

### Added
- OpenCode marketplace plugin structure: `command/opencode-harness-bridge.md` (CLI slash command) + `skill/harness-convert/SKILL.md` (migration guidance) + `.github/plugin/marketplace.json` (discovery manifest)
- `.github/workflows/release.yml` — tag-driven build (sdist+wheel) + GitHub Release with attached artifacts
- `.pre-commit-config.yaml` — ruff check/format + standard hygiene hooks (trailing-whitespace, end-of-file-fixer, check-yaml/json/toml)
- `tests/test_release_readiness.py` — 8 invariants enforcing version sync, classifier, CI matrix, manifest schema across future bumps

### Changed
- `pyproject.toml`: version `0.4.0` → `1.0.0`; classifier `3 - Alpha` → `5 - Production/Stable`
- `__version__` in `src/opencode_harness_bridge/__init__.py` aligned to `1.0.0`
- `.github/workflows/ci.yml`: mypy is now blocking (removed `|| true` escape); Python 3.14 added to the test matrix
- Dev extras: added `build>=1.0` and `twine>=5` for sdist/wheel build + validation (no PyPI publish in v1.0.0)

### Notes
- Public API frozen at v1.0.0: `migrate`, `maintain`, `HarnessAsset`, `MigrationPlan`, `SafetyTier`, `MaintenanceItem`, `MaintenanceReport`. No symbol renames or removals.
- Zero runtime dependencies preserved (stdlib only: `pathlib`, `json`, `tomllib`, `re`, `dataclasses`, `enum`, `argparse`).
- 86 tests in v0.4.0 + 8 new readiness tests = 94 tests in v1.0.0.
- v1.0.0 is the first release to ship OpenCode marketplace artifacts and the first to have automated GitHub Release creation. The release workflow fires on `v*` tag push and attaches sdist + wheel to the GitHub Release.
- PyPI publishing is intentionally out of scope for v1.0.0; only GitHub Releases ship artifacts.

## [0.4.0] - 2026-06-18

### Added
- Report-only `migrate maintain` subcommand (v0.4.0) — bidirectional drift detection between source workspace and target OpenCode directory
- `sync.maintain()` function with two-tier diff strategy: surface set diff (agents/skills) + signature diff (per-block JSON canonicalization for `opencode.json`, exact-match for `AGENTS.md` and `skills/<name>.md`)
- `sync.MaintenanceItem` and `sync.MaintenanceReport` frozen dataclasses — full report shape (added / modified / removed / unchanged_count / manual_steps)
- `MaintenanceReport.to_dict()` for JSON serialization; `_render_maintain_markdown()` helper for human-readable output
- `maintain` CLI subcommand: `--source {claude-code|codex}`, `--workspace`, `--target-dir`, `--format {markdown|json}` (default markdown)
- `sync` module is report-only — NO file writes, NO backup, NO atomic write. User reviews the report and re-runs `convert --apply-safe` manually
- Mcp blocks are excluded from `added`/`modified`/`unchanged` counts (they are MODEL_ASSISTED tier); they surface via `manual_steps` and the missing-section detector
- 1 new test module: `tests/test_maintain.py` (8 tests) — covers added/unchanged/modified/removed/mixed/missing-file/manual-steps/InvalidTargetError
- 3 new CLI tests in `tests/test_cli.py` — maintain missing-target (exit 2), markdown format, JSON format
- Public API exports: `MaintenanceItem`, `MaintenanceReport`, `maintain` added to `opencode_harness_bridge.__init__`

### Changed
- `sync.py` refactored: extracted `_source_path_for`, `_expected_content_for`, `_read_target_state`, `_diff_agents`, `_diff_instruction`, `_diff_skills`, `_diff_missing_sections`, `_diff_removed`, `_build_manual_steps` helpers
- `cli.py` refactored: extracted `_render_maintain_markdown` from `_cmd_maintain`
- Test count: 75 → 86 (+11 new tests)

### Notes
- Content-only diff (sha256/JSON canonicalization) — ignores permissions, ownership, symlinks (Q1)
- Report-only — does NOT apply, does NOT backup, does NOT atomic-write (Q2)
- Adapted from `danyuchn/claude-codex-harness-sync` `migrate maintain` subcommand exactly
- All 7 new manual scenarios (S15-S21) verified PASS
- v0.4.0 retains zero runtime dependencies (stdlib only)

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
