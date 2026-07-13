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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compiler.common.kb_manifest import write_manifest  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VOCAB = _REPO_ROOT / "data" / "danbooru_vocab.txt"
_ALIASES = _REPO_ROOT / "data" / "danbooru_aliases.txt"
_IMPLICATIONS = _REPO_ROOT / "data" / "danbooru_implications.txt"
_KB_DIR = _REPO_ROOT / "knowledge_base"
_GEN_PREFIX = "gen_"

# The dataset version stamped into the manifest on each rebuild. Bump this when a
# regeneration changes the dataset in a way workflows should be able to pin.
_DATASET_VERSION = "1.0.0"

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
        if path.name.startswith(_GEN_PREFIX) or path.name == "manifest.json":
            continue
        for entry in json.loads(path.read_text(encoding="utf-8")):
            reserved.add(entry["id"])
            reserved.update(entry.get("aliases", ()))
    return reserved


def _load_curated_ids() -> set[str]:
    """Canonical ids from the hand-curated files (valid expansion targets)."""
    ids: set[str] = set()
    for path in sorted(_KB_DIR.glob("*.json")):
        if path.name.startswith(_GEN_PREFIX) or path.name == "manifest.json":
            continue
        for entry in json.loads(path.read_text(encoding="utf-8")):
            ids.add(entry["id"])
    return ids


def _read_tsv_pairs(path: Path) -> list[tuple[str, str]]:
    """Read ``a<TAB>b`` lines (deterministic order); empty when the file is absent."""
    if not path.is_file():
        return []
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        left, right = line.split("\t", 1)
        pairs.append((left.strip(), right.strip()))
    return pairs


def _load_aliases_by_canonical() -> dict[str, list[str]]:
    """Danbooru aliases grouped by canonical id: ``canonical -> [alias, ...]``."""
    by_canonical: dict[str, list[str]] = {}
    for alias, canonical in _read_tsv_pairs(_ALIASES):
        by_canonical.setdefault(canonical, []).append(alias)
    return by_canonical


def _load_implications() -> dict[str, list[str]]:
    """Danbooru implications grouped by antecedent: ``antecedent -> [consequent, ...]``."""
    by_antecedent: dict[str, list[str]] = {}
    for antecedent, consequent in _read_tsv_pairs(_IMPLICATIONS):
        by_antecedent.setdefault(antecedent, []).append(consequent)
    return by_antecedent


def _read_vocab() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in _VOCAB.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        category, tag = line.split("\t", 1)
        pairs.append((category, tag))
    return pairs


def _ingest_aliases_and_implications(
    by_category: dict[str, list[dict]],
    reserved: set[str],
    curated_ids: set[str],
) -> None:
    """Attach Danbooru aliases/implications to the generated entries (issue #118).

    - Aliases whose canonical is a generated entry are attached to it, so synonyms
      resolve (``tights`` → ``pantyhose``). Aliases colliding with a curated
      id/alias or any generated id are skipped (curated always wins; no chains).
    - Implications whose antecedent is a generated entry become ``expand`` targets
      when the consequent exists (curated id or generated id). This is additive and
      deterministic; nothing is invented (data comes only from the committed
      Danbooru snapshots). Aliases whose canonical is a *curated* entry are owned by
      the curated files and left untouched here.
    """
    generated_ids = {entry["id"] for entries in by_category.values() for entry in entries}
    known_targets = curated_ids | generated_ids
    aliases_by_canonical = _load_aliases_by_canonical()
    implications = _load_implications()

    for entries in by_category.values():
        for entry in entries:
            entry_id = entry["id"]

            new_aliases = sorted(
                alias
                for alias in aliases_by_canonical.get(entry_id, ())
                if alias not in reserved and alias not in generated_ids and alias != entry_id
            )
            if new_aliases:
                entry["aliases"] = new_aliases

            new_expand = sorted(
                target
                for target in implications.get(entry_id, ())
                if target in known_targets and target != entry_id
            )
            if new_expand:
                entry["expand"] = new_expand


def build_generated_entries() -> dict[str, list[dict]]:
    """Build the generated entries (with alias/implication ingestion), sorted.

    Pure and side-effect-free: it reads the committed snapshots and returns the
    ``category -> [entry, ...]`` mapping without touching disk, so the pipeline
    (#122) can validate the candidates before anything is written.
    """
    reserved = _load_hand_reserved()
    by_category: dict[str, list[dict]] = {}

    for raffle_category, tag in _read_vocab():
        sc_category = _CATEGORY_MAP.get(raffle_category)
        if sc_category is None or tag in reserved:
            continue
        entry = {
            "id": tag,
            "tags": [tag.replace("_", " ")],
            "category": sc_category,
        }
        if raffle_category in _EXPLICIT_CATEGORIES:
            entry["rating"] = "explicit"
        by_category.setdefault(sc_category, []).append(entry)

    _ingest_aliases_and_implications(by_category, reserved, _load_curated_ids())
    for entries in by_category.values():
        entries.sort(key=lambda e: e["id"])
    return by_category


def write_generated(by_category: dict[str, list[dict]]) -> dict[str, int]:
    """Write the generated entry files and stamp the manifest deterministically."""
    # Remove any stale generated files before writing the fresh set.
    for path in _KB_DIR.glob(f"{_GEN_PREFIX}*.json"):
        path.unlink()

    counts: dict[str, int] = {}
    for sc_category, entries in sorted(by_category.items()):
        out = _KB_DIR / f"{_GEN_PREFIX}{sc_category}.json"
        out.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        counts[sc_category] = len(entries)

    write_manifest(_KB_DIR, _DATASET_VERSION, _VOCAB)
    return counts


def generate() -> dict[str, int]:
    by_category = build_generated_entries()
    counts = write_generated(by_category)
    total = sum(counts.values())
    print(f"generated {total} entries across {len(counts)} category files")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:6}  gen_{cat}.json")
    return counts


if __name__ == "__main__":
    generate()
