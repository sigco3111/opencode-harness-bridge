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
from collections.abc import Callable
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
    inv.add_argument(
        "--source", required=True, choices=["claude-code", "codex"], help="source harness format"
    )
    inv.add_argument(
        "--workspace", type=Path, default=Path.cwd(), help="project workspace root (default: cwd)"
    )
    inv.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="output format (default: markdown)",
    )
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
    cvt.add_argument(
        "--dry-run", action="store_true", help="print plan without touching files (default)"
    )
    cvt.add_argument(
        "--apply-safe",
        action="store_true",
        help="apply tier-1 (auto-apply-after-confirmation) changes",
    )
    cvt.set_defaults(handler=_cmd_convert)

    # validate
    val = sub.add_parser("validate", help="verify an OpenCode config directory")
    val.add_argument(
        "target_dir",
        type=Path,
        nargs="?",
        default=Path("~/.config/opencode"),
        help="OpenCode config directory (default: ~/.config/opencode)",
    )
    val.set_defaults(handler=_cmd_validate)

    # maintain
    mtn = sub.add_parser(
        "maintain",
        help=(
            "report-only drift detection between source workspace and "
            "target OpenCode directory (no apply)"
        ),
    )
    mtn.add_argument("--source", required=True, choices=["claude-code", "codex"],
                     help="source harness format")
    mtn.add_argument("--workspace", required=True, type=Path,
                     help="source workspace to scan")
    mtn.add_argument("--target-dir", required=True, type=Path,
                     help="target OpenCode directory to compare against (e.g., ~/.config/opencode)")
    mtn.add_argument("--format", choices=["markdown", "json"], default="markdown",
                     help="output format (default: markdown)")
    mtn.set_defaults(handler=_cmd_maintain)

    return parser


# ---- subcommand handlers (real implementations, v0.2.0) -----------------


def _render_inventory_markdown(plan) -> str:
    lines = [
        f"# Inventory: {plan.source} → {plan.target}",
        f"Workspace: {plan.workspace}",
        f"Total: {plan.summary()['total']} assets",
        "",
        "| Path | Kind | Tier |",
        "|------|------|------|",
    ]
    for a in plan.assets:
        lines.append(f"| {a.path} | {a.kind} | {a.tier.value} |")
    return "\n".join(lines) + "\n"


def _cmd_inventory(args: argparse.Namespace) -> int:
    """Scan the source harness and list discovered assets."""
    from opencode_harness_bridge.audit.classify import migrate
    from opencode_harness_bridge.audit.inventory import scan

    print(f"opencode-harness-bridge {__version__} — inventory")
    if args.format == "json":
        import json as _json

        ws = Path(args.workspace).expanduser().resolve()
        assets = scan(args.source, ws)
        plan = migrate(source=args.source, target="opencode", workspace=ws)
        import dataclasses

        plan = dataclasses.replace(plan, assets=assets)
        print(_json.dumps(plan.to_dict()))
    else:
        plan = migrate(
            source=args.source,
            target="opencode",
            workspace=Path(args.workspace).expanduser().resolve(),
        )
        print(_render_inventory_markdown(plan))
    return 0


def _cmd_classify(args: argparse.Namespace) -> int:
    """Classify discovered assets by SafetyTier."""
    from opencode_harness_bridge.audit.classify import migrate

    plan = migrate(
        source=args.source,
        target=args.target,
        workspace=Path(args.workspace).expanduser().resolve(),
    )
    print(f"opencode-harness-bridge {__version__} — classify")
    print(f"  source:    {plan.source}")
    print(f"  target:    {plan.target}")
    print(f"  workspace: {plan.workspace}")
    print()
    if args.format == "json":
        import json as _json

        print(_json.dumps(plan.to_dict(), indent=2))
    else:
        s = plan.summary()
        print("Tier breakdown:")
        for tier, count in s.items():
            if tier == "total":
                continue
            print(f"  {tier}: {count}")
        print(f"  total: {s['total']}")
    return 0


def _write_opencode_json(out_dir: Path, plan, fragments) -> None:
    """Deep-merge the opencode_json_blocks into out_dir/opencode.json."""
    import json as _json

    target = out_dir / "opencode.json"
    existing: dict = {}
    if target.exists():
        try:
            existing = _json.loads(target.read_text(encoding="utf-8"))
        except _json.JSONDecodeError:
            existing = {}
    from opencode_harness_bridge.converters.shared import merge_opencode_json

    merged = merge_opencode_json(existing, fragments.get("opencode_json_blocks", {}))
    target.write_text(_json.dumps(merged, indent=2) + "\n", encoding="utf-8")


def _write_agents_md(out_dir: Path, fragments) -> None:
    """Render and write the agents_md_blocks to out_dir/AGENTS.md."""
    from opencode_harness_bridge.converters.shared import render_agents_md

    blocks = fragments.get("agents_md_blocks", [])
    body = render_agents_md(blocks)
    (out_dir / "AGENTS.md").write_text(body, encoding="utf-8")


def _write_skills(out_dir: Path, fragments) -> None:
    """Write each skill to out_dir/skills/<name>.md."""
    skills = fragments.get("skills", [])
    if not skills:
        return
    skills_dir = out_dir / "skills"
    skills_dir.mkdir(exist_ok=True)
    for skill in skills:
        name = skill.get("name", "unnamed")
        body = skill.get("body", "")
        (skills_dir / f"{name}.md").write_text(body, encoding="utf-8")


