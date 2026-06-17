"""Shared utilities for converters.

This module is stdlib-only per ADR-0002 (zero runtime dependencies). It
provides four helpers used by both ``claude_code_to_opencode`` and
``codex_to_opencode``:

- :func:`parse_frontmatter` — extract a flat ``key: value`` frontmatter
  block from a Markdown document without pulling in PyYAML.
- :func:`toml_to_dict` — thin ``tomllib`` wrapper that converts
  :class:`tomllib.TOMLDecodeError` into :class:`MigrationError`.
- :func:`merge_opencode_json` — deep-merge a config fragment into an
  existing ``opencode.json`` (dicts merged, lists replaced).
- :func:`render_agents_md` — concatenate instruction blocks into a
  layered ``AGENTS.md`` with horizontal-rule separators.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from opencode_harness_bridge.exceptions import MigrationError

__all__ = [
    "parse_frontmatter",
    "toml_to_dict",
    "merge_opencode_json",
    "render_agents_md",
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a Markdown document into (frontmatter, body).

    The frontmatter must start on line 0 with ``---`` and be terminated
    by a line that is exactly ``---``. Values are returned as raw
    strings — we deliberately do not parse types (this is the trade-off
    adopted in ADR-0002 instead of pulling in PyYAML).
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        return {}, text

    end_index: int | None = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end_index = i
            break
    if end_index is None:
        return {}, text

    frontmatter: dict[str, str] = {}
    for raw in lines[1:end_index]:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        frontmatter[key.strip()] = value.strip()
    body = "".join(lines[end_index + 1 :])
    return frontmatter, body


def toml_to_dict(path: Path) -> dict[str, Any]:
    """Read a TOML file and return its contents as a dict.

    Malformed TOML is re-raised as :class:`MigrationError` so callers
    only need to handle the project exception hierarchy.
    """
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise MigrationError(f"Failed to parse TOML file {path}: {exc}") from exc


def merge_opencode_json(existing: dict[str, Any], fragment: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge ``fragment`` into ``existing`` and return the result.

    Dict values are merged recursively (last-wins on primitive keys).
    List values and other non-dict types are replaced wholesale — we
    never concatenate lists, which is the safer default for config
    files where the order and contents are authorial intent.

    Neither input is mutated.
    """
    result: dict[str, Any] = dict(existing)
    for key, value in fragment.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_opencode_json(result[key], value)
        else:
            result[key] = value
    return result


def render_agents_md(blocks: list[str]) -> str:
    """Concatenate ``blocks`` into a single ``AGENTS.md`` body.

    Blocks are joined with ``\\n\\n---\\n\\n`` so the resulting document
    reads as a layered stack of sections separated by horizontal rules.
    An empty input returns an empty string; a single block is returned
    unchanged.
    """
    if not blocks:
        return ""
    return "\n\n---\n\n".join(blocks)
