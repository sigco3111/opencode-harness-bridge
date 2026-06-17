"""Entry point for `python -m opencode_harness_bridge`.

Usage:
    python -m opencode_harness_bridge --version
    python -m opencode_harness_bridge --help
    python -m opencode_harness_bridge inventory --source claude-code
    python -m opencode_harness_bridge classify --source claude-code --target opencode
    python -m opencode_harness_bridge convert --source claude-code --target opencode --dry-run
    python -m opencode_harness_bridge validate <opencode_config_dir>

Implementation note (for other-PC worker)
----------------------------------------
This is a thin shim. CLI logic lives in :mod:`opencode_harness_bridge.cli`.
"""

from __future__ import annotations

import sys

from opencode_harness_bridge.cli import main

if __name__ == "__main__":
    sys.exit(main())
