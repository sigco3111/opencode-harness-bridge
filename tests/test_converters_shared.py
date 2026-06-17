"""Unit tests for converters/shared.py (v0.2.0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opencode_harness_bridge.converters.shared import (
    merge_opencode_json,
    parse_frontmatter,
    render_agents_md,
    toml_to_dict,
)
from opencode_harness_bridge.exceptions import MigrationError

# ---- parse_frontmatter ---------------------------------------------------


def test_parse_frontmatter_returns_dict_and_body() -> None:
    """With frontmatter, returns (dict, body) tuple."""
    text = "---\nkey: value\nother: another\n---\n# heading\n\nbody text\n"
    fm, body = parse_frontmatter(text)
    assert fm == {"key": "value", "other": "another"}
    assert body == "# heading\n\nbody text\n"


def test_parse_frontmatter_no_frontmatter_returns_empty_dict() -> None:
    """Without frontmatter, returns ({}, full_text)."""
    text = "# Just a heading\n\nNo frontmatter here.\n"
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_empty_value() -> None:
    """Empty value after colon is preserved as empty string."""
    text = "---\nname:\n---\nbody\n"
    fm, body = parse_frontmatter(text)
    assert fm == {"name": ""}
    assert body == "body\n"


# ---- toml_to_dict --------------------------------------------------------


def test_toml_to_dict_parses_valid(tmp_path: Path) -> None:
    """Valid TOML file → dict."""
    p = tmp_path / "config.toml"
    p.write_bytes(b'key = "value"\nnumber = 42\n')
    assert toml_to_dict(p) == {"key": "value", "number": 42}


def test_toml_to_dict_raises_migration_error_on_malformed(tmp_path: Path) -> None:
    """Malformed TOML → MigrationError (not raw tomllib.TOMLDecodeError)."""
    p = tmp_path / "bad.toml"
    p.write_bytes(b'key = "unterminated string\n')  # missing closing quote
    with pytest.raises(MigrationError, match="[Tt]oml|parse|invalid"):
        toml_to_dict(p)


# ---- merge_opencode_json -------------------------------------------------


def test_merge_opencode_json_deep_merges_nested_dicts() -> None:
    """Nested dicts are deep-merged (last-wins for primitives, deep-merge for dicts)."""
    base = {"a": {"b": 1, "c": 2}, "top": "x"}
    frag = {"a": {"c": 99, "d": 3}, "new": "y"}
    out = merge_opencode_json(base, frag)
    assert out == {"a": {"b": 1, "c": 99, "d": 3}, "top": "x", "new": "y"}


def test_merge_opencode_json_list_values_replaced_not_concatenated() -> None:
    """Lists are replaced, not concatenated (safer for config files)."""
    base = {"items": [1, 2, 3]}
    frag = {"items": [9]}
    out = merge_opencode_json(base, frag)
    assert out == {"items": [9]}


# ---- render_agents_md ----------------------------------------------------


def test_render_agents_md_concatenates_with_dividers() -> None:
    """Multiple blocks are joined with `\\n\\n---\\n\\n` between them."""
    blocks = ["# Block 1\n\nContent", "# Block 2\n\nMore", "# Block 3\n"]
    out = render_agents_md(blocks)
    assert out == "# Block 1\n\nContent\n\n---\n\n# Block 2\n\nMore\n\n---\n\n# Block 3\n"
