# Knowledge Base

The Knowledge Base is **data only** — no executable code (MASTER_SPEC §15). It is
the single source of truth for how semantic concepts map to Illustrious tags. The
compiler loads every file here once during initialization.

## File organization

Concepts are split into multiple JSON files **by domain**, for readability and
maintenance (§15.3). The compiler loads and merges all of them:

```
knowledge_base/
  appearance.json   clothing.json   anatomy.json   expressions.json
  poses.json        actions.json    interactions.json  objects.json
  environments.json camera.json     lighting.json   quality.json  style.json
```

Domain files are a maintenance convenience; a concept's **category** (below), not
the file it lives in, determines its behaviour.

## File format

Each file is a **JSON array of entries**:

```json
[
  { "id": "long_hair", "tags": ["long hair"], "category": "hair" },
  { "id": "blue_eyes", "tags": ["blue eyes"], "category": "eyes" }
]
```

A complete worked example (with an alias and an expansion) is in
[`examples/knowledge_base.example.json`](../examples/knowledge_base.example.json).

## Entry fields

Each entry validates against the `knowledge_base_entry` schema
([`schemas/json/knowledge_base_entry.schema.json`](../schemas/json/knowledge_base_entry.schema.json)).

| Field | Required | Rule |
|---|---|---|
| `id` | yes | Canonical ID: lowercase `snake_case`, **globally unique** across the whole Knowledge Base. |
| `tags` | yes | The Illustrious tags this concept generates. **At least one.** Order is preserved. |
| `category` | yes | Exactly one of the 19 canonical categories (see below). |
| `aliases` | no | Alternative expressions resolving **directly** to this entry (no alias→alias chains). **Globally unique**, and must not collide with any `id`. |
| `expand` | no | Additional canonical `id`s automatically added during resolution. References **canonical ids only**, never raw tags; targets must exist. |
| `deprecated` | no | Marks an obsolete concept; it keeps working but the compiler emits a warning. |
| `notes` | no | Free-form documentation for contributors; ignored during compilation. |

### Contributor rules

- **`id` uniqueness** — every canonical `id` is unique across all files.
- **`alias` uniqueness** — every alias is unique across all files and never equal
  to any `id`; aliases resolve directly to their entry (no chains).
- **Tag order** — the order of `tags` is significant and preserved in output.
- **Category** — must be one of the 19 categories; the authoritative set is
  defined once in `compiler/common/categories.py`.
- **Expansion** — `expand` lists canonical `id`s only; every target must exist.
- **At least one tag** — every entry generates one or more tags.

> Per-entry structure is enforced by the entry schema. Cross-entry rules (global
> uniqueness, expand targets exist, no alias chains) are enforced by the Knowledge
> Base validation tooling.

## The 19 categories

`character`, `appearance`, `hair`, `face`, `eyes`, `expression`, `body`,
`clothing`, `accessories`, `pose`, `action`, `interaction`, `objects`,
`environment`, `camera`, `lighting`, `style`, `quality`, `miscellaneous`.

`style` and `quality` are reserved for workflow integration (not generated
automatically in V1); `miscellaneous` is a fallback that should stay nearly empty.
