"""Real-CLI tests for cli.py (v0.2.0).

Subprocess-based smoke tests. Each test invokes the real CLI binary
and asserts on the actual output and side effects.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opencode_harness_bridge", "--version"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "opencode-harness-bridge 0.4.0" in result.stdout


def test_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opencode_harness_bridge", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "OpenCode" in result.stdout
    for cmd in ("inventory", "classify", "convert", "validate"):
        assert cmd in result.stdout


def test_cli_inventory_lists_claude_md(tmp_claude_workspace: Path) -> None:
    """v0.2.0: inventory actually discovers assets in a real (or temp) workspace."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opencode_harness_bridge",
            "inventory",
            "--source",
            "claude-code",
            "--workspace",
            str(tmp_claude_workspace),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "CLAUDE.md" in result.stdout
    assert "instruction" in result.stdout
    assert "auto-apply-after-confirmation" in result.stdout


def test_cli_classify_shows_tier_breakdown(tmp_claude_workspace: Path) -> None:
    """v0.2.0: classify prints a real tier breakdown (not the v0.1.0 stub)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opencode_harness_bridge",
            "classify",
            "--source",
            "claude-code",
            "--target",
            "opencode",
            "--workspace",
            str(tmp_claude_workspace),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Tier breakdown" in result.stdout
    assert "auto-apply-after-confirmation" in result.stdout
    assert "model-assisted-manual" in result.stdout
    assert "user-owned-secret-step" in result.stdout
    assert "opencode-incompatible" in result.stdout


def test_cli_convert_dry_run_no_files(tmp_claude_workspace: Path) -> None:
    """v0.2.0: convert --dry-run (default) prints a plan but writes no files."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opencode_harness_bridge",
            "convert",
            "--source",
            "claude-code",
            "--target",
            "opencode",
            "--workspace",
            str(tmp_claude_workspace),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "dry-run" in result.stdout
    assert "no files written" in result.stdout
    assert not (tmp_claude_workspace / ".opencode-out").exists()


def test_cli_validate_missing_target(tmp_path: Path) -> None:
    """v0.2.0: validate returns exit 2 when target directory does not exist."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opencode_harness_bridge",
            "validate",
            str(tmp_path / "nope"),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 2
    assert "does not exist" in result.stderr


def test_cli_maintain_missing_target(tmp_path: Path) -> None:
    """v0.4.0: `maintain` with non-existent --target-dir exits 2 with error to stderr."""
    result = subprocess.run(
        [
            sys.executable, "-m", "opencode_harness_bridge",
            "maintain",
            "--source", "claude-code",
            "--workspace", str(tmp_path),  # workspace path doesn't matter
            "--target-dir", str(tmp_path / "does-not-exist"),
        ],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 2, f"stderr: {result.stderr}"
    assert "does not exist" in result.stderr, f"stderr: {result.stderr}"
