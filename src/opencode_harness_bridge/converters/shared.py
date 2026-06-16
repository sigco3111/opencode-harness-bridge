"""Shared utilities for converters.

Implementation note (for other-PC worker)
----------------------------------------
This module is a placeholder for v0.2.0. Helpers that will live here:

- :func:`parse_frontmatter` — extract YAML frontmatter from a Markdown file
- :func:`toml_to_dict` — stdlib ``tomllib`` wrapper with error handling
- :func:`merge_opencode_json` — deep-merge dict fragments into an existing
  ``opencode.json``
- :func:`render_agents_md` — render an instruction list into a layered
  AGENTS.md

The TOML parser must use stdlib ``tomllib`` (Python 3.11+). DO NOT add
``tomli`` or ``tomli-w`` as dependencies.

For Markdown frontmatter, the simplest approach is a tiny custom parser
(splits on ``---`` lines). The full PyYAML approach is overkill for our
flat frontmatter shapes and would add a dependency.
"""
from __future__ import annotations

# Intentionally empty in v0.1.0. Real helpers land in v0.2.0.
__all__: list[str] = []
