"""Smoke tests for the 4-tier safety model and secret detection."""
from __future__ import annotations

from opencode_harness_bridge.safety.tiers import (
    DEFAULT_TIER_MAP,
    classify_asset,
    looks_like_secret,
)


def test_classify_claude_code_instruction_is_auto_apply() -> None:
    assert classify_asset("claude-code", "instruction") == "auto-apply-after-confirmation"


def test_classify_claude_code_hook_is_model_assisted() -> None:
    assert classify_asset("claude-code", "hook") == "model-assisted-manual"


def test_classify_claude_code_secret_is_user_owned() -> None:
    assert classify_asset("claude-code", "secret") == "user-owned-secret-step"


def test_classify_unknown_combination_defaults_to_opencode_incompatible() -> None:
    """Fail-safe: unknown asset kinds default to the most conservative tier."""
    tier = classify_asset("claude-code", "totally_made_up_kind")
    assert tier == "opencode-incompatible"


def test_classify_codex_paths_in_map() -> None:
    """v0.3.0+ Codex paths are pre-classified (for the day v0.3.0 ships)."""
    assert "codex:instruction" in DEFAULT_TIER_MAP
    assert "codex:agent" in DEFAULT_TIER_MAP


def test_looks_like_secret_detects_openai_key() -> None:
    text = "My key is sk-abcdefghijklmnopqrstuvwxyz"
    assert looks_like_secret(text) is True


def test_looks_like_secret_detects_anthropic_key() -> None:
    text = "key: sk-ant-abcdefghijklmnopqrstuvwx"
    assert looks_like_secret(text) is True


def test_looks_like_secret_detects_github_pat() -> None:
    text = "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123"
    assert looks_like_secret(text) is True


def test_looks_like_secret_detects_pem_private_key() -> None:
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK..."
    assert looks_like_secret(text) is True


def test_looks_like_secret_returns_false_for_plain_text() -> None:
    text = "Use pytest. Always type-hint. Never commit secrets to git."
    assert looks_like_secret(text) is False


def test_looks_like_secret_returns_false_for_short_strings() -> None:
    """Short strings that look nothing like secrets."""
    text = "Hello world"
    assert looks_like_secret(text) is False
