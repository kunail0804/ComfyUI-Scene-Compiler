"""Parallel resolution determinism (issue #133, epic #38)."""

from __future__ import annotations

from compiler.common.config import Config
from compiler.resolver.illustrious_resolver import resolve_scene
from schemas.models import Scene
from tests.regression.golden_scenes import load_reference_knowledge_base

# A mix of exact hits, alias hits, head-noun reductions, and unknowns.
_BASE = [
    "long hair",
    "blue eyes",
    "thighhighs",
    "jacket",
    "open white shirt",
    "white summer dress",
    "smile",
    "sitting",
    "classroom",
    "sunset",
    "quantum flux inverter",
]


def _big_scene(n: int) -> Scene:
    concepts = [_BASE[i % len(_BASE)] for i in range(n - 5)] + [
        f"unique_unknown_{i}" for i in range(5)
    ]
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": concepts,
                    "appearance": [],
                    "clothing": [],
                    "accessories": [],
                    "pose": [],
                    "expression": [],
                    "actions": [],
                }
            ],
            "interactions": [],
            "objects": [],
            "environment": [],
            "camera": [],
            "lighting": [],
            "metadata": {"schema_version": "1.0"},
        }
    )


def _resolve(scene, threshold):
    return resolve_scene(
        scene, load_reference_knowledge_base(), Config(), parallel_threshold=threshold
    )


def test_parallel_matches_sequential_exactly() -> None:
    scene = _big_scene(80)  # above the default threshold
    sequential = _resolve(scene, 0)  # forced sequential
    parallel = _resolve(scene, 1)  # forced parallel
    assert [t.tag for t in parallel.data] == [t.tag for t in sequential.data]
    assert [m.code for m in parallel.warnings] == [m.code for m in sequential.warnings]


def test_parallel_is_deterministic_across_runs() -> None:
    scene = _big_scene(90)
    first = [t.tag for t in _resolve(scene, 1).data]
    second = [t.tag for t in _resolve(scene, 1).data]
    assert first == second


def test_many_scene_sizes_match_sequential() -> None:
    kb = load_reference_knowledge_base()
    for n in (1, 10, 63, 64, 65, 128):
        scene = _big_scene(n)
        seq = resolve_scene(scene, kb, Config(), parallel_threshold=0)
        par = resolve_scene(scene, kb, Config(), parallel_threshold=1)
        assert [t.tag for t in par.data] == [t.tag for t in seq.data], n
