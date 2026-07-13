"""Tests for the deterministic offline embedding backend (issue #114, epic #34)."""

from __future__ import annotations

import pytest

from compiler.common.embedding import (
    CharNGramEmbeddingBackend,
    cosine_similarity,
    get_backend,
)


def test_embedding_is_deterministic() -> None:
    backend = CharNGramEmbeddingBackend()
    assert backend.embed(["thighhighs"]) == backend.embed(["thighhighs"])


def test_vectors_are_l2_normalized() -> None:
    (vector,) = CharNGramEmbeddingBackend().embed(["blue eyes"])
    magnitude = sum(weight * weight for weight in vector.values())
    assert magnitude == pytest.approx(1.0)


def test_identical_text_has_self_similarity_one() -> None:
    (vector,) = CharNGramEmbeddingBackend().embed(["long hair"])
    assert cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_similar_text_scores_higher_than_dissimilar() -> None:
    backend = CharNGramEmbeddingBackend()
    (thighhighs,) = backend.embed(["thighhighs"])
    (thigh_highs,) = backend.embed(["thigh highs"])
    (unrelated,) = backend.embed(["castle"])
    assert cosine_similarity(thighhighs, thigh_highs) > cosine_similarity(thighhighs, unrelated)


def test_normalization_ignores_case_and_underscores() -> None:
    backend = CharNGramEmbeddingBackend()
    assert backend.embed(["Long_Hair"]) == backend.embed(["long hair"])


def test_empty_text_yields_empty_vector() -> None:
    assert CharNGramEmbeddingBackend().embed([""]) == [{}]
    assert cosine_similarity({}, {"abc": 1.0}) == pytest.approx(0.0)


def test_get_backend_returns_default_and_rejects_unknown() -> None:
    assert isinstance(get_backend("char_ngram"), CharNGramEmbeddingBackend)
    with pytest.raises(ValueError):
        get_backend("nope")
