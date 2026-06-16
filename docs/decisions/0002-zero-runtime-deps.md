# ADR 0002: Zero runtime dependencies (stdlib only)

## Status

Accepted — 2026-06-17 (v0.1.0)

## Context

`claude-codex-harness-sync` adds `pyyaml` and `tomli` for parsing
configuration files. While reasonable for a Codex-only tool, the same
dependencies feel heavy for an OpenCode adapter that:

1. Needs to ship in a 1MB wheel (sigco3111 OSS series convention)
2. Should install in <2s on a fresh machine
3. Should not conflict with the user's existing PyYAML or tomli versions
4. Should be audit-friendly (a one-file stdlib scan is easier than a
   dependency tree)

## Decision

Use **only Python 3.11+ stdlib** for runtime:

- `pathlib.Path` for filesystem walks
- `json` for JSON parsing
- `tomllib` (Python 3.11+) for TOML parsing
- `re` for secret detection
- `dataclasses` + `enum` for domain models
- `argparse` for CLI

No `pyyaml` (we parse frontmatter with a tiny custom splitter), no
`tomli` (stdlib), no `click`/`typer` (stdlib argparse is enough).

## Consequences

- Install in <1s, ~200KB wheel
- Zero supply-chain attack surface
- Slightly more code for frontmatter parsing (10 lines vs `yaml.safe_load`)
- Python 3.11+ is a hard requirement (acceptable in 2026)
- Markdown frontmatter without a parser is fine for our flat shapes

## Alternatives considered

- **`tomli-w` for writing TOML**: rejected — we don't write TOML in
  this adapter (OpenCode target is JSON, not TOML)
- **`pyyaml`**: rejected — adds a 700KB dep for 1 use site
- **`detect-secrets`**: rejected — too heavy for our pattern list;
  revisit in v0.4.0 if community asks for it
