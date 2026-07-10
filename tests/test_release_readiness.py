"""Release-readiness checks for Version 1 (issue #32)."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_version_is_1_1_0() -> None:
    assert _pyproject()["project"]["version"] == "1.1.0"


def test_changelog_documents_current_version() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "1.1.0" in changelog


def test_definition_of_done_exists() -> None:
    assert (REPO_ROOT / "docs" / "definition_of_done.md").is_file()


def test_all_schema_files_present() -> None:
    schema_files = {p.name for p in (REPO_ROOT / "schemas" / "json").glob("*.schema.json")}
    expected = {
        "scene.schema.json",
        "character.schema.json",
        "concept.schema.json",
        "interaction.schema.json",
        "metadata.schema.json",
        "knowledge_base_entry.schema.json",
        "resolved_tag.schema.json",
        "configuration.schema.json",
    }
    assert expected <= schema_files


def test_knowledge_base_domain_files_present() -> None:
    kb_files = {p.name for p in (REPO_ROOT / "knowledge_base").glob("*.json")}
    # The by-domain layout from MASTER_SPEC §15.3.
    for domain in ("appearance", "clothing", "anatomy", "expressions", "environments"):
        assert f"{domain}.json" in kb_files


def test_default_config_and_prompt_shipped() -> None:
    assert (REPO_ROOT / "config" / "default_config.json").is_file()
    assert (REPO_ROOT / "prompts" / "analyzer_system_prompt.md").is_file()


def test_manifest_includes_data_directories() -> None:
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    for directory in ("schemas", "knowledge_base", "prompts", "config"):
        assert directory in manifest


def test_schemas_are_declared_as_package_data() -> None:
    package_data = _pyproject()["tool"]["setuptools"]["package-data"]
    assert any("json" in pattern for pattern in package_data["schemas"])