def _cmd_convert(args: argparse.Namespace) -> int:
    """Produce a migration plan (dry-run default) or apply safe changes."""
    from opencode_harness_bridge.audit.classify import migrate

    plan = migrate(
        source=args.source,
        target=args.target,
        workspace=Path(args.workspace).expanduser().resolve(),
    )
    print(f"opencode-harness-bridge {__version__} — convert")
    print(f"  source:    {plan.source}")
    print(f"  target:    {plan.target}")
    print(f"  workspace: {plan.workspace}")
    print(f"  mode:      {'apply-safe' if args.apply_safe else 'dry-run'}")
    print()
    if plan.source == "claude-code":
        from opencode_harness_bridge.converters.claude_code_to_opencode import (
            convert as cc_convert,
        )

        fragments = cc_convert(plan, strict_secrets=True)
    elif plan.source == "codex":
        from opencode_harness_bridge.converters import convert_codex_to_opencode

        fragments = convert_codex_to_opencode(plan, strict_secrets=True)
    else:
        print(f"error: unsupported source: {plan.source!r}", file=sys.stderr)
        return 2
    manual = fragments.get("manual_steps", [])
    auto = sum(1 for a in plan.assets if a.tier.value == "auto-apply-after-confirmation")
    print(f"Assets: {len(plan.assets)} total, {auto} auto-apply, {len(manual)} manual")

    if not args.apply_safe:
        print()
        print("Plan (dry-run, no files written):")
        n_ojb = len(fragments.get("opencode_json_blocks", {}))
        n_amb = len(fragments.get("agents_md_blocks", []))
        n_sk = len(fragments.get("skills", []))
        print(f"  opencode_json_blocks: {n_ojb} top-level keys")
        print(f"  agents_md_blocks:     {n_amb} blocks")
        print(f"  skills:               {n_sk} skills")
        print(f"  manual_steps:         {len(manual)} steps")
        for step in manual:
            print(f"    - SKIP [{step.get('tier')}] {step.get('kind')}: {step.get('description')}")
        return 0

    out_dir = plan.workspace / ".opencode-out"
    out_dir.mkdir(exist_ok=True)
    _write_opencode_json(out_dir, plan, fragments)
    _write_agents_md(out_dir, fragments)
    _write_skills(out_dir, fragments)
    print(f"Wrote: {out_dir}/opencode.json, AGENTS.md, skills/")
    if manual:
        print()
        print("Manual steps (not written to disk):")
        for step in manual:
            print(f"  - [{step.get('tier')}] {step.get('kind')}: {step.get('description')}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Verify an OpenCode config directory."""
    from opencode_harness_bridge.safety.tiers import looks_like_secret

    target: Path = args.target_dir.expanduser()
    print(f"opencode-harness-bridge {__version__} — validate")
    print(f"  target: {target}")
    print()
    if not target.exists():
        print(f"error: target directory does not exist: {target}", file=sys.stderr)
        return 2

    opencode_json = target / "opencode.json"
    errors: list[str] = []
    if opencode_json.exists():
        try:
            import json as _json

            data = _json.loads(opencode_json.read_text(encoding="utf-8"))
            print(f"  ✓ opencode.json syntax OK ({len(data)} top-level keys)")
            text = opencode_json.read_text(encoding="utf-8")
            if looks_like_secret(text):
                errors.append("secret detected in opencode.json")
                print("  ✗ secret detected in opencode.json")
            else:
                print("  ✓ no secrets detected")
        except _json.JSONDecodeError as e:
            errors.append(f"opencode.json is invalid JSON: {e}")
            print(f"  ✗ opencode.json invalid JSON: {e}")
    else:
        print("  - opencode.json not present (nothing to validate)")

    if errors:
        print()
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    print()
    print("PASS")
    return 0


def _cmd_maintain(args: argparse.Namespace) -> int:
    """Report-only drift detection (no apply)."""
    from opencode_harness_bridge.audit.classify import migrate
    from opencode_harness_bridge.sync import maintain

    target_dir = Path(args.target_dir).expanduser().resolve()
    if not target_dir.is_dir():
        print(
            f"error: target directory does not exist or is not a directory: {target_dir}",
            file=sys.stderr,
        )
        return 2

    workspace = Path(args.workspace).expanduser().resolve()
    plan = migrate(source=args.source, target="opencode", workspace=workspace)
    report = maintain(plan=plan, target_dir=target_dir)

    if args.format == "json":
        import json as _json
        print(_json.dumps(report.to_dict()))
        return 0

    print(f"opencode-harness-bridge {__version__} — maintain")
    print(f"  source:    {report.source}")
    print(f"  workspace: {plan.workspace}")
    print(f"  target:    {report.target_dir}")
    print()

    # Markdown format: header + sections
    n_total = (
        len(report.added) + len(report.modified) + len(report.removed) + report.unchanged_count
    )
    print(
        f"Maintenance: {len(report.added)} added, {len(report.modified)} modified, "
        f"{len(report.removed)} removed, {report.unchanged_count} unchanged "
        f"({n_total} total)"
    )

    def _emit_section(label: str, items: tuple) -> None:
        if not items:
            return
        print(f"\n## {label} ({len(items)})")
        for it in items:
            print(f"  - [{it.tier}] {it.kind} {it.target_subpath}  {it.description}")

    _emit_section("Added", report.added)
    _emit_section("Modified", report.modified)
    _emit_section("Removed", report.removed)

    if report.manual_steps:
        print(f"\n## Manual steps ({len(report.manual_steps)})")
        for step in report.manual_steps:
            print(f"  - [{step['tier']}] {step['kind']}  {step['action']}")

    return 0


_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "inventory": _cmd_inventory,
    "classify": _cmd_classify,
    "convert": _cmd_convert,
    "validate": _cmd_validate,
    "maintain": _cmd_maintain,
}


if __name__ == "__main__":
    sys.exit(main())
