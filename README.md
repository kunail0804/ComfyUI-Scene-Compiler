# ComfyUI Scene Compiler

**A deterministic prompt compiler for ComfyUI.**
Turn a plain-language scene description into structured, category-separated
Illustrious tags — without an LLM inventing anything.

> **Status:** Version 1 in development. This repository is spec-driven; the
> full design is documented in [`MASTER_SPEC.md`](../MASTER_SPEC.md) and in the
> [Wiki](../../wiki). Follow the [Roadmap](../../wiki/Roadmap) and
> [issues](../../issues) for progress.

---

## The idea

Most prompt-generation workflows ask a language model to write Danbooru tags
directly:

```
Natural Language → LLM → Prompt
```

LLMs are bad at this. They invent clothing, poses, lighting, and environments
that were never described, emit invalid tags, and return different output for
identical input. Scene Compiler takes a different position:

> **The language model understands the scene. The compiler generates the prompt.**

Prompt generation is treated as a **compilation** problem, not a text-generation
problem. Language understanding happens once, up front; everything after it is
deterministic and traceable.

```
Natural Language
  → Scene Analyzer      → Scene JSON
  → Scene Validator     → Validated Scene JSON
  → Resolver            → Resolved Tags
  → Category Splitter   → Category Map
  → Prompt Builder      → Prompt Outputs
```

Only the **Scene Analyzer** uses an LLM, and only to understand language — never
to produce tags. Every generated tag is looked up deterministically in a
data-only **Knowledge Base** and stays fully traceable:

```
Natural Language → Scene JSON → Knowledge Base Entry → Resolved Tag → Prompt Output
```

---

## Key principles

- **Determinism first** — same input + Knowledge Base + config → same output, always. No random seeds anywhere.
- **No hallucinations** — if it isn't in the description, it isn't in the output. Unknown concepts are reported, never guessed.
- **Knowledge is data** — every concept→tag mapping lives in the Knowledge Base, never in code.
- **Traceability** — every tag can be explained back to the sentence it came from.
- **Separation of concerns** — each stage does exactly one job and can be tested on its own.
- **Nodes are interfaces** — ComfyUI nodes are thin wrappers; all logic lives in the compiler package.

Version 1 targets the **Illustrious** model family only. The architecture is
model-independent so future versions can add Pony, Flux, NoobAI, and others
without changing the compiler core.

---

## Nodes

Scene Compiler ships as a ComfyUI custom-node package. It is a toolbox, not a
fixed workflow — every node can be used independently.

### Pipeline nodes

| Node | Input | Output |
|---|---|---|
| **Scene Analyzer** | Natural language, model, temperature, timeout | Scene JSON |
| **Scene Validator** | Scene JSON | Validated Scene JSON |
| **Resolver** | Scene JSON, Knowledge Base | Resolved Tags |
| **Category Splitter** | Resolved Tags | Category Map |
| **Prompt Builder** | Category Map | One string per category (+ reserved Negative / Scene) |

### Support nodes

- **Debug Viewer** — inspect any intermediate state (Scene JSON, Resolved Tags, categories, warnings, errors).
- **Knowledge Base Loader** — load the active Knowledge Base, with manual reload for development.
- **Configuration Node** — centralize compiler settings without editing workflows.

---

## Installation

> Not yet released. These are the intended install steps for Version 1.

**Via ComfyUI Manager** (recommended once published): search for *Scene Compiler*.

**Manual:**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/kunail0804/ComfyUI-Scene-Compiler.git
```

Then restart ComfyUI. The Scene Analyzer requires a local [Ollama](https://ollama.com)
instance for language understanding; the rest of the pipeline runs fully offline.

---

## Quick start

1. Add a **Scene Analyzer** node and type a description, e.g.
   *"A blonde girl wearing a white dress hugs a young man while walking in the rain."*
2. Connect **Scene Analyzer → Scene Validator → Resolver → Category Splitter → Prompt Builder**.
3. Wire the **Prompt Builder** category outputs into your image-generation
   workflow (e.g. EasyIllustrious).
4. Use the **Debug Viewer** on any connection to inspect the intermediate state.

Given the example above, the compiler extracts `female`, `blonde hair`,
`white dress`, `male`, the interaction `hug`, and environment `rain` — and
nothing else. It does not add eye colour, quality tags, or lighting that were
never described.

---

## Documentation

Full documentation lives in the **[Wiki](../../wiki)**:

- [Overview & Vision](../../wiki/Overview-and-Vision)
- [Architecture & Pipeline](../../wiki/Architecture-and-Pipeline)
- [Data Model](../../wiki/Data-Model)
- [Scene JSON & Schemas](../../wiki/Scene-JSON-and-Schemas)
- [Scene Analyzer](../../wiki/Scene-Analyzer)
- [Knowledge Base](../../wiki/Knowledge-Base)
- [Resolver, Categories & Prompt Builder](../../wiki/Resolver-Categories-and-Prompt-Builder)
- [ComfyUI Nodes](../../wiki/ComfyUI-Nodes)
- [Configuration, Errors & Logging](../../wiki/Configuration-Errors-and-Logging)
- [Development, Testing & Contributing](../../wiki/Development-Testing-and-Contributing)
- [Roadmap](../../wiki/Roadmap)
- [Glossary & Reference](../../wiki/Glossary-and-Reference)

The complete normative specification is [`MASTER_SPEC.md`](../MASTER_SPEC.md).

---

## Roadmap

- **Version 1 — Deterministic Compiler Foundation** *(in progress)*: the complete
  deterministic pipeline for Illustrious, plus Ollama integration, Knowledge Base,
  Debug Viewer, and regression tests.
- **Version 2 — Semantic Resolution**: Knowledge Base editor, semantic/embedding
  fallback search, localization, performance — determinism preserved.
- **Version 3 — Extensible Compiler Platform**: multi-model Resolvers, a plugin
  system, multiple Analyzer backends, and a standalone Compiler SDK.

See the [Roadmap](../../wiki/Roadmap) for details.

---

## Contributing

Contributions are welcome — especially Knowledge Base entries. Please read the
[Development, Testing & Contributing](../../wiki/Development-Testing-and-Contributing)
guide first. Core rule: **never hardcode knowledge, and never break determinism.**

## License

See [LICENSE](LICENSE).
