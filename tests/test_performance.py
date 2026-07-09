"""Performance tests and benchmark smoke test (issue #29, §26.6, NFR-004)."""

from __future__ import annotations

from pathlib import Path

import compiler.common.knowledge_base as kb_module
from scripts.benchmark import (
    measure_full_pipeline,
    measure_kb_load,
    measure_resolution,
    run_benchmarks,
)
from tests.regression.golden_scenes import (
    SCENES,
    compile_prompt_outputs,
    load_reference_knowledge_base,
)

BASELINE_FILE = Path(__file__).resolve().parent.parent / "docs" / "benchmarks.md"


def test_benchmark_functions_return_positive_durations() -> None:
    kb = load_reference_knowledge_base()
    scene = SCENES["complex_multi_character"]
    assert measure_kb_load(iterations=2) > 0
    assert measure_resolution(kb, scene, iterations=5) > 0
    assert measure_full_pipeline(kb, scene, iterations=5) > 0


def test_run_benchmarks_reports_all_metrics() -> None:
    results = run_benchmarks()
    assert set(results) == {"knowledge_base_load", "single_scene_resolution", "full_pipeline"}
    assert all(value > 0 for value in results.values())


def test_full_pipeline_is_fast() -> None:
    # Generous, non-flaky bound: the non-Analyzer pipeline is sub-millisecond in
    # practice; 100 ms leaves ample margin under CI load.
    kb = load_reference_knowledge_base()
    scene = SCENES["complex_multi_character"]
    assert measure_full_pipeline(kb, scene, iterations=20) < 0.1


def test_recorded_baseline_exists() -> None:
    assert BASELINE_FILE.is_file()
    assert "Performance baselines" in BASELINE_FILE.read_text(encoding="utf-8")


def test_knowledge_base_loaded_once_and_reused(tmp_path, monkeypatch) -> None:
    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]',
        encoding="utf-8",
    )
    calls = {"n": 0}
    real_load = kb_module.load_knowledge_base

    def counting_load(*args, **kwargs):
        calls["n"] += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr(kb_module, "load_knowledge_base", counting_load)

    loader = kb_module.KnowledgeBaseLoader(tmp_path)
    loaded = [loader.get() for _ in range(5)]

    assert calls["n"] == 1  # loaded once
    assert all(kb is loaded[0] for kb in loaded)  # reused


def test_pipeline_does_not_reload_knowledge_base(monkeypatch) -> None:
    kb = load_reference_knowledge_base()
    calls = {"n": 0}
    monkeypatch.setattr(
        kb_module, "load_knowledge_base", lambda *a, **k: calls.__setitem__("n", calls["n"] + 1)
    )
    for scene in SCENES.values():
        compile_prompt_outputs(scene, kb)
    assert calls["n"] == 0  # compilation reuses the passed Knowledge Base
