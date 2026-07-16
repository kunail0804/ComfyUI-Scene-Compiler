"""Concept-fidelity regression cases (epic #86, issue #113).

Durable, data-driven guards for the two fidelity failure modes so they cannot
silently return:

- **Modifier loss during resolution** (#111): the head-noun reduction used to
  drop leading modifiers ("open white shirt" → "white shirt"), silently losing
  "open" even though it forms a valid compound tag. Each case asserts the
  compiled prompt contains both the head-noun tag and the recovered modifier tag.
- **List under-transcription** (#112): every item of a tag-list input must survive
  to the compiled prompt. The list case pins that resolution never silently drops
  a known list item.

Cases are ``(name, scene, required_tags)`` triples, so a new regression is a
one-line addition. Assertions run against the shipped reference Knowledge Base
with a fixed Scene JSON — no live Analyzer backend — so they are deterministic.
Every case here fails against pre-#86 behaviour and passes once the fidelity
fixes land.
"""

from __future__ import annotations

import pytest

from tests.regression.golden_scenes import (
    _character,
    _scene,
    compile_prompt,
    load_reference_knowledge_base,
)

# (name, scene, tags that MUST appear in the compiled prompt)
FIDELITY_CASES = [
    (
        "modifier_open_white_shirt",
        _scene([_character(0, clothing=["open white shirt"])]),
        ["white shirt", "open shirt"],
    ),
    (
        "modifier_long_messy_hair",
        _scene([_character(0, appearance=["long messy hair"])]),
        ["messy hair", "long hair"],
    ),
    (
        "modifier_long_blue_skirt",
        _scene([_character(0, clothing=["long blue skirt"])]),
        ["blue skirt", "long skirt"],
    ),
    (
        "full_list_transcription",
        _scene(
            [
                _character(
                    0, appearance=["long hair", "blue eyes"], clothing=["thighhighs", "jacket"]
                )
            ],
            environment=["classroom"],
        ),
        ["long hair", "blue eyes", "thighhighs", "jacket", "classroom"],
    ),
    # Relational fidelity (bug report #3): the Analyzer must keep held/positioned
    # relationships as concepts ("money in her hand" -> holding money), not collapse
    # them to the bare noun. These pin that the reference KB resolves such concepts,
    # so the improved Analyzer output compiles end to end.
    (
        "relational_holding_money",
        _scene([_character(0, actions=["holding money"])]),
        ["holding money"],
    ),
    (
        "relational_hand_on_hip",
        _scene([_character(0, pose=["hand on own hip"])]),
        ["hand on own hip"],
    ),
    # Conjunction fidelity: both items of "a sword and a shield" must survive.
    (
        "conjunction_sword_and_shield",
        _scene([_character(0, actions=["holding sword", "holding shield"])]),
        ["holding sword", "holding shield"],
    ),
]


@pytest.fixture(scope="module")
def knowledge_base():
    return load_reference_knowledge_base()


@pytest.mark.parametrize(
    "name, scene, required_tags", FIDELITY_CASES, ids=[c[0] for c in FIDELITY_CASES]
)
def test_fidelity_case(name: str, scene, required_tags: list[str], knowledge_base) -> None:
    prompt = compile_prompt(scene, knowledge_base)
    tags = prompt.split(",")
    missing = [tag for tag in required_tags if tag not in tags]
    assert not missing, f"{name}: prompt {prompt!r} is missing {missing}"
