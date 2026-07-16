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
    compile_prompt,
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


def test_performance_regression_guard() -> None:
    """Guard against gross perf regressions (issue #134, epic #38).

    Uses generous ceilings and a relative ratio rather than machine-specific
    absolute timings, so it is non-flaky under CI load but still fails on a
    deliberate slowdown (e.g. reloading the Knowledge Base or rebuilding the
    normalized index on every resolve).
    """
    kb = load_reference_knowledge_base()
    scene = SCENES["complex_multi_character"]
    kb_load = measure_kb_load(iterations=3)  # few iterations: a full load is costly
    resolution = measure_resolution(kb, scene, iterations=50)
    full_pipeline = measure_full_pipeline(kb, scene, iterations=50)

    # Generous absolute ceilings (sub-millisecond in practice; ample headroom).
    assert resolution < 0.05
    assert full_pipeline < 0.1
    # Relative guard: a single resolution and a full non-Analyzer pipeline must be
    # a small fraction of a full Knowledge Base load. Disabling the KB cache or the
    # compiled-index cache (reloading/rebuilding per resolve) would break this.
    assert resolution < kb_load
    assert full_pipeline < kb_load


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
        compile_prompt(scene, kb)
    assert calls["n"] == 0  # compilation reuses the passed Knowledge Base


def test_kb_loading_reuses_cached_kb_across_runs(tmp_path, monkeypatch) -> None:
    from nodes import kb_loading

    (tmp_path / "hair.json").write_text(
        '[{"id": "long_hair", "tags": ["long hair"], "category": "hair"}]', encoding="utf-8"
    )
    calls = {"n": 0}
    real_load = kb_module.load_knowledge_base

    def counting_load(*args, **kwargs):
        calls["n"] += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr(kb_module, "load_knowledge_base", counting_load)
    # Isolate the process-wide cache for this test.
    monkeypatch.setattr(kb_loading, "_LOADERS", {})
    monkeypatch.setattr(kb_loading, "_LAST_RELOAD", {})

    kb1 = kb_loading.load_cached_knowledge_base(str(tmp_path))[0]
    kb2 = kb_loading.load_cached_knowledge_base(str(tmp_path))[0]
    assert kb1 is kb2  # same cached object reused across calls
    assert calls["n"] == 1  # loaded once

    kb3 = kb_loading.load_cached_knowledge_base(str(tmp_path), reload=1)[0]  # forces a fresh read
    assert calls["n"] == 2
    assert kb3 is not kb1


def test_resolution_reuses_compiled_normalized_index(monkeypatch) -> None:
    # The normalized lookup table is compiled once per KB and reused across
    # resolves, not rebuilt on every resolve_scene (#131).
    kb = load_reference_knowledge_base()
    builds = {"n": 0}
    real = type(kb).normalized_index

    def counting(self, include_nsfw):
        if include_nsfw not in self._normalized_index:
            builds["n"] += 1
        return real(self, include_nsfw)

    monkeypatch.setattr(type(kb), "normalized_index", counting)
    for scene in SCENES.values():
        compile_prompt(scene, kb)
    assert builds["n"] == 1  # built once for the general (non-NSFW) gating, then reused
