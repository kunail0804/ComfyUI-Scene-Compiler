"""Build the committed Knowledge Base embedding index (issue #115, epic #34).

Embeds each Knowledge Base entry's surface forms (canonical id, tags, aliases)
with the deterministic offline backend and writes the index snapshot to
``data/kb_embedding_index.json``. The snapshot maps vectors back to existing entry
ids only, so the semantic fallback can never invent a tag. It is committed so CI
never recomputes embeddings.

Paths are hard-coded constants (no CLI/untrusted input) matching the style of
``scripts/build_vocab.py`` (SonarCloud S8707).

Usage:
    python scripts/build_embedding_index.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.embedding_index import build_index_rows  # noqa: E402
from compiler.common.knowledge_base import load_knowledge_base  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_KB_DIR = _REPO_ROOT / "knowledge_base"
_OUTPUT = _REPO_ROOT / "data" / "kb_embedding_index.json"


def build() -> int:
    kb = load_knowledge_base(_KB_DIR)
    rows = build_index_rows(kb)
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {len(rows)} index rows for {len(kb)} entries to {_OUTPUT.relative_to(_REPO_ROOT)}"
    )
    return len(rows)


if __name__ == "__main__":
    build()
