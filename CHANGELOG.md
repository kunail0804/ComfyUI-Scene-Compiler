# Changelog

All notable changes to Scene Compiler are documented here. The project follows
[Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.

## [1.0.0] — Deterministic Compiler Foundation

The first release: a complete, deterministic natural-language-to-prompt compiler
for ComfyUI targeting the Illustrious model family.

### Compiler

- **Scene Analyzer** — the only LLM stage; turns a natural-language description
  into Scene JSON via a local Ollama backend, with a bounded retry policy and the
  official system prompt. Never generates tags or invents information.
- **Scene Validator** — validates and normalizes Scene JSON against the schema;
  recoverable issues warn and continue, hard errors stop.
- **Illustrious Resolver** — deterministically resolves concepts to Illustrious
  tags through the Knowledge Base: normalization, direct alias resolution,
  recursive expansion, and duplicate removal, with full traceability.
- **Category Splitter** — groups Resolved Tags into the 19 canonical categories,
  preserving order.
- **Prompt Builder** — formats the Category Map into one output per category plus
  reserved Negative and Scene outputs.

### Foundation

- JSON Schemas and immutable typed data models for every inter-stage document.
- Compiler Result wrapper and a stable message-code registry.
- Typed, injectable configuration and structured logging.
- Knowledge Base loader with validation tooling and an initial Illustrious
  dataset (188 entries).

### ComfyUI

- Eight nodes: Scene Analyzer, Scene Validator, Resolver, Category Splitter,
  Prompt Builder, Debug Viewer, Knowledge Base Loader, and Configuration.

### Quality

- Full unit, integration, golden, and performance test suites; deterministic
  golden outputs for ten reference scenes.
- CI on Python 3.11 and 3.12; documentation and ready-to-use examples.
