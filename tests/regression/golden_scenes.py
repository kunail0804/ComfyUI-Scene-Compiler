"""Reference scene set and the pipeline runner for golden tests (issue #28).

The ten reference scenes (MASTER_SPEC §26.8) are defined here as fixed Scene JSON
inputs. Their expected prompt outputs are stored as golden files in
``tests/regression/golden/`` and are regenerated deliberately via
``scripts/regenerate_goldens.py`` — never automatically.

Both the golden test and the regeneration script import from this module so the
inputs and the compilation path stay in one place.
"""

from __future__ import annotations

from pathlib import Path

from compiler.common.config import Config
from compiler.common.knowledge_base import KnowledgeBase, load_knowledge_base
from compiler.resolver.illustrious_resolver import resolve_scene, tags_to_prompt
from compiler.validator.scene_validator import validate_scene

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KB_DIR = _REPO_ROOT / "knowledge_base"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _character(id_: int, **fields) -> dict:
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


def _scene(characters, interactions=(), **sections) -> dict:
    return {
        "characters": list(characters),
        "interactions": list(interactions),
        "objects": list(sections.get("objects", [])),
        "environment": list(sections.get("environment", [])),
        "camera": list(sections.get("camera", [])),
        "lighting": list(sections.get("lighting", [])),
        "metadata": {"schema_version": "1.0"},
    }


# The ten reference scenes. Concepts are drawn from the shipped Knowledge Base,
# except the deliberately-unknown/ambiguous ones used to pin down that behaviour.
SCENES: dict[str, dict] = {
    "single_character": _scene(
        [
            _character(
                0,
                identity=["girl"],
                appearance=["blonde hair", "blue eyes"],
                clothing=["dress"],
                expression=["smile"],
            )
        ],
        environment=["classroom"],
        lighting=["sunset"],
    ),
    "two_characters": _scene(
        [
            _character(0, identity=["girl"], appearance=["long hair"]),
            _character(1, identity=["man"], appearance=["short hair"]),
        ],
    ),
    "character_interaction": _scene(
        [_character(0, identity=["girl"]), _character(1, identity=["boy"])],
        interactions=[{"participants": [0, 1], "concept": "hug"}],
    ),
    "indoor": _scene(
        [_character(0, identity=["girl"], pose=["sitting"])],
        objects=["chair", "table"],
        environment=["bedroom"],
    ),
    "outdoor": _scene(
        [_character(0, identity=["girl"], actions=["walking"])],
        environment=["forest"],
        camera=["wide shot"],
    ),
    "fantasy": _scene(
        [
            _character(
                0,
                identity=["girl"],
                appearance=["pointy ears", "wings"],
                clothing=["armor", "cape"],
            )
        ],
        objects=["sword", "shield"],
        environment=["castle"],
        lighting=["moonlight"],
    ),
    "modern": _scene(
        [_character(0, identity=["man"], clothing=["jeans", "hoodie"], accessories=["sunglasses"])],
        objects=["phone", "car"],
        environment=["city"],
    ),
    "unknown_concepts": _scene(
        [
            _character(
                0,
                identity=["girl"],
                appearance=["cyberpunk implants", "blue eyes"],
                clothing=["hologram jacket"],
            )
        ],
        environment=["spaceport"],
    ),
    "ambiguous_concepts": _scene(
        [
            _character(
                0,
                identity=["girl"],
                appearance=["orange"],
                expression=["blush"],
            )
        ],
        environment=["spring"],
    ),
    "complex_multi_character": _scene(
        [
            _character(
                0,
                identity=["girl"],
                appearance=["long hair", "green eyes"],
                clothing=["school uniform"],
                expression=["smile"],
            ),
            _character(1, identity=["boy"], appearance=["short hair"], clothing=["jacket"]),
            _character(2, identity=["child"], expression=["laughing"]),
        ],
        interactions=[
            {"participants": [0, 1], "concept": "holding hands"},
            {"participants": [0, 2], "concept": "carrying"},
        ],
        objects=["umbrella"],
        environment=["park"],
        camera=["wide shot"],
        lighting=["sunset"],
    ),
}


def load_reference_knowledge_base() -> KnowledgeBase:
    """Load the shipped Knowledge Base used by the reference scenes."""
    return load_knowledge_base(KB_DIR)


def compile_prompt(scene: dict, knowledge_base: KnowledgeBase) -> str:
    """Run the full no-LLM pipeline and return the flat prompt string."""
    config = Config()
    validated = validate_scene(scene, config)
    resolved = resolve_scene(validated.data, knowledge_base, config)
    return tags_to_prompt(resolved.data, config.prompt_builder.separator)
