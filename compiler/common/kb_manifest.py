"""Knowledge Base dataset manifest (MASTER_SPEC §30.2, epic #36).

A Knowledge Base directory may ship a ``manifest.json`` that pins the dataset's
``version`` so a workflow can select and reproduce a specific Knowledge Base
build. The manifest is *data about the dataset*, not an entry file, so the loader
skips it when reading entries.

The manifest is deterministic: its ``content_hash`` is a stable digest of every
entry file (sorted by name), and ``source_vocab`` is the digest of the committed
Danbooru vocabulary snapshot the generated entries came from. Regenerating an
unchanged Knowledge Base therefore produces a byte-identical manifest — there is
no wall-clock build date. A directory without a manifest defaults to the implicit
``v1`` version so existing installs keep loading unchanged.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = "manifest.json"

# The manifest document's own schema version (bumped if the manifest shape
# changes), distinct from the dataset ``version`` it records.
MANIFEST_SCHEMA_VERSION = "1.0"

# The version assumed when a Knowledge Base ships no manifest (backward compat).
IMPLICIT_VERSION = "1.0.0"


@dataclass(frozen=True)
class KnowledgeBaseManifest:
    """The parsed manifest of a Knowledge Base dataset."""

    version: str
    content_hash: str
    source_vocab: str | None = None
    entry_schema_version: str | None = None
    manifest_schema_version: str = MANIFEST_SCHEMA_VERSION

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "manifest_schema_version": self.manifest_schema_version,
            "version": self.version,
            "content_hash": self.content_hash,
        }
        if self.source_vocab is not None:
            result["source_vocab"] = self.source_vocab
        if self.entry_schema_version is not None:
            result["entry_schema_version"] = self.entry_schema_version
        return result


def _entry_files(directory: Path) -> list[Path]:
    """Every Knowledge Base entry file (``*.json`` except the manifest), sorted."""
    return [p for p in sorted(directory.glob("*.json")) if p.name != MANIFEST_FILENAME]


def compute_content_hash(directory: str | Path) -> str:
    """Return a deterministic ``sha256:`` digest of all entry files in a directory.

    The digest covers each entry file's name and raw bytes in sorted order, so it
    is stable across runs and changes only when an entry file's content changes.
    """
    directory = Path(directory)
    digest = hashlib.sha256()
    for path in _entry_files(directory):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def build_manifest(
    directory: str | Path, version: str, source_vocab_path: str | Path
) -> KnowledgeBaseManifest:
    """Build a manifest for a directory, hashing its entries and the source vocab."""
    directory = Path(directory)
    return KnowledgeBaseManifest(
        version=version,
        content_hash=compute_content_hash(directory),
        source_vocab=_hash_file(Path(source_vocab_path)),
    )


def write_manifest(
    directory: str | Path, version: str, source_vocab_path: str | Path
) -> KnowledgeBaseManifest:
    """Stamp ``manifest.json`` into ``directory`` deterministically and return it."""
    directory = Path(directory)
    manifest = build_manifest(directory, version, source_vocab_path)
    path = directory / MANIFEST_FILENAME
    path.write_text(
        json.dumps(manifest.to_json(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_manifest(directory: str | Path) -> KnowledgeBaseManifest:
    """Load the manifest of a Knowledge Base directory.

    A missing manifest yields the implicit ``v1`` version (with the content hash
    computed on the fly), so a directory without a manifest still reports a
    coherent version and loads unchanged.
    """
    directory = Path(directory)
    path = directory / MANIFEST_FILENAME
    if not path.is_file():
        return KnowledgeBaseManifest(
            version=IMPLICIT_VERSION,
            content_hash=compute_content_hash(directory),
            source_vocab=None,
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return KnowledgeBaseManifest(
        version=data["version"],
        content_hash=data["content_hash"],
        source_vocab=data.get("source_vocab"),
        entry_schema_version=data.get("entry_schema_version"),
        manifest_schema_version=data.get("manifest_schema_version", MANIFEST_SCHEMA_VERSION),
    )
