"""Smoke tests for the CLI (v0.1.0)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opencode_harness_bridge", "--version"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "opencode-harness-bridge 0.1.0" in result.stdout


def test_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "opencode_harness_bridge", "--help"],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "OpenCode" in result.stdout
    for cmd in ("inventory", "classify", "convert", "validate"):
        assert cmd in result.stdout


def test_cli_inventory_stub(tmp_claude_workspace: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "opencode_harness_bridge",
            "inventory",
            "--source", "claude-code",
            "--workspace", str(tmp_claude_workspace),
        ],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "v0.1.0 stub" in result.stdout


def test_cli_classify_stub(tmp_claude_workspace: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "opencode_harness_bridge",
            "classify",
            "--source", "claude-code",
            "--target", "opencode",
            "--workspace", str(tmp_claude_workspace),
        ],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "v0.1.0 stub" in result.stdout


def test_cli_convert_dry_run(tmp_claude_workspace: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "opencode_harness_bridge",
            "convert",
            "--source", "claude-code",
            "--target", "opencode",
            "--workspace", str(tmp_claude_workspace),
        ],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 0
    assert "dry-run" in result.stdout
    assert "v0.1.0 stub" in result.stdout


def test_cli_validate_missing_target(tmp_path: Path) -> None:
    """v0.1.0 stub still validates that the target exists."""
    result = subprocess.run(
        [
            sys.executable, "-m", "opencode_harness_bridge",
            "validate", str(tmp_path / "nope"),
        ],
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent / "src",
    )
    assert result.returncode == 2
    assert "does not exist" in result.stderr
