"""Tests that the shipped example scenes compile to their documented outputs (#30)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.regression.golden_scenes import (
    compile_prompt,
    load_reference_knowledge_base,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
SCENES_DIR = EXAMPLES_DIR / "scenes"
WORKFLOW_FILE = EXAMPLES_DIR / "workflows" / "scene_compiler_pipeline.json"

SCENE_FILES = sorted(SCENES_DIR.glob("*.scene.json"))


@pytest.fixture(scope="module")
def knowledge_base():
    return load_reference_knowledge_base()


def test_example_scenes_exist() -> None:
    assert SCENE_FILES, "no example scenes found"
    for scene_file in SCENE_FILES:
        expected = scene_file.with_name(scene_file.name.replace(".scene.json", ".prompts.json"))
        assert expected.is_file(), f"missing expected outputs for {scene_file.name}"


@pytest.mark.parametrize("scene_file", SCENE_FILES, ids=lambda p: p.stem)
def test_example_scene_compiles_to_documented_outputs(scene_file: Path, knowledge_base) -> None:
    scene = json.loads(scene_file.read_text(encoding="utf-8"))
    expected_file = scene_file.with_name(scene_file.name.replace(".scene.json", ".prompts.json"))
    expected = json.loads(expected_file.read_text(encoding="utf-8"))
    assert compile_prompt(scene, knowledge_base) == expected


def test_workflow_is_valid_json_referencing_registered_nodes() -> None:
    import nodes

    workflow = json.loads(WORKFLOW_FILE.read_text(encoding="utf-8"))
    node_types = {node["type"] for node in workflow["nodes"]}
    # Every node type in the example workflow is a registered Scene Compiler node.
    assert node_types <= set(nodes.NODE_CLASS_MAPPINGS)
    # The full pipeline is present.
    for required in (
        "SceneCompilerConfiguration",
        "SceneCompilerAnalyzer",
        "SceneCompilerValidator",
        "SceneCompilerResolver",
    ):
        assert required in node_types


# ComfyUI stores widget values positionally, so a node whose widget list changes
# silently misaligns older saved workflows (a boolean landing where a string is
# expected, etc.). This guards the shipped example against that drift.
_WIDGET_PRIMITIVES = {"STRING", "INT", "FLOAT", "BOOLEAN"}


def _widget_count(input_types: dict) -> int:
    """Count the positional widgets a node exposes (excluding socket-only inputs)."""
    count = 0
    for section in ("required", "optional"):
        for spec in input_types.get(section, {}).values():
            type_name = spec[0]
            options = spec[1] if len(spec) > 1 else {}
            is_combo = isinstance(type_name, (list, tuple))
            is_primitive = isinstance(type_name, str) and type_name in _WIDGET_PRIMITIVES
            # ``forceInput`` primitives render as sockets, not widgets.
            if is_combo or (is_primitive and not options.get("forceInput")):
                count += 1
    return count


def test_workflow_widget_values_align_with_current_nodes() -> None:
    import nodes

    workflow = json.loads(WORKFLOW_FILE.read_text(encoding="utf-8"))
    for node in workflow["nodes"]:
        node_cls = nodes.NODE_CLASS_MAPPINGS[node["type"]]
        expected = _widget_count(node_cls.INPUT_TYPES())
        actual = len(node.get("widgets_values", []))
        assert actual == expected, (
            f"{node['type']} has {actual} saved widget values but the node now "
            f"defines {expected} widgets — the workflow is stale and would misalign."
        )
