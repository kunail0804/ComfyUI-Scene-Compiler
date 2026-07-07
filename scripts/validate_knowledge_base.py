"""CLI to validate a Knowledge Base directory (issue #9).

Loads every ``*.json`` file under the given directory (each a JSON array of
entries), validates the whole Knowledge Base, and writes the findings as JSON to
stdout. Exit code is 0 when the Knowledge Base is valid, 1 otherwise.

Usage:
    python scripts/validate_knowledge_base.py knowledge_base/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running directly (python scripts/validate_knowledge_base.py) without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.kb_validation import validate_knowledge_base  # noqa: E402
from compiler.common.result import Message, Severity  # noqa: E402


def load_entries(directory: Path) -> tuple[list[dict], list[Message]]:
    """Load all entries from ``*.json`` files; return (entries, load_errors)."""
    entries: list[dict] = []
    errors: list[Message] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(
                Message(
                    code="SC0004",
                    severity=Severity.FATAL,
                    title="Invalid JSON",
                    description=f"{path.name}: {exc}",
                    context={"id": path.name},
                )
            )
            continue
        if isinstance(data, list):
            entries.extend(data)
        else:
            errors.append(
                Message(
                    code="SC0004",
                    severity=Severity.FATAL,
                    title="Invalid Knowledge Base file",
                    description=f"{path.name}: expected a JSON array of entries.",
                    context={"id": path.name},
                )
            )
    return entries, errors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write("usage: validate_knowledge_base.py <knowledge_base_dir>\n")
        return 2
    directory = Path(argv[0])
    if not directory.is_dir():
        sys.stderr.write(f"not a directory: {directory}\n")
        return 2

    entries, findings = load_entries(directory)
    findings = findings + validate_knowledge_base(entries)

    report = {
        "valid": not findings,
        "entry_count": len(entries),
        "findings": [m.to_json() for m in findings],
    }
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
