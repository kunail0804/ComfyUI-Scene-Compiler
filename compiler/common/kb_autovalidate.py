"""Automatic acceptance validator for generated Knowledge Base candidates (#119).

Per the epic #35 direction (**zero user input, no approval gate**), generated
candidate entries are accepted or rejected **automatically** — there is no
human-in-the-loop prompt. This module combines:

- **Structural rules** — reused from :mod:`compiler.common.kb_validation`
  (valid id pattern, known category, per-entry schema) plus cross-entry checks a
  candidate must satisfy against the existing dataset: no id/alias collision with
  curated entries, expansion targets exist, no self-cycle.
- **Confidence heuristics** — a deterministic score in ``[0, 1]``: a candidate
  must be a real source-vocab tag (no invention) and map to a known category. A
  candidate below :data:`DEFAULT_CONFIDENCE_THRESHOLD` is rejected.

A rejected candidate carries structured :class:`Message` reasons for logging; the
pipeline (#122) records them and never prompts.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any

from compiler.common.categories import is_valid_category
from compiler.common.kb_validation import validate_entry
from compiler.common.message_codes import message
from compiler.common.result import Message

# Weighting: source-vocab membership dominates (no invention), a known category
# completes the score. The default threshold requires source-vocab membership.
_VOCAB_WEIGHT = 0.7
_CATEGORY_WEIGHT = 0.3
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


@dataclass(frozen=True)
class CandidateDecision:
    """The automatic accept/reject outcome for one candidate entry."""

    entry: Mapping[str, Any]
    accepted: bool
    confidence: float
    reasons: list[Message] = field(default_factory=list)


def compute_confidence(entry: Mapping[str, Any], source_vocab: Collection[str]) -> float:
    """Deterministic confidence in ``[0, 1]`` for a candidate entry."""
    score = 0.0
    if entry.get("id") in source_vocab:
        score += _VOCAB_WEIGHT
    if is_valid_category(entry.get("category")):
        score += _CATEGORY_WEIGHT
    return round(score, 6)


def validate_candidate(
    entry: Mapping[str, Any],
    *,
    curated_ids: Collection[str],
    curated_aliases: Collection[str],
    known_ids: Collection[str],
    source_vocab: Collection[str],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> CandidateDecision:
    """Decide whether a generated candidate entry is auto-accepted.

    Args:
        entry: The candidate entry (parsed dict).
        curated_ids / curated_aliases: Ids/aliases owned by curated entries
            (curated always wins — a candidate colliding with them is rejected).
        known_ids: All canonical ids that will exist (curated + generated), used to
            check that expansion targets resolve.
        source_vocab: The committed source-vocab tag set; the candidate id must be
            a member (no invention).
        confidence_threshold: Minimum confidence to accept.
    """
    reasons: list[Message] = list(validate_entry(entry))
    entry_id = entry.get("id", "<unknown>")

    if entry_id in curated_ids:
        reasons.append(
            message(
                "SC0005",
                f"Candidate id '{entry_id}' collides with a curated entry (curated wins).",
                id=entry_id,
            )
        )
    for alias in entry.get("aliases", ()):
        if alias in curated_ids or alias in curated_aliases:
            reasons.append(
                message(
                    "SC0004",
                    f"Candidate alias '{alias}' collides with a curated id/alias.",
                    id=entry_id,
                    alias=alias,
                )
            )
    for target in entry.get("expand", ()):
        if target == entry_id:
            reasons.append(
                message(
                    "SC0003",
                    f"Candidate '{entry_id}' expands to itself.",
                    id=entry_id,
                )
            )
        elif target not in known_ids:
            reasons.append(
                message(
                    "SC0004",
                    f"Candidate '{entry_id}' expands to unknown id '{target}'.",
                    id=entry_id,
                    target=target,
                )
            )

    confidence = compute_confidence(entry, source_vocab)
    if confidence < confidence_threshold:
        reasons.append(
            message(
                "SC0022",
                (
                    f"Candidate '{entry_id}' rejected: confidence {confidence:.2f} is below "
                    f"threshold {confidence_threshold:.2f} (not a real source-vocab tag?)."
                ),
                id=entry_id,
                confidence=confidence,
                threshold=confidence_threshold,
            )
        )

    return CandidateDecision(
        entry=entry, accepted=not reasons, confidence=confidence, reasons=reasons
    )
