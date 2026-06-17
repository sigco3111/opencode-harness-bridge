#!/usr/bin/env python3
"""Example Codex pre-tool-use hook (Python file).

Codex hooks are Python files. v0.3.0+ will wrap these in a shell-callable form for OpenCode.
"""
import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    print(f"pre-tool-use invoked: {payload.get('tool_name', 'unknown')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
