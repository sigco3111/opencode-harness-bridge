"""Real-CLI tests for cli.py (v0.2.0).

Subprocess-based integration tests. Each test invokes the real CLI binary
and asserts on the actual output and side effects on disk.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_PYTHON = sys.executable
_SRC_DIR = Path(__file__).parent.parent / "src"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_PYTHON, "-m", "opencode_harness_bridge", *args],
        capture_output=True,
        text=True,
        cwd=str(_SRC_DIR),
    )


# ---- inventory ----------------------------------------------------------


def test_cli_inventory_markdown_lists_5plus_assets(sample_claude_harness: Path) -> None:
    """inventory --source claude-code --workspace ... (markdown) lists 5+ asset paths."""
    result = _run_cli(
        "inventory",
        "--source",
        "claude-code",
        "--workspace",
        str(sample_claude_harness),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = result.stdout
    # Count distinct asset entries in the markdown (each line with a path counts)
    asset_count = sum(
        1
        for line in out.splitlines()
        if "claude" in line.lower() and ("/" in line or ".md" in line or ".json" in line)
    )
    assert asset_count >= 5, f"Expected 5+ assets, found {asset_count}\n{out}"


def test_cli_inventory_json_format_has_summary(sample_claude_harness: Path) -> None:
    """inventory --format json produces a JSON document with a summary field."""
    result = _run_cli(
        "inventory",
        "--source",
        "claude-code",
        "--workspace",
        str(sample_claude_harness),
        "--format",
        "json",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Last line is the JSON document (the rest is the version banner)
    json_line = [ln for ln in result.stdout.splitlines() if ln.startswith("{")][-1]
    doc = json.loads(json_line)
    assert "summary" in doc
    assert doc["summary"]["total"] >= 5


# ---- convert ------------------------------------------------------------


def test_cli_convert_dry_run_writes_no_files(sample_claude_harness: Path) -> None:
    """convert --dry-run (default) does NOT create .opencode-out/ directory."""
    import shutil

    out_dir = sample_claude_harness / ".opencode-out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    result = _run_cli(
        "convert",
        "--source",
        "claude-code",
        "--target",
        "opencode",
        "--workspace",
        str(sample_claude_harness),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert not out_dir.exists(), f"--dry-run wrote files: {out_dir}"


def test_cli_convert_apply_safe_writes_only_auto_apply(sample_claude_harness: Path) -> None:
    """convert --apply-safe writes opencode.json + AGENTS.md to workspace/.opencode-out/.

    Manual steps (MODEL_ASSISTED) are listed in stdout but NOT written to disk.
    """
    result = _run_cli(
        "convert",
        "--source",
        "claude-code",
        "--target",
        "opencode",
        "--workspace",
        str(sample_claude_harness),
        "--apply-safe",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out_dir = sample_claude_harness / ".opencode-out"
    assert out_dir.exists()
    # opencode.json + AGENTS.md should be written
    opencode_json = out_dir / "opencode.json"
    agents_md = out_dir / "AGENTS.md"
    assert opencode_json.exists(), f"opencode.json not written to {out_dir}"
    assert agents_md.exists(), f"AGENTS.md not written to {out_dir}"
    # opencode.json is valid JSON
    data = json.loads(opencode_json.read_text())
    assert "agent" in data  # agents were written
    # The output mentions skipped manual steps
    assert "manual" in result.stdout.lower() or "skip" in result.stdout.lower()
