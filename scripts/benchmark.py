"""Benchmark the non-Analyzer compiler pipeline (issue #29, MASTER_SPEC §26.6, NFR-004).

Measures Knowledge Base load time, single-scene resolution time, and full
non-Analyzer pipeline time (median over several iterations). Prints a table and
records a baseline to ``docs/benchmarks.md`` for future comparison.

Usage:
    python scripts/benchmark.py
"""

from __future__ import annotations

import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.builder.prompt_builder import build_prompts  # noqa: E402
from compiler.common.config import Config  # noqa: E402
from compiler.common.knowledge_base import KnowledgeBase, load_knowledge_base  # noqa: E402
from compiler.resolver.illustrious_resolver import resolve_scene  # noqa: E402
from compiler.splitter.category_splitter import split_into_categories  # noqa: E402
from compiler.validator.scene_validator import validate_scene  # noqa: E402
from tests.regression.golden_scenes import KB_DIR, SCENES  # noqa: E402

_BENCHMARK_SCENE = "complex_multi_character"
_BASELINE_FILE = Path(__file__).resolve().parent.parent / "docs" / "benchmarks.md"


def _median_seconds(operation: Callable[[], object], iterations: int) -> float:
    """Return the median wall-clock time of ``operation`` over ``iterations`` runs."""
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        operation()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def measure_kb_load(iterations: int = 20) -> float:
    return _median_seconds(lambda: load_knowledge_base(KB_DIR), iterations)


def measure_resolution(kb: KnowledgeBase, scene: dict, iterations: int = 200) -> float:
    config = Config()
    validated = validate_scene(scene, config).data
    return _median_seconds(lambda: resolve_scene(validated, kb, config), iterations)


def measure_full_pipeline(kb: KnowledgeBase, scene: dict, iterations: int = 200) -> float:
    config = Config()

    def run() -> None:
        validated = validate_scene(scene, config)
        resolved = resolve_scene(validated.data, kb, config)
        categorized = split_into_categories(resolved.data)
        build_prompts(categorized.data, config)

    return _median_seconds(run, iterations)


def run_benchmarks() -> dict[str, float]:
    """Run all benchmarks and return their median seconds."""
    kb = load_knowledge_base(KB_DIR)
    scene = SCENES[_BENCHMARK_SCENE]
    return {
        "knowledge_base_load": measure_kb_load(),
        "single_scene_resolution": measure_resolution(kb, scene),
        "full_pipeline": measure_full_pipeline(kb, scene),
    }


def _format_baseline(results: dict[str, float], entry_count: int) -> str:
    lines = [
        "# Performance baselines",
        "",
        "Median wall-clock times for the non-Analyzer pipeline "
        f"(Knowledge Base: {entry_count} entries; scene: `{_BENCHMARK_SCENE}`).",
        "Numbers are machine-dependent and indicative; regenerate with "
        "`python scripts/benchmark.py`.",
        "",
        "| Metric | Median |",
        "|---|---|",
        f"| Knowledge Base load | {results['knowledge_base_load'] * 1e3:.2f} ms |",
        f"| Single-scene resolution | {results['single_scene_resolution'] * 1e6:.1f} µs |",
        f"| Full pipeline (validate → build) | {results['full_pipeline'] * 1e6:.1f} µs |",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    results = run_benchmarks()
    entry_count = len(load_knowledge_base(KB_DIR))
    baseline = _format_baseline(results, entry_count)
    _BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BASELINE_FILE.write_text(baseline, encoding="utf-8")
    sys.stdout.write(baseline)
    sys.stdout.write(f"\nWrote baseline to {_BASELINE_FILE}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
