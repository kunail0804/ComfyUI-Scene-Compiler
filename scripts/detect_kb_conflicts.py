"""CLI to scan a Knowledge Base for duplicates and conflicts (issue #120).

Loads every entry file under a Knowledge Base directory (curated ids are taken
from the non-``gen_*`` files so curated-wins semantics are respected), runs the
conflict detector, writes a machine-readable JSON report to stdout, and prints a
one-line human summary to stderr. Exit code is 0 when the Knowledge Base is clean,
1 when any conflict is found — so it can serve as a CI gate.

Usage:
    python scripts/detect_kb_conflicts.py knowledge_base/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.kb_conflicts import detect_conflicts  # noqa: E402

_GEN_PREFIX = "gen_"
_MANIFEST = "manifest.json"


def _load(directory: Path) -> tuple[list[dict], set[str]]:
    """Return (all entries, curated ids) from a Knowledge Base directory."""
    entries: list[dict] = []
    curated_ids: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        if path.name == _MANIFEST:
            continue
        file_entries = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(file_entries)
        if not path.name.startswith(_GEN_PREFIX):
            curated_ids.update(e["id"] for e in file_entries if isinstance(e.get("id"), str))
    return entries, curated_ids


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: detect_kb_conflicts.py <knowledge_base_dir>\n")
        return 2
    directory = Path(argv[0])
    if not directory.is_dir():
        sys.stderr.write(f"not a directory: {directory}\n")
        return 2

    entries, curated_ids = _load(directory)
    report = detect_conflicts(entries, curated_ids)
    sys.stdout.write(json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n")
    sys.stderr.write(f"{report.total} conflict(s) found across {len(entries)} entries.\n")
    return 0 if report.total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
