"""Guards that the docs describe the actual shipped nodes (issue #31).

Catches stale or missing node references so documentation cannot drift from the
registered ComfyUI nodes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import nodes

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_DISPLAY_NAMES = sorted(nodes.NODE_DISPLAY_NAME_MAPPINGS.values())

DOCS_LISTING_NODES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "nodes.md",
]


@pytest.mark.parametrize("doc", DOCS_LISTING_NODES, ids=lambda p: p.name)
def test_docs_mention_every_node(doc: Path) -> None:
    text = doc.read_text(encoding="utf-8")
    missing = [name for name in NODE_DISPLAY_NAMES if name not in text]
    assert not missing, f"{doc.name} is missing node references: {missing}"


def test_node_reference_covers_inter_stage_types() -> None:
    text = (REPO_ROOT / "docs" / "nodes.md").read_text(encoding="utf-8")
    for type_name in (
        "SCENE",
        "RESOLVED_TAGS",
        "CATEGORY_MAP",
        "KNOWLEDGE_BASE",
        "COMPILER_CONFIG",
    ):
        assert type_name in text


def test_contributing_links_the_knowledge_base_guide() -> None:
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "knowledge_base/README.md" in text
    assert "validate_knowledge_base.py" in text
