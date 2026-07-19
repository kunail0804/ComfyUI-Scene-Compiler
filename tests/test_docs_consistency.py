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
    # The live inter-stage types. RESOLVED_TAGS and CATEGORY_MAP were retired with
    # the Category Splitter and Prompt Builder in V1.1, so the reference must not be
    # required to mention them.
    text = (REPO_ROOT / "docs" / "nodes.md").read_text(encoding="utf-8")
    for type_name in ("SCENE", "KNOWLEDGE_BASE", "COMPILER_CONFIG"):
        assert type_name in text


def test_node_reference_does_not_resurrect_removed_nodes() -> None:
    """Guard the reference against listing nodes that no longer ship.

    Matches table rows only, so prose explaining that a node was removed is fine.
    """
    text = (REPO_ROOT / "docs" / "nodes.md").read_text(encoding="utf-8")
    for removed in ("Knowledge Base Loader", "Category Splitter", "Prompt Builder"):
        row = f"| **{removed}**"
        assert row not in text, f"docs/nodes.md still lists the removed {removed!r} node"


def test_contributing_links_the_knowledge_base_guide() -> None:
    text = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "knowledge_base/README.md" in text
    assert "validate_knowledge_base.py" in text
