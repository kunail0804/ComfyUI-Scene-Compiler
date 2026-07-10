"""Generate Knowledge Base entries from the embedded Danbooru vocabulary.

Reads ``data/danbooru_vocab.txt`` (``raffle_category<TAB>tag`` per line, produced
by ``build_vocab.py``) and writes ``knowledge_base/gen_<category>.json`` files.

The generation is ADDITIVE and non-destructive: the hand-curated Knowledge Base
files (everything under ``knowledge_base/`` NOT named ``gen_*.json``) are left
untouched and always win. A generated tag is skipped when its id already exists
as a hand-curated id or alias, so the curated canonicalization (``female`` +
aliases) and expansions (``school_uniform`` -> ``blazer``, ``pleated_skirt``)
are preserved while the vocabulary adds broad coverage on top.

Generated entries carry a ``rating`` (general/explicit) derived from the Raffle
category, so NSFW tags are gated behind ``resolver.include_nsfw``.

Usage:
    python scripts/generate_kb_from_vocab.py
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VOCAB = _REPO_ROOT / "data" / "danbooru_vocab.txt"
_KB_DIR = _REPO_ROOT / "knowledge_base"
_GEN_PREFIX = "gen_"

# Raffle category -> one of the 19 canonical SceneCompiler categories.
_CATEGORY_MAP = {
    "clothes_and_accessories": "clothing",
    "specific_garment_interactions": "clothing",
    "generic_clothing_interactions": "clothing",
    "named_garment_exposure": "clothing",
    "general_clothing_exposure": "clothing",
    "intentional_design_exposure": "clothing",
    "background_objects": "objects",
    "one_handed_character_items": "objects",
    "two_handed_character_items": "objects",
    "holding_small_items": "objects",
    "holding_large_items": "objects",
    "standard_physical_descriptors": "appearance",
    "female_physical_descriptors": "appearance",
    "male_physical_descriptors": "appearance",
    "sfw_clothed_anatomy": "body",
    "publicly_visible_anatomy": "body",
    "female_intimate_anatomy": "body",
    "male_intimate_anatomy": "body",
    "nudity_and_absence_of_clothing": "body",
    "bodily_fluids": "body",
    "actions": "action",
    "sex_acts": "action",
    "poses": "pose",
    "physical_locations": "environment",
    "thematic_settings": "environment",
    "special_backgrounds": "environment",
    "expressions_and_mental_state": "expression",
    "gaze_direction_and_eye_contact": "eyes",
    "lighting_and_vfx": "lighting",
    "camera_angle_perspective": "camera",
    "camera_focus_subject": "camera",
    "camera_framing_composition": "camera",
    "character_count": "character",
    "relationships": "interaction",
    "color_scheme": "style",
    "artstyle_technique": "style",
}

# Raffle categories whose tags are explicit (gated behind resolver.include_nsfw).
_EXPLICIT_CATEGORIES = frozenset(
    {
        "sex_acts",
        "bodily_fluids",
        "female_intimate_anatomy",
        "male_intimate_anatomy",
        "nudity_and_absence_of_clothing",
        "publicly_visible_anatomy",
        "named_garment_exposure",
        "general_clothing_exposure",
        "intentional_design_exposure",
    }
)


def _load_hand_reserved() -> set[str]:
    """Collect every id and alias from the hand-curated (non-generated) KB files."""
    reserved: set[str] = set()
    for path in sorted(_KB_DIR.glob("*.json")):
        if path.name.startswith(_GEN_PREFIX):
            continue
        for entry in json.loads(path.read_text(encoding="utf-8")):
            reserved.add(entry["id"])
            reserved.update(entry.get("aliases", ()))
    return reserved


def _read_vocab() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in _VOCAB.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        category, tag = line.split("\t", 1)
        pairs.append((category, tag))
    return pairs


def generate() -> dict[str, int]:
    reserved = _load_hand_reserved()
    by_category: dict[str, list[dict]] = {}
    skipped_reserved = skipped_unmapped = 0

    for raffle_category, tag in _read_vocab():
        sc_category = _CATEGORY_MAP.get(raffle_category)
        if sc_category is None:
            skipped_unmapped += 1
            continue
        if tag in reserved:
            skipped_reserved += 1
            continue
        entry = {
            "id": tag,
            "tags": [tag.replace("_", " ")],
            "category": sc_category,
        }
        if raffle_category in _EXPLICIT_CATEGORIES:
            entry["rating"] = "explicit"
        by_category.setdefault(sc_category, []).append(entry)

    # Remove any stale generated files before writing the fresh set.
    for path in _KB_DIR.glob(f"{_GEN_PREFIX}*.json"):
        path.unlink()

    counts: dict[str, int] = {}
    for sc_category, entries in sorted(by_category.items()):
        entries.sort(key=lambda e: e["id"])
        out = _KB_DIR / f"{_GEN_PREFIX}{sc_category}.json"
        out.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        counts[sc_category] = len(entries)

    total = sum(counts.values())
    print(f"generated {total} entries across {len(counts)} category files")
    print(f"  skipped {skipped_reserved} (already hand-curated), {skipped_unmapped} (unmapped)")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:6}  gen_{cat}.json")
    return counts


if __name__ == "__main__":
    generate()
