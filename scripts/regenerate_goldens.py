"""Deliberately regenerate the golden prompt outputs (issue #28).

Run this only when a change is *intended* to alter compiler output (e.g. a
Knowledge Base or formatting change). It compiles every reference scene against
the shipped Knowledge Base and overwrites the golden files under
``tests/regression/golden/``.

Usage:
    python scripts/regenerate_goldens.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.regression.golden_scenes import (  # noqa: E402
    GOLDEN_DIR,
    SCENES,
    compile_prompt_outputs,
    load_reference_knowledge_base,
)


def main() -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    knowledge_base = load_reference_knowledge_base()
    for name, scene in SCENES.items():
        outputs = compile_prompt_outputs(scene, knowledge_base)
        path = GOLDEN_DIR / f"{name}.json"
        path.write_text(json.dumps(outputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sys.stdout.write(f"wrote {path.relative_to(GOLDEN_DIR.parent.parent.parent)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
