# Rebuilding the Knowledge Base

The generated Knowledge Base is produced by a single, fully-automated pipeline
with **zero human input** (epic #35). It regenerates the `gen_*.json` files and the
`manifest.json` deterministically from the committed source snapshots under
`data/`.

## One command

```bash
python scripts/build_knowledge_base.py
```

The pipeline runs:

1. **build vocab** (dev-only) — rebuilds `data/danbooru_vocab.txt` from an external
   Danbooru/Raffle export. Skipped automatically when that source is absent (e.g.
   in CI), so the committed snapshot is used and no network access is needed.
2. **generate candidates** from the vocab snapshot.
3. **ingest aliases/implications** from `data/danbooru_aliases.txt` and
   `data/danbooru_implications.txt` (synonyms → canonical aliases, implications →
   `expand`).
4. **auto-validate** every candidate (structural rules reused from
   `compiler/common/kb_validation.py` + a confidence heuristic — no approval gate).
5. **conflict-scan** the whole Knowledge Base (duplicate ids/aliases, ambiguous tag
   ownership, contradictory expansions).
6. **write** `gen_*.json` and stamp `manifest.json` — only if steps 4–5 are clean.

On any rejected candidate or detected conflict the pipeline writes a structured
JSON log to stderr and exits non-zero **without writing** — it never prompts. The
curated-wins additive merge is preserved end-to-end: a candidate colliding with a
curated id/alias is rejected.

## Source snapshots (committed)

| File | Built by | Contents |
|---|---|---|
| `data/danbooru_vocab.txt` | `scripts/build_vocab.py` | `raffle_category<TAB>tag` |
| `data/danbooru_aliases.txt` | `scripts/build_aliases.py` | `alias<TAB>canonical_id` |
| `data/danbooru_implications.txt` | `scripts/build_aliases.py` | `antecedent_id<TAB>consequent_id` |

The `build_*` scripts read an external export from a hard-coded path (edit the
constant before running) and are occasional dev steps, not part of runtime or CI.

## Related tools

- `python scripts/build_embedding_index.py` — rebuild the committed semantic-fallback embedding index (`data/kb_embedding_index.json`) from the current KB.
- `python scripts/detect_kb_conflicts.py knowledge_base/` — standalone conflict scan (CI-gateable).
- `python scripts/coverage_benchmark.py` — Knowledge Base coverage report.
- `python scripts/validate_knowledge_base.py knowledge_base/` — full KB validation.
