# ComfyUI Scene Compiler

**A deterministic prompt compiler for ComfyUI.**
Turn a plain-language scene description into a clean, valid Illustrious tag
prompt — without an LLM inventing anything.

> **Status:** Version 2 released (`v2.1.0`). The deterministic Version 1 pipeline
> shipped in v1.0.0 / v1.1.0. Full documentation lives in the [Wiki](../../wiki);
> see the [Roadmap](../../wiki/Roadmap) and [issues](../../issues) for what's next.

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
  → Scene Analyzer   → Scene JSON
  → Scene Validator  → Validated Scene JSON
  → Resolver         → Prompt
```

Only the **Scene Analyzer** uses an LLM, and only to understand language — never
to produce tags. Every generated tag is looked up in a data-only **Knowledge
Base** built from a real Danbooru tag vocabulary, so tags are always valid and
never invented. The Resolver both resolves concepts to tags and joins them into a
single flat prompt string, in resolution order. Every tag stays traceable:

```
Natural Language → Scene JSON → Knowledge Base Entry → Resolved Tag → Prompt
```

---

## What Version 2 changed

Version 1 proved the compiler works. Version 2 is about making it **know more and
ask less** — without giving up a single guarantee.

### Know more

The V1 compiler was honest but narrow: a concept missing from the Knowledge Base
was simply dropped, and the Knowledge Base only grew by hand.

- **The Knowledge Base grows itself.** A fully automated pipeline regenerates it
  from committed Danbooru snapshots — generate candidates, ingest aliases and
  implications, auto-validate, scan for conflicts, write. There is **no approval
  gate**: an automation that stops to ask a human is an automation that doesn't run.
- **Near-misses are caught, not dropped.** An **opt-in** semantic (nearest-neighbour)
  fallback resolves concepts that miss exact lookup. It is off by default,
  deterministic when enabled, and can only return an entry that *already exists* in
  the Knowledge Base — so it can never invent a tag. Deterministic lookup always wins.
- **Detail stops leaking.** The compiler used to silently discard parts of what you
  wrote. Now modifiers survive (`open white shirt` → `white shirt` **and**
  `open shirt`), every item of a list is transcribed, and relationships are kept
  rather than flattened to a noun (`money in her hand` → `holding money`, not just
  `money`). The same fidelity applies to explicit content — nothing is quietly
  softened or skipped.

### Ask less

V1 exposed almost every internal as a node or a widget. That is honest, but it
pushes the compiler's internal shape onto the user.

- **Configuration lives in one place.** All settings are on the **Configuration**
  node; the stage nodes take a single optional `config` connection. The analyzer
  model used to be set in two disconnected places — now it's set once.
- **Fewer nodes.** Stages that carried no real decisions were folded away: the
  Category Splitter and Prompt Builder collapsed into the Resolver (V1.1), and the
  Knowledge Base Loader collapsed into the Configuration node (V2.1). Eight nodes
  became five.
- **Don't ask what the system already knows.** The Knowledge Base ships inside the
  package, so its path is no longer a question. Options that aren't ready or aren't
  really user-facing (prompt target, separator, hand-written system prompts) are not
  exposed — they keep working defaults instead.
- **Plain language.** Every input has a tooltip written for a user, not for a compiler
  engineer.

### What did not change

Determinism. Every V2 addition is opt-in, bounded to the existing Knowledge Base,
and reproducible: the same Scene JSON, Knowledge Base, and configuration always
compile to the same prompt. Knowledge stays data, never code. Nothing is invented.

---

## Key principles

- **Determinism first** — a given Scene JSON + Knowledge Base + config always produces the same output, with no random seeds. (The one non-deterministic step is the LLM understanding the language up front; everything after it is reproducible.)
- **No hallucinations** — if it isn't in the description, it isn't in the output. Unknown concepts are reported, never guessed.
- **Knowledge is data** — every concept→tag mapping lives in the Knowledge Base, never in code.
- **Fidelity** — described detail must survive to the prompt, or be reported. Silence is a bug.
- **Traceability** — every tag can be explained back to the sentence it came from.
- **Automation without gates** — the pipeline runs end to end with zero required human input.
- **Nodes are interfaces** — ComfyUI nodes are thin wrappers; all logic lives in the compiler package, and settings live on one node.

Version 2 targets the **Illustrious** model family. The architecture is
model-independent, so future versions can add Pony, Flux, NoobAI, and others
without changing the compiler core.

---

## Nodes

Scene Compiler ships as a ComfyUI custom-node package of **five** nodes. It is a
toolbox, not a fixed workflow — every node can be used independently.

### Pipeline nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Scene Analyzer** | `natural_language`, `config` *(optional)* | `scene`, `warnings`, `errors`, `raw` |
| **Scene Validator** | `scene`, `config` *(optional)* | `scene`, `warnings`, `errors`, `raw` |
| **Resolver** | `scene`, `knowledge_base`, `config` *(optional)* | `prompt`, `warnings`, `errors`, `json` |

The Resolver is the final stage: it resolves concepts to Knowledge Base tags and
joins them into one flat `prompt` string. Its `json` output carries the traceable
resolved tags so a translation problem is inspectable.

### Support nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Configuration** | all compiler settings (see below) | `config`, `knowledge_base`, `warnings`, `errors` |
| **Debug Viewer** | `scene`, `warnings`, `errors` *(all optional)* | `report` |

- **Configuration** is the single place for compiler settings *and* the Knowledge
  Base loader: it reads the Knowledge Base that ships with the package and emits it
  on its `knowledge_base` output, which you wire into the Resolver. Bump its
  `knowledge_base_reload` counter after editing the Knowledge Base to re-read it.
- **Debug Viewer** is read-only; connect any intermediate state to inspect it.

A typical graph:

```
Configuration ─ config ──────────► Scene Analyzer / Scene Validator / Resolver
              └ knowledge_base ───► Resolver

