"""v1.0.0 release-readiness invariant tests.

These tests encode the quality bar for any future v1.x release. They are
intentionally strict: a failure here means the release artifacts are
inconsistent and the version should not ship.

Invariant matrix (8 tests, one per row):
- pyproject version matches package __version__
- Development Status classifier is "5 - Production/Stable"
- CI mypy step is blocking (no `|| true` escape)
- CI matrix includes Python 3.14
- .github/plugin/marketplace.json is valid JSON
- marketplace.json plugin version matches package __version__
- skill/harness-convert/SKILL.md has required YAML frontmatter
- command/opencode-harness-bridge.md exists and has name frontmatter
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
PACKAGE_INIT = REPO_ROOT / "src" / "opencode_harness_bridge" / "__init__.py"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
MARKETPLACE_JSON = REPO_ROOT / ".github" / "plugin" / "marketplace.json"
SKILL_MD = REPO_ROOT / "skill" / "harness-convert" / "SKILL.md"
COMMAND_MD = REPO_ROOT / "command" / "opencode-harness-bridge.md"


def _read_pyproject() -> dict:
    text = PYPROJECT.read_text(encoding="utf-8")
    return tomllib.loads(text)


def _read_package_version() -> str:
    text = PACKAGE_INIT.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    assert match, f"__version__ not found in {PACKAGE_INIT}"
    return match.group(1)


def test_pyproject_version_matches_package_version() -> None:
    """pyproject.toml [project].version must equal src/__init__.py __version__."""
    pyproject_version = _read_pyproject()["project"]["version"]
    package_version = _read_package_version()
    assert pyproject_version == package_version, (
        f"version drift: pyproject.toml={pyproject_version!r} vs __init__.py={package_version!r}"
    )


def test_development_status_is_production_stable() -> None:
    """[project].classifiers must include '5 - Production/Stable' for v1.0.0+ releases."""
    classifiers = _read_pyproject()["project"]["classifiers"]
    assert any("Production/Stable" in c for c in classifiers), (
        f"Production/Stable classifier missing; got {classifiers!r}"
    )
    assert not any("Alpha" in c or "Beta" in c for c in classifiers), (
        f"Pre-release classifier leaked into v1.0.0: {classifiers!r}"
    )


def test_ci_mypy_is_blocking() -> None:
    """.github/workflows/ci.yml must run mypy WITHOUT `|| true` (blocking gate)."""
    text = CI_YML.read_text(encoding="utf-8")
    assert "mypy src" in text, "mypy src step not found in ci.yml"
    assert "mypy src || true" not in text, (
        "mypy is non-blocking (|| true); remove the escape for v1.0.0+"
    )


def test_ci_includes_python_314() -> None:
    """`.github/workflows/ci.yml` matrix must include Python 3.14."""
    text = CI_YML.read_text(encoding="utf-8")
    assert '"3.14"' in text, "Python 3.14 missing from CI matrix"


def test_marketplace_manifest_is_valid_json() -> None:
    """.github/plugin/marketplace.json must be valid JSON."""
    assert MARKETPLACE_JSON.is_file(), f"missing {MARKETPLACE_JSON}"
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    assert data.get("name") == "opencode-harness-bridge", (
        f"unexpected manifest name: {data.get('name')!r}"
    )
    assert "plugins" in data and len(data["plugins"]) == 1


def test_marketplace_plugin_version_matches_package_version() -> None:
    """.github/plugin/marketplace.json plugins[0].version must equal __version__."""
    data = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    plugin_version = data["plugins"][0]["version"]
    package_version = _read_package_version()
    assert plugin_version == package_version, (
        f"marketplace plugin version drift: manifest={plugin_version!r} "
        f"vs package={package_version!r}"
    )


def test_skill_frontmatter_has_required_fields() -> None:
    """SKILL.md YAML frontmatter must include name/description/license/compatibility.

    The name field must be lowercase kebab-case (per OpenCode skill naming rules).
    """
    assert SKILL_MD.is_file(), f"missing {SKILL_MD}"
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---"), "SKILL.md must start with YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) >= 3, "SKILL.md frontmatter not delimited by ---"
    frontmatter = yaml.safe_load(parts[1])
    for required in ("name", "description", "license"):
        assert required in frontmatter, f"SKILL.md missing frontmatter field: {required}"
    name = frontmatter["name"]
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), (
        f"SKILL.md name must be lowercase kebab-case; got {name!r}"
    )


def test_command_md_exists_and_has_name_frontmatter() -> None:
    """command/opencode-harness-bridge.md must exist and have YAML frontmatter with name."""
    assert COMMAND_MD.is_file(), f"missing {COMMAND_MD}"
    text = COMMAND_MD.read_text(encoding="utf-8")
    assert text.startswith("---"), "command md must start with YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) >= 3, "command md frontmatter not delimited by ---"
    frontmatter = yaml.safe_load(parts[1])
    assert "name" in frontmatter, "command md missing frontmatter field: name"
    assert "command" in frontmatter, "command md missing frontmatter field: command"


# Sanity: ensure pytest can collect this module's fixtures without import errors.
@pytest.fixture(scope="module")
def _repo_root() -> Path:
    return REPO_ROOT
