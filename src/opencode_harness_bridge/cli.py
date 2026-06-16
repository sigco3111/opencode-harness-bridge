"""Command-line interface for opencode-harness-bridge.

Implementation note (for other-PC worker)
----------------------------------------
5 subcommands follow the claude-codex-harness-sync 3-phase structure
(inventory → classify → convert) plus validate and a global --version:

1. ``inventory``   — scan the source harness, list discovered assets
2. ``classify``    — assign a SafetyTier to each asset
3. ``convert``     — produce a migration plan (dry-run) or apply safe changes
4. ``validate``    — verify a target OpenCode config directory
5. ``--version``   — print version and exit

Argparse pitfall (from python-oss-bootstrap kakao-summary lesson)
----------------------------------------------------------------
``argparse`` positional args with ``nargs="?"`` collide with subparsers when
the positional value contains spaces or special chars. The safe pattern:
pass ``--workspace`` and ``--source``/``--target`` as required options, not
positionals. We do this throughout.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from opencode_harness_bridge import __version__


def main(argv: list[str] | None = None) -> int:
    """CLI entry point registered as the ``opencode-harness-bridge`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"opencode-harness-bridge {__version__}")
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    handler = _HANDLERS.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
        return 2  # unreachable
    return handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode-harness-bridge",
        description="Safely migrate Claude Code/Codex harnesses to OpenCode "
        "with a 4-tier safety policy.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # inventory
    inv = sub.add_parser("inventory", help="scan a source harness and list discovered assets")
    inv.add_argument("--source", required=True, choices=["claude-code", "codex"],
                     help="source harness format")
    inv.add_argument("--workspace", type=Path, default=Path.cwd(),
                     help="project workspace root (default: cwd)")
    inv.add_argument("--format", choices=["markdown", "json"], default="markdown",
                     help="output format (default: markdown)")
    inv.set_defaults(handler=_cmd_inventory)

    # classify
    cls = sub.add_parser("classify", help="classify discovered assets by SafetyTier")
    cls.add_argument("--source", required=True, choices=["claude-code", "codex"])
    cls.add_argument("--target", required=True, choices=["opencode"])
    cls.add_argument("--workspace", type=Path, default=Path.cwd())
    cls.add_argument("--format", choices=["markdown", "json"], default="markdown")
    cls.set_defaults(handler=_cmd_classify)

    # convert
    cvt = sub.add_parser("convert", help="produce a migration plan or apply safe changes")
    cvt.add_argument("--source", required=True, choices=["claude-code", "codex"])
    cvt.add_argument("--target", required=True, choices=["opencode"])
    cvt.add_argument("--workspace", type=Path, default=Path.cwd())
    cvt.add_argument("--dry-run", action="store_true",
                     help="print plan without touching files (default)")
    cvt.add_argument("--apply-safe", action="store_true",
                     help="apply tier-1 (auto-apply-after-confirmation) changes")
    cvt.set_defaults(handler=_cmd_convert)

    # validate
    val = sub.add_parser("validate", help="verify an OpenCode config directory")
    val.add_argument("target_dir", type=Path, nargs="?", default=Path("~/.config/opencode"),
                     help="OpenCode config directory (default: ~/.config/opencode)")
    val.set_defaults(handler=_cmd_validate)

    return parser


# ---- subcommand handlers (all stubs in v0.1.0) -----------------------------


def _cmd_inventory(args: argparse.Namespace) -> int:
    """Stub: scan the source harness. v0.2.0 implements real scanning."""
    print(f"opencode-harness-bridge {__version__} — inventory")
    print(f"  source:    {args.source}")
    print(f"  workspace: {args.workspace}")
    print(f"  format:    {args.format}")
    print()
    print("v0.1.0 stub: no assets discovered yet.")
    print("Implementation plan: see README.md '다른 PC에서 작업' section.")
    return 0


def _cmd_classify(args: argparse.Namespace) -> int:
    """Stub: classify assets. v0.2.0 wires inventory + safety tiers."""
    print(f"opencode-harness-bridge {__version__} — classify")
    print(f"  source:    {args.source}")
    print(f"  target:    {args.target}")
    print(f"  workspace: {args.workspace}")
    print()
    print("v0.1.0 stub: no classification performed yet.")
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    """Stub: produce a plan (or apply safe changes)."""
    print(f"opencode-harness-bridge {__version__} — convert")
    print(f"  source:      {args.source}")
    print(f"  target:      {args.target}")
    print(f"  workspace:   {args.workspace}")
    print(f"  mode:        {'apply-safe' if args.apply_safe else 'dry-run'}")
    print()
    print("v0.1.0 stub: no conversion performed yet.")
    if not args.apply_safe:
        print("  (default: dry-run. Use --apply-safe to apply tier-1 changes in v0.2.0+)")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Stub: validate an OpenCode config dir."""
    target: Path = args.target_dir.expanduser()
    if not target.exists():
        print(f"error: target directory does not exist: {target}", file=sys.stderr)
        sys.exit(2)
    print(f"opencode-harness-bridge {__version__} — validate")
    print(f"  target: {target}")
    print()
    print("v0.1.0 stub: no validation performed yet.")
    return 0


_HANDLERS: dict[str, object] = {
    "inventory": _cmd_inventory,
    "classify": _cmd_classify,
    "convert": _cmd_convert,
    "validate": _cmd_validate,
}


if __name__ == "__main__":
    sys.exit(main())
