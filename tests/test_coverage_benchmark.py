"""Smoke tests for the KB coverage benchmark harness (issue #121, epic #35)."""

from __future__ import annotations

from scripts.coverage_benchmark import load_corpus, measure_coverage, run
from tests.regression.golden_scenes import load_reference_knowledge_base


def test_run_returns_expected_metric_keys() -> None:
    summary = run()
    assert set(summary) == {"total", "covered", "coverage_rate", "hit_rate", "per_category"}
    assert set(summary["hit_rate"]) == {"exact", "head_noun", "fallback", "dropped"}
    assert summary["total"] > 0
    assert 0.0 <= summary["coverage_rate"] <= 1.0


def test_hit_rate_paths_sum_to_total() -> None:
    kb = load_reference_knowledge_base()
    summary = measure_coverage(kb, load_corpus())
    assert sum(summary["hit_rate"].values()) == summary["total"]
    assert summary["covered"] == summary["total"] - summary["hit_rate"]["dropped"]


def test_known_paths_are_classified() -> None:
    kb = load_reference_knowledge_base()
    # "long hair" resolves exactly; "white summer dress" via head-noun reduction;
    # a nonsense phrase is dropped.
    summary = measure_coverage(kb, ["long hair", "white summer dress", "zzz nonexistent thing"])
    assert summary["hit_rate"]["exact"] >= 1
    assert summary["hit_rate"]["head_noun"] >= 1
    assert summary["hit_rate"]["dropped"] >= 1
