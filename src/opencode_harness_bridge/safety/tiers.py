"""Safety tier classification and secret detection.

Implementation note (for other-PC worker)
----------------------------------------
The 4-tier model is the heart of this tool. v0.2.0 needs to wire up
:class:`safety.tiers.classify_asset` to actually assign tiers based on
the asset kind and content. The current 0.1.0 stub uses a simple
key lookup so tests can verify the model.

For secret detection (:mod:`safety.secrets`), the strategy is **defense
in depth**:
1. Regex-based pattern matching (fast, false-positive prone)
2. File-path heuristics (``*.env``, ``*secret*``, ``*token*``)
3. (v0.2.0+) Optional: secret-scanning library (e.g. ``detect-secrets``)

The default is to *flag, never silently pass through* — any uncertain
match escalates to ``user-owned-secret-step``.
"""
from __future__ import annotations

from opencode_harness_bridge.models import SafetyTier

__all__ = ["classify_asset", "looks_like_secret", "DEFAULT_TIER_MAP"]


# A simple static map for v0.1.0 tests. v0.2.0 will make this dynamic
# (inspecting the asset path + content + source format).
DEFAULT_TIER_MAP: dict[str, SafetyTier] = {
    # Claude Code kinds
    "claude-code:instruction": SafetyTier.AUTO_APPLY,
    "claude-code:agent": SafetyTier.AUTO_APPLY,
    "claude-code:skill": SafetyTier.AUTO_APPLY,
    "claude-code:hook": SafetyTier.MODEL_ASSISTED,
    "claude-code:mcp_server": SafetyTier.MODEL_ASSISTED,
    "claude-code:memory": SafetyTier.MODEL_ASSISTED,
    "claude-code:rule": SafetyTier.MODEL_ASSISTED,
    "claude-code:secret": SafetyTier.USER_OWNED,
    # Codex kinds (v0.3.0+)
    "codex:instruction": SafetyTier.AUTO_APPLY,
    "codex:agent": SafetyTier.AUTO_APPLY,
    "codex:hook": SafetyTier.MODEL_ASSISTED,
    "codex:mcp_server": SafetyTier.MODEL_ASSISTED,
    "codex:memory": SafetyTier.MODEL_ASSISTED,
    "codex:secret": SafetyTier.USER_OWNED,
}


def classify_asset(source: str, kind: str) -> SafetyTier:
    """Classify a harness asset by source format and kind.

    Parameters
    ----------
    source : str
        Source harness format (``"claude-code"`` or ``"codex"``).
    kind : str
        Asset kind (``"instruction"``, ``"agent"``, ``"hook"``, ``"mcp_server"``,
        ``"memory"``, ``"rule"``, ``"secret"``, ...).

    Returns
    -------
    SafetyTier
        Assigned safety tier. Defaults to ``OPENCODE_INCOMPATIBLE`` for
        unknown combinations (fail-safe: don't auto-apply what we don't
        understand).
    """
    key = f"{source}:{kind}"
    return DEFAULT_TIER_MAP.get(key, SafetyTier.OPENCODE_INCOMPATIBLE)


# Common secret patterns — kept conservative (high precision, low recall).
# We prefer false negatives (let it through to user review) over false
# positives (block a legitimate asset). v0.2.0 may expand.
_SECRET_PATTERNS: tuple[str, ...] = (
    r"sk-[A-Za-z0-9]{20,}",                  # OpenAI
    r"sk-ant-[A-Za-z0-9\-]{20,}",            # Anthropic
    r"sk-or-[A-Za-z0-9\-]{20,}",             # OpenRouter
    r"ghp_[A-Za-z0-9]{30,}",                 # GitHub PAT
    r"github_pat_[A-Za-z0-9_]{50,}",         # GitHub fine-grained PAT
    r"xai-[A-Za-z0-9]{20,}",                 # xAI
    r"AKIA[0-9A-Z]{16}",                     # AWS access key
    r"AIza[0-9A-Za-z\-_]{35}",               # Google API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",   # PEM private keys
)


def looks_like_secret(text: str) -> bool:
    """Heuristic: does the given text contain something that looks like a secret?

    Returns
    -------
    bool
        True if any of the known secret patterns matches.

    Note
    ----
    This is a *defense in depth* check. The primary defense is never
    auto-applying ``user-owned-secret-step`` tier assets. This function
    is a backstop for tier-1 (auto-apply) assets that might accidentally
    contain a secret.
    """
    import re

    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, text):
            return True
    return False
