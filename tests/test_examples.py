"""Tests that the shipped example scenes compile to their documented outputs (#30)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.regression.golden_scenes import (
    compile_prompt_outputs,
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
    assert compile_prompt_outputs(scene, knowledge_base) == expected


def test_workflow_is_valid_json_referencing_registered_nodes() -> None:
    import nodes

    workflow = json.loads(WORKFLOW_FILE.read_text(encoding="utf-8"))
    node_types = {node["type"] for node in workflow["nodes"]}
    # Every node type in the example workflow is a registered Scene Compiler node.
    assert node_types <= set(nodes.NODE_CLASS_MAPPINGS)
    # The full pipeline is present.
    for required in (
        "SceneCompilerConfiguration",
        "SceneCompilerKnowledgeBaseLoader",
        "SceneCompilerAnalyzer",
        "SceneCompilerValidator",
        "SceneCompilerResolver",
        "SceneCompilerCategorySplitter",
        "SceneCompilerPromptBuilder",
    ):
        assert required in node_types
