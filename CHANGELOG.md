# Changelog

All notable changes to Scene Compiler are documented here. The project follows
[Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.

## [1.1.0] — Flat prompt, no categories

A deliberate simplification of the pipeline's back half.

### Changed

- **The Resolver is now the translator from Scene JSON to prompt.** It resolves
  concepts to tags and joins them into a single flat prompt string, in resolution
  order (which naturally leads with character/appearance tags). The Resolver node
  outputs `prompt`, `warnings`, `errors`, and `json` (the traceable resolved tags,
  to inspect what the translation produced).

### Removed

- **Category Splitter and Prompt Builder stages and nodes** — categories are no
  longer part of the output; there is one prompt, not one output per category. The
  `CategoryMap` / `PromptOutput` models and schemas are removed. Node count is now
  six. The `category` field remains on Knowledge Base entries and resolved tags for
  traceability in the `json` output.

## [1.0.0] — Deterministic Compiler Foundation

The first release: a complete, deterministic natural-language-to-prompt compiler
for ComfyUI targeting the Illustrious model family.

### Compiler

- **Scene Analyzer** — the only LLM stage; turns a natural-language description
  into Scene JSON via a local Ollama backend and the official system prompt.
  Never generates tags or invents information. Robust to real local-model
  behaviour: JSON is extracted from surrounding prose, and bounded retries
  escalate the sampling temperature (prompt unchanged) so a malformed response can
  self-recover. The node also surfaces the raw model text for debugging.
- **Scene Validator** — validates and normalizes Scene JSON against the schema;
  recoverable issues warn and continue, hard errors stop.
- **Illustrious Resolver** — deterministically resolves concepts to Illustrious
  tags through the Knowledge Base: normalization, direct alias resolution,
  a head-noun fallback for compound concepts (`white summer dress` → `dress`),
  recursive expansion, and duplicate removal, with full traceability. NSFW-rated
  entries are gated behind an opt-in `include_nsfw` flag.
- **Category Splitter** — groups Resolved Tags into the 19 canonical categories,
  preserving order.
- **Prompt Builder** — formats the Category Map into one output per category plus
  reserved Negative and Scene outputs.

### Foundation

- JSON Schemas and immutable typed data models for every inter-stage document.
- Compiler Result wrapper and a stable message-code registry.
- Typed, injectable configuration and structured logging.
- Knowledge Base loader with validation tooling. Ships ~188 hand-curated entries
  (with aliases and expansions) plus ~16k entries generated from a real Danbooru
  tag vocabulary, merged additively so the curated entries always win. Entries
  carry a `rating` (general/explicit) for NSFW gating.

### ComfyUI

- Eight nodes: Scene Analyzer, Scene Validator, Resolver, Category Splitter,
  Prompt Builder, Debug Viewer, Knowledge Base Loader, and Configuration. Each
  stage node exposes a raw-debug output; the Configuration node exposes every
  option including the `include_nsfw` toggle.

### Quality

- Full unit, integration, golden, and performance test suites; deterministic
  golden outputs for ten reference scenes.
- CI on Python 3.11 and 3.12; documentation and ready-to-use examples.
