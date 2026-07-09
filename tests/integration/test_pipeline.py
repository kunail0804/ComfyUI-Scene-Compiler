"""End-to-end compiler pipeline tests (issue #27, MASTER_SPEC §26.2).

Exercises Scene JSON -> Validator -> Resolver -> Category Splitter -> Prompt
Builder against the shipped Knowledge Base. The Analyzer is bypassed (fixed Scene
JSON inputs), so no test requires a running Ollama.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compiler.builder.prompt_builder import build_prompts
from compiler.common.config import Config
from compiler.common.knowledge_base import load_knowledge_base
from compiler.resolver.illustrious_resolver import resolve_scene
from compiler.splitter.category_splitter import split_into_categories
from compiler.validator.scene_validator import validate_scene

KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


@pytest.fixture(scope="module")
def knowledge_base():
    return load_knowledge_base(KB_DIR)


def character(id_: int, **fields) -> dict:
    base = {
        "id": id_,
        "identity": [],
        "appearance": [],
        "clothing": [],
        "accessories": [],
        "pose": [],
        "expression": [],
        "actions": [],
    }
    base.update(fields)
    return base


def scene(characters, interactions=(), **sections) -> dict:
    return {
        "characters": list(characters),
        "interactions": list(interactions),
        "objects": list(sections.get("objects", [])),
        "environment": list(sections.get("environment", [])),
        "camera": list(sections.get("camera", [])),
        "lighting": list(sections.get("lighting", [])),
        "metadata": {"schema_version": "1.0"},
    }


class Compiled:
    """The outputs of a full compilation run."""

    def __init__(self, outputs: dict[str, str], warning_codes: list[str]) -> None:
        self.outputs = outputs
        self.warning_codes = warning_codes


def compile_scene(scene_json: dict, knowledge_base, config: Config) -> Compiled:
    """Run the full no-LLM pipeline and return the prompt outputs + warnings."""
    validated = validate_scene(scene_json, config)
    assert validated.success, [m.code for m in validated.errors]

    resolved = resolve_scene(validated.data, knowledge_base, config)
    assert resolved.success, [m.code for m in resolved.errors]

    categorized = split_into_categories(resolved.data)
    assert categorized.success, [m.code for m in categorized.errors]

    built = build_prompts(categorized.data, config)
    outputs = {output.name: output.value for output in built.data}
    warning_codes = [m.code for m in (*validated.warnings, *resolved.warnings)]
    return Compiled(outputs, warning_codes)


# --- reference scenes ------------------------------------------------------


def test_single_character(knowledge_base) -> None:
    doc = scene(
        [
            character(
                0,
                identity=["girl"],
                appearance=["blonde hair", "blue eyes"],
                clothing=["dress"],
                expression=["smile"],
            )
        ],
        environment=["classroom"],
        lighting=["sunset"],
    )
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["character"] == "1girl"
    assert result.outputs["hair"] == "blonde hair"
    assert result.outputs["eyes"] == "blue eyes"
    assert result.outputs["clothing"] == "dress"
    assert result.outputs["expression"] == "smile"
    assert result.outputs["environment"] == "classroom"
    assert result.outputs["lighting"] == "sunset"
    assert result.outputs["negative"] == ""
    assert "SC0001" not in result.warning_codes  # all core concepts are known


def test_two_characters(knowledge_base) -> None:
    doc = scene(
        [
            character(0, identity=["girl"], appearance=["long hair"]),
            character(1, identity=["man"], appearance=["short hair"]),
        ]
    )
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["character"] == "1girl,1boy"
    assert result.outputs["hair"] == "long hair,short hair"


def test_character_interaction(knowledge_base) -> None:
    doc = scene(
        [character(0, identity=["girl"]), character(1, identity=["boy"])],
        interactions=[{"participants": [0, 1], "concept": "hug"}],
    )
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["character"] == "1girl,1boy"
    assert result.outputs["interaction"] == "hug"


def test_indoor_scene(knowledge_base) -> None:
    doc = scene(
        [character(0, identity=["girl"], pose=["sitting"])],
        objects=["chair", "table"],
        environment=["bedroom"],
    )
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["environment"] == "bedroom"
    assert result.outputs["objects"] == "chair,table"
    assert result.outputs["pose"] == "sitting"


def test_outdoor_scene(knowledge_base) -> None:
    doc = scene(
        [character(0, identity=["girl"], actions=["walking"])],
        environment=["forest"],
        camera=["wide shot"],
    )
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["environment"] == "forest"
    assert result.outputs["action"] == "walking"
    assert result.outputs["camera"] == "wide shot"


# --- determinism -----------------------------------------------------------


def test_pipeline_is_deterministic(knowledge_base) -> None:
    doc = scene(
        [
            character(
                0,
                identity=["girl"],
                appearance=["blonde hair"],
                clothing=["school uniform"],
            )
        ],
        environment=["classroom"],
    )
    first = compile_scene(doc, knowledge_base, Config())
    second = compile_scene(doc, knowledge_base, Config())
    assert first.outputs == second.outputs


def test_expansion_flows_end_to_end(knowledge_base) -> None:
    # school_uniform expands to blazer + pleated_skirt in the shipped KB.
    doc = scene([character(0, identity=["girl"], clothing=["school uniform"])])
    result = compile_scene(doc, knowledge_base, Config())
    assert result.outputs["clothing"] == "school uniform,blazer,pleated skirt"
