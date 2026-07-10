"""Build the embedded Danbooru vocabulary snapshot from the Raffle tag dump.

This is a one-time / occasional dev step, not part of the runtime or CI. It reads
the Raffle node's ``categorized_tags.txt`` (each line ``[raffle_category] tag``),
drops attribution/identity categories that carry no scene meaning, drops tags
whose name cannot be a Knowledge Base id, and writes a compact, deterministic
snapshot to ``data/danbooru_vocab.txt`` (``raffle_category<TAB>tag`` per line).

The snapshot is committed so the repository is self-contained: the KB generator
(``generate_kb_from_vocab.py``) consumes only the snapshot, never the external
Raffle path.

The source path is a hard-coded constant (no CLI/untrusted input): edit
``_SOURCE`` below to point at your local Raffle checkout before running.

Usage:
    python scripts/build_vocab.py
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SOURCE = Path(
    "/home/kunail/Documents/AIStuff/ComfyUI/custom_nodes/raffle/lists/categorized_tags.txt"
)
_OUTPUT = _REPO_ROOT / "data" / "danbooru_vocab.txt"

# Raffle categories that carry no scene concept (artists, character/series names,
# attribution, metadata, raw symbols, censorship) — excluded entirely so the
# resolver can never inject an identity or attribution the user did not ask for.
_EXCLUDED_CATEGORIES = frozenset(
    {
        "artist",
        "character_name",
        "copyright",
        "metadata_and_attribution",
        "meta",
        "speech_and_text",
        "format_and_presentation",
        "abstract_symbols",
        "content_censorship_methods",
    }
)

# Subjective / opinion tags the analyzer is instructed to ignore (§ system prompt);
# the Knowledge Base must not offer them either, matching the curated dataset's
# "no subjective concepts" guarantee.
_BANNED_SUBJECTIVE = frozenset(
    {
        "beautiful",
        "cute",
        "pretty",
        "sexy",
        "gorgeous",
        "handsome",
        "hot",
        "ugly",
        "cool",
        "adorable",
        "lovely",
        "elegant",
        "epic",
    }
)

# A tag can only become a Knowledge Base id if it matches the id pattern
# (lowercase alphanumerics joined by single underscores). This drops emoticon and
# symbol tags (":d", ">_<", "^_^", tags with parentheses/apostrophes).
_ID_PATTERN = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line.startswith("["):
        return None
    close = line.find("]")
    if close == -1:
        return None
    category = line[1:close]
    tag = line[close + 1 :].strip()
    if not tag:
        return None
    return category, tag


def build_vocab(source: Path) -> list[tuple[str, str]]:
    """Return the kept ``(raffle_category, tag)`` pairs, sorted deterministically."""
    kept: dict[str, str] = {}  # tag -> category (first occurrence wins)
    for raw in source.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_line(raw)
        if parsed is None:
            continue
        category, tag = parsed
        if category in _EXCLUDED_CATEGORIES:
            continue
        if tag in _BANNED_SUBJECTIVE:
            continue
        if not _ID_PATTERN.match(tag):
            continue
        kept.setdefault(tag, category)
    return sorted((cat, tag) for tag, cat in kept.items())


def main() -> None:
    pairs = build_vocab(_SOURCE)
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text("".join(f"{cat}\t{tag}\n" for cat, tag in pairs), encoding="utf-8")
    print(f"wrote {len(pairs)} tags to {_OUTPUT.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
