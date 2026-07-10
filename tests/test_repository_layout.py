"""Verify the repository layout matches MASTER_SPEC §24.

This guards the acceptance criterion "Directory layout matches section 24 exactly"
and doubles as the smoke test proving pytest collects and runs successfully.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories required by MASTER_SPEC §24 (Repository Structure).
REQUIRED_DIRS = [
    "nodes",
    "compiler",
    "compiler/analyzer",
    "compiler/validator",
    "compiler/resolver",
    "compiler/common",
    "knowledge_base",
    "schemas",
    "prompts",
    "config",
    "tests",
    "tests/analyzer",
    "tests/resolver",
    "tests/validator",
    "tests/integration",
    "tests/regression",
    "examples",
    "scripts",
    "docs",
]

# Files required at the repository root by §24.
REQUIRED_ROOT_FILES = [
    "__init__.py",
    "LICENSE",
    "README.md",
    "pyproject.toml",
]

# Python packages that must be importable (root loaded by ComfyUI by path, not here).
CODE_PACKAGES = [
    "compiler",
    "compiler.analyzer",
    "compiler.validator",
    "compiler.resolver",
    "compiler.common",
    "nodes",
    "schemas",
]


def test_required_directories_exist() -> None:
    missing = [d for d in REQUIRED_DIRS if not (REPO_ROOT / d).is_dir()]
    assert not missing, f"Missing directories from MASTER_SPEC §24: {missing}"


def test_required_root_files_exist() -> None:
    missing = [f for f in REQUIRED_ROOT_FILES if not (REPO_ROOT / f).is_file()]
    assert not missing, f"Missing required root files: {missing}"


def test_code_packages_are_importable() -> None:
    import importlib

    for package in CODE_PACKAGES:
        importlib.import_module(package)
