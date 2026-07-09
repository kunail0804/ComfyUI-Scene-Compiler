"""Golden tests for the ten reference scenes (issue #28, MASTER_SPEC §26.7, §26.8).

Each scene compiles to a fixed set of prompt outputs; this asserts exact equality
against the stored golden files, guarding determinism across changes. Regenerate
the goldens deliberately with ``python scripts/regenerate_goldens.py`` when a
change is intended to alter output.
"""

from __future__ import annotations

import json

import pytest

from tests.regression.golden_scenes import (
    GOLDEN_DIR,
    SCENES,
    compile_prompt_outputs,
    load_reference_knowledge_base,
)


@pytest.fixture(scope="module")
def knowledge_base():
    return load_reference_knowledge_base()


def test_all_ten_reference_scenes_have_goldens() -> None:
    assert len(SCENES) == 10
    for name in SCENES:
        assert (GOLDEN_DIR / f"{name}.json").is_file(), f"missing golden for {name}"


@pytest.mark.parametrize("name", sorted(SCENES))
def test_scene_matches_golden(name: str, knowledge_base) -> None:
    expected = json.loads((GOLDEN_DIR / f"{name}.json").read_text(encoding="utf-8"))
    actual = compile_prompt_outputs(SCENES[name], knowledge_base)
    assert actual == expected


@pytest.mark.parametrize("name", sorted(SCENES))
def test_scene_is_deterministic(name: str, knowledge_base) -> None:
    first = compile_prompt_outputs(SCENES[name], knowledge_base)
    second = compile_prompt_outputs(SCENES[name], knowledge_base)
    assert first == second