Scene Analyzer → Scene Validator → Resolver → (your image workflow)
```

### Knowledge Base Editor (optional web tool)

Not a node. Version 2 adds an optional browser editor for curated Knowledge Base
entries, served by ComfyUI at `http://127.0.0.1:8188/scene-compiler/kb`. It offers
create/edit/delete with live validation and atomic, format-safe saves. It is the
*only* manual surface in the project and is entirely off the compile critical path —
the compiler never depends on it.

---

## Installation

> Install manually from Git today; a ComfyUI Manager listing is planned.

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

1. Add a **Configuration** node (it also loads the Knowledge Base).
2. Add a **Scene Analyzer** and type a description, e.g.
   *"A blonde girl wearing a white dress hugs a young man while walking in the rain."*
3. Wire **Scene Analyzer → Scene Validator → Resolver**, and connect Configuration's
   `config` to each stage and its `knowledge_base` to the Resolver.
4. Send the **Resolver**'s `prompt` output into your image-generation workflow
   (e.g. EasyIllustrious).
5. Drop a **Debug Viewer** on any connection to inspect the intermediate state.

A ready-made graph is in
[`examples/workflows/scene_compiler_pipeline.json`](examples/workflows/scene_compiler_pipeline.json).

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
- [Resolver & Prompt](../../wiki/Resolver-and-Prompt)
- [ComfyUI Nodes](../../wiki/ComfyUI-Nodes)
- [Configuration, Errors & Logging](../../wiki/Configuration-Errors-and-Logging)
- [Development, Testing & Contributing](../../wiki/Development-Testing-and-Contributing)
- [Roadmap](../../wiki/Roadmap)
- [Glossary & Reference](../../wiki/Glossary-and-Reference)

In-repo notes live in [`docs/`](docs/) — see [`docs/nodes.md`](docs/nodes.md) for the
node reference and [`docs/knowledge_base_build.md`](docs/knowledge_base_build.md) for
how the Knowledge Base is regenerated.

[`MASTER_SPEC.md`](MASTER_SPEC.md) is the full normative specification, maintained
through Version 2. Chapters superseded by later versions are marked in place rather
than deleted, so the original design intent stays readable.

---

## Roadmap

- **Version 1 — Deterministic Compiler Foundation** *(done — v1.0.0 / v1.1.0)*: the
  complete deterministic pipeline for Illustrious, plus Ollama integration, Knowledge
  Base, Debug Viewer, and regression tests.
- **Version 2 — Semantic Resolution** *(done — v2.0.0 / v2.1.0)*: opt-in
  semantic/embedding fallback, automatic Knowledge Base builder, Knowledge Base
  versioning and editor, concept fidelity, performance, and the node/configuration
  consolidation — determinism preserved. (Analyzer localization was dropped as
  unnecessary.)
- **Version 3 — Extensible Compiler Platform**: multi-model Resolvers, a plugin
  system, multiple Analyzer backends, and a standalone Compiler SDK.
- **Version 4 — Consolidation**: a single unified node that runs the whole pipeline,
  continuing the V2 consolidation. The granular nodes stay available for debugging.

See the [Roadmap](../../wiki/Roadmap) for details.

---

## Contributing

Contributions are welcome — especially Knowledge Base entries. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[Development, Testing & Contributing](../../wiki/Development-Testing-and-Contributing)
guide first. Core rule: **never hardcode knowledge, and never break determinism.**

## License

See [LICENSE](LICENSE).

---

## A note on AI assistance

This project — its code, tests, and documentation — is built with heavy help from
AI coding assistants, and is developed and maintained by a solo author. AI makes
mistakes: despite testing and review, parts of this project and its docs may be
inaccurate, out of date, or simply wrong. Please treat it as a good-faith best
effort rather than authoritative truth — **if the docs and the code disagree, the
code wins** — and open an issue when you spot something off.
