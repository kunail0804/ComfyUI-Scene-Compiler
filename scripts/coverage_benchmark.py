"""Knowledge Base coverage benchmark (issue #121, epic #35).

Runs a fixed corpus of representative concept phrases through the deterministic
Resolver and measures how well the Knowledge Base covers them:

- **hit rate** by resolution path — ``exact`` (direct id/alias hit), ``head_noun``
  (recovered via the head-noun reduction, ``SC0019``), ``fallback`` (semantic
  nearest-neighbour, ``SC0020``, when that feature is enabled), and ``dropped``
  (no entry, ``SC0001``).
- **per-category coverage** — the category of the first resolved tag for each
  covered phrase.

The report is informational (no hard threshold gate — one can be added later). It
is deterministic: a fixed corpus and no live model. Prints a human summary and
writes a JSON summary.

Usage:
    python scripts/coverage_benchmark.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.config import Config  # noqa: E402
from compiler.common.knowledge_base import KnowledgeBase, load_knowledge_base  # noqa: E402
from compiler.resolver.illustrious_resolver import resolve_scene  # noqa: E402
from schemas.models import Scene  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KB_DIR = _REPO_ROOT / "knowledge_base"
_CORPUS = _REPO_ROOT / "data" / "coverage_corpus.txt"
_REPORT = _REPO_ROOT / "docs" / "kb_coverage.json"

_PATHS = ("exact", "head_noun", "fallback", "dropped")


def load_corpus(path: Path = _CORPUS) -> list[str]:
    """Read the corpus file: one phrase per line, ignoring blanks and comments."""
    phrases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            phrases.append(stripped)
    return phrases


def _single_concept_scene(phrase: str) -> Scene:
    return Scene.from_json(
        {
            "characters": [
                {
                    "id": 0,
                    "identity": [phrase],
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


def _classify(phrase: str, kb: KnowledgeBase, config: Config) -> tuple[str, str | None]:
    """Return (resolution path, first resolved tag category) for one phrase."""
    result = resolve_scene(_single_concept_scene(phrase), kb, config)
    codes = {warning.code for warning in result.warnings}
    tags = result.data or ()
    category = tags[0].category if tags else None
    if "SC0001" in codes and not tags:
        return "dropped", None
    if "SC0020" in codes:
        return "fallback", category
    if "SC0019" in codes:
        return "head_noun", category
    return "exact", category


def measure_coverage(kb: KnowledgeBase, phrases: list[str], config: Config | None = None) -> dict:
    """Measure resolution hit-rate and per-category coverage over a phrase corpus."""
    config = config or Config()
    hits: Counter[str] = Counter({path: 0 for path in _PATHS})
    per_category: Counter[str] = Counter()
    for phrase in phrases:
        path, category = _classify(phrase, kb, config)
        hits[path] += 1
        if category is not None:
            per_category[category] += 1

    total = len(phrases)
    covered = total - hits["dropped"]
    return {
        "total": total,
        "covered": covered,
        "coverage_rate": round(covered / total, 4) if total else 0.0,
        "hit_rate": {path: hits[path] for path in _PATHS},
        "per_category": dict(sorted(per_category.items())),
    }


def run() -> dict:
    kb = load_knowledge_base(_KB_DIR)
    return measure_coverage(kb, load_corpus())


def _format_human(summary: dict) -> str:
    lines = [
        f"KB coverage: {summary['covered']}/{summary['total']} "
        f"({summary['coverage_rate'] * 100:.1f}%)",
        "  by path: " + ", ".join(f"{path}={count}" for path, count in summary["hit_rate"].items()),
        "  by category: "
        + ", ".join(f"{cat}={count}" for cat, count in summary["per_category"].items()),
    ]
    return "\n".join(lines)


def main() -> int:
    summary = run()
    _REPORT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(_format_human(summary))
    print(f"wrote JSON summary to {_REPORT.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
