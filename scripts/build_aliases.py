"""Build the committed Danbooru alias/implication snapshots.

Danbooru publishes tag **aliases** (synonym → canonical, e.g. ``stockings`` →
``thighhighs``) and **implications** (a tag implies another, e.g. ``elbow_gloves``
implies ``gloves``). Ingesting them lets synonyms reach their canonical entry and
turns implications into Knowledge Base ``expand`` relations
(``scripts/generate_kb_from_vocab.py``).

Like ``build_vocab.py``, this is an occasional dev step, not part of runtime/CI.
It reads a Danbooru export from a hard-coded path (no CLI/untrusted input) and
writes two compact, deterministic, committed snapshots:

- ``data/danbooru_aliases.txt``      — ``alias<TAB>canonical_id`` per line
- ``data/danbooru_implications.txt`` — ``antecedent_id<TAB>consequent_id`` per line

Only rows whose names are valid Knowledge Base ids (lowercase alphanumerics joined
by single underscores) are kept, so no symbol/emoticon tag can enter the KB. The
generator consumes only these committed snapshots, never the external export, so
the repository stays self-contained and CI never needs network access.

Edit ``_ALIAS_SOURCE`` / ``_IMPLICATION_SOURCE`` to point at your local Danbooru
export (CSV with ``antecedent_name,consequent_name`` columns) before running.

Usage:
    python scripts/build_aliases.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ALIAS_SOURCE = Path("/home/kunail/Documents/AIStuff/danbooru/tag_aliases.csv")
_IMPLICATION_SOURCE = Path("/home/kunail/Documents/AIStuff/danbooru/tag_implications.csv")
_ALIAS_OUTPUT = _REPO_ROOT / "data" / "danbooru_aliases.txt"
_IMPLICATION_OUTPUT = _REPO_ROOT / "data" / "danbooru_implications.txt"

_ID_PATTERN = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


def _read_pairs(source: Path) -> list[tuple[str, str]]:
    """Return kept ``(antecedent, consequent)`` rows, sorted and deduplicated."""
    kept: dict[str, str] = {}  # antecedent -> consequent (first wins)
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            antecedent = (row.get("antecedent_name") or "").strip()
            consequent = (row.get("consequent_name") or "").strip()
            if not _ID_PATTERN.match(antecedent) or not _ID_PATTERN.match(consequent):
                continue
            if antecedent == consequent:
                continue
            kept.setdefault(antecedent, consequent)
    return sorted(kept.items())


def _write(pairs: list[tuple[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(f"{a}\t{b}\n" for a, b in pairs), encoding="utf-8")
    print(f"wrote {len(pairs)} rows to {output.relative_to(_REPO_ROOT)}")


def main() -> None:
    _write(_read_pairs(_ALIAS_SOURCE), _ALIAS_OUTPUT)
    _write(_read_pairs(_IMPLICATION_SOURCE), _IMPLICATION_OUTPUT)


if __name__ == "__main__":
    main()
