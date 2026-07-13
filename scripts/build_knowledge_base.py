"""Fully-automated Knowledge Base build pipeline (issue #122, epic #35).

One command runs the whole generation flow with **zero human input**:

    build vocab (dev-only) → generate candidates → ingest aliases/implications
    → auto-validate candidates → conflict-scan → write gen_*.json + manifest

- The vocab build reads an external Danbooru/Raffle export and is skipped when that
  source is absent (e.g. in CI); the committed ``data/danbooru_vocab.txt`` snapshot
  is used instead, so the pipeline is CI-runnable with no network access.
- Candidates are validated automatically (structural rules + confidence, #119) and
  the resulting Knowledge Base is conflict-scanned (#120). On any rejection or
  conflict the pipeline writes a structured JSON log to stderr and exits non-zero
  **without writing** — it never prompts.
- The curated-wins additive merge is preserved end-to-end (candidates colliding
  with curated ids/aliases are rejected).

Usage:
    python scripts/build_knowledge_base.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.kb_autovalidate import validate_candidate  # noqa: E402
from compiler.common.kb_conflicts import detect_conflicts  # noqa: E402
from scripts import build_vocab  # noqa: E402
from scripts import generate_kb_from_vocab as gen  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KB_DIR = _REPO_ROOT / "knowledge_base"
_VOCAB = _REPO_ROOT / "data" / "danbooru_vocab.txt"
_GEN_PREFIX = "gen_"
_MANIFEST = "manifest.json"


def _source_vocab() -> set[str]:
    """The committed source-vocab tag set (candidate ids must be members)."""
    tags: set[str] = set()
    for line in _VOCAB.read_text(encoding="utf-8").splitlines():
        if line.strip():
            tags.add(line.split("\t", 1)[1].strip())
    return tags


def _curated() -> tuple[list[dict], set[str], set[str]]:
    """Return (curated entries, curated ids, curated aliases)."""
    entries: list[dict] = []
    ids: set[str] = set()
    aliases: set[str] = set()
    for path in sorted(_KB_DIR.glob("*.json")):
        if path.name.startswith(_GEN_PREFIX) or path.name == _MANIFEST:
            continue
        file_entries = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(file_entries)
        for entry in file_entries:
            ids.add(entry["id"])
            aliases.update(entry.get("aliases", ()))
    return entries, ids, aliases


def validate_candidates(
    by_category: dict[str, list[dict]],
    curated_ids: set[str],
    curated_aliases: set[str],
    source_vocab: set[str],
) -> list[dict]:
    """Auto-validate every candidate; return structured rejection records."""
    candidates = [entry for entries in by_category.values() for entry in entries]
    generated_ids = {entry["id"] for entry in candidates}
    known_ids = curated_ids | generated_ids
    rejections: list[dict] = []
    for entry in candidates:
        decision = validate_candidate(
            entry,
            curated_ids=curated_ids,
            curated_aliases=curated_aliases,
            known_ids=known_ids,
            source_vocab=source_vocab,
        )
        if not decision.accepted:
            rejections.append(
                {"id": entry.get("id"), "reasons": [m.description for m in decision.reasons]}
            )
    return rejections


def run_pipeline(write: bool = True) -> int:
    """Run the full pipeline. Return 0 on success, 1 on rejection/conflict."""
    if build_vocab._SOURCE.is_file():
        build_vocab.main()
    else:
        print(f"[pipeline] external vocab source absent; using committed {_VOCAB.name}")

    by_category = gen.build_generated_entries()
    curated_entries, curated_ids, curated_aliases = _curated()
    source_vocab = _source_vocab()

    rejections = validate_candidates(by_category, curated_ids, curated_aliases, source_vocab)
    candidates = [entry for entries in by_category.values() for entry in entries]
    report = detect_conflicts(curated_entries + candidates, curated_ids)

    if rejections or report.total:
        sys.stderr.write(
            json.dumps(
                {
                    "status": "failed",
                    "rejected_candidates": rejections,
                    "conflicts": report.to_json(),
                },
                indent=2,
            )
            + "\n"
        )
        return 1

    if write:
        counts = gen.write_generated(by_category)
        print(f"[pipeline] wrote {sum(counts.values())} generated entries; manifest stamped.")
    else:
        print(f"[pipeline] dry run OK: {len(candidates)} candidates, no conflicts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_pipeline())
