# Scene Compiler — Master Specification

**Version:** 2 (V2) — covers releases `v1.0.0` … `v2.1.0`
**Status:** Maintained
**Authors:** Project Owner (design authority); drafted with AI assistance.
**Primary audience:** AI software-engineering agents and human contributors implementing Scene Compiler.

---

## Document Status & Version History

This specification was originally written for Version 1 and has been **updated
through Version 2**. It describes the compiler as it ships today.

Later versions removed some stages the original design defined. Rather than delete
those chapters — which would break every cross-reference and erase the design
rationale — they are **kept in place and marked**:

> **⚠️ Superseded** blocks state what replaced the chapter and where the current
> normative text lives.

Chapter and section numbers are therefore **stable**: `§17`, `§20`, `§23`, and
Appendix B mean the same thing they always did, and the wiki's `§` references
remain valid.

| Version | Released | Change of record |
|---|---|---|
| **V1** | `v1.0.0` | The deterministic five-stage compiler as specified in Part III–IV. |
| **V1.1** | `v1.1.0` | The **Category Splitter** ([Ch 18](#18-categories--category-splitter)) and **Prompt Builder** ([Ch 19](#19-prompt-builder--outputs)) were removed as separate stages. The Resolver ([Ch 17](#17-resolver)) now resolves *and* emits one flat prompt. Categories survive as traceability metadata only. |
| **V2.0** | `v2.0.0` | Semantic Resolution: automatic Knowledge Base growth, an opt-in Knowledge-Base-bounded semantic fallback, Knowledge Base versioning and editor, concept fidelity, performance. New codes `SC0019`–`SC0022`. |
| **V2.1** | `v2.1.0` | Node and configuration consolidation: the **Knowledge Base Loader** node folded into the **Configuration** node, and the Configuration surface trimmed to what a user should set. Eight nodes became five ([Ch 20](#20-comfyui-nodes)). |

**Precedence.** Where this document and the shipped code disagree, the code wins and
this document is a bug. Report it.

---

## Document Conventions

This specification defines **behaviour**, not implementation. Any implementation that satisfies the stated behaviour is compliant.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used in the RFC 2119 sense:

- **MUST / MUST NOT** — an absolute requirement or prohibition.
- **SHOULD / SHOULD NOT** — a strong recommendation; deviation requires justification.
- **MAY** — an optional behaviour.

When a requirement and a convenience conflict, the requirement wins. When ambiguity remains, deterministic behaviour MUST be preferred over intelligent behaviour.

Diagrams are shown in fenced blocks. Data structures are shown as JSON. Concept names in running text are written in `code` style. Canonical vocabulary is defined once in the [Glossary](#appendix-a--glossary) and used consistently thereafter.

---

## Table of Contents

**Part I — Overview & Rationale**
1. Introduction
2. Scope & Non-Goals
3. Design Principles
4. Audience & Conventions

**Part II — Requirements**
5. Functional Requirements
6. Non-Functional Requirements
7. Success Criteria & Definition of Done

**Part III — Architecture**
8. Compilation Pipeline
9. Data Model
10. Scene JSON Grammar
11. JSON Schemas

**Part IV — Components**
12. Scene Analyzer
13. Official Analyzer Prompt
14. Scene Validator
15. Knowledge Base
16. Knowledge Base Construction Guide
17. Resolver
18. Categories & Category Splitter *(splitter removed in V1.1; category list still normative)*
19. Prompt Builder & Outputs *(stage removed in V1.1; see §19.7 for the current flat prompt)*
20. ComfyUI Nodes

**Part V — Cross-Cutting Concerns**
21. Error & Warning Handling
22. Logging & Debugging
23. Configuration

**Part VI — Engineering & Process**
24. Repository Structure
25. Coding Guidelines
26. Testing Strategy
27. Guidelines for AI Engineering Agents
28. Versioning Strategy

**Part VII — Roadmap**
29. Recommended Development Order
30. Long-Term Roadmap

**Appendices**
- A. Glossary
- B. Error & Warning Codes
- C. Category Reference

---

# Part I — Overview & Rationale

# 1. Introduction

## 1.1 Purpose

Scene Compiler is a deterministic prompt compiler for ComfyUI. It transforms a natural-language scene description into a structured prompt compatible with Danbooru-format image-generation models. Version 1 targets the **Illustrious** model family exclusively, while the architecture is designed to support additional model families in future versions without structural change.

## 1.2 Problem Statement

Current prompt-generation workflows rely on a Large Language Model (LLM) to generate Danbooru tags directly:

```
Natural Language → LLM → Prompt
```

This approach is unsuitable for deterministic generation. LLMs routinely invent scene elements that were never described (clothing, poses, lighting, environments), emit invalid tags, produce inconsistent prompts, and return different outputs for identical inputs. Tools such as TIPO reduce but do not eliminate this, because they still delegate tag generation to the language model.

Scene Compiler takes a fundamentally different position: **the language model understands the scene; the compiler generates the prompt.**

## 1.3 Vision

Scene Compiler treats prompt generation as a **compilation** problem rather than a text-generation problem. It receives a natural-language description, extracts explicit semantic information, converts that information into an intermediate representation, resolves every concept against a deterministic Knowledge Base, and only then produces Illustrious tags.

The compiler therefore keeps two problems completely independent:

- **Language understanding** — performed once, by the Scene Analyzer.
- **Prompt generation** — performed deterministically, by the remaining pipeline.

Version 1 is a foundation. Future versions extend the compiler; they do not replace it.

---

# 2. Scope & Non-Goals

## 2.1 In Scope

- Natural-language analysis and scene extraction.
- Scene JSON generation (the Intermediate Representation).
- Deterministic tag resolution against the Knowledge Base.
- Scene validation.
- Category assignment, as traceability metadata on entries and resolved tags.
- Flat prompt translation (performed by the Resolver — see the V1.1 note in [§19](#19-prompt-builder--outputs)).
- EasyIllustrious integration (via connectable outputs).
- Ollama integration (as the default Analyzer backend).

**Added in V2:**

- Automatic Knowledge Base growth from a committed tag vocabulary, with no approval gate ([§3.14](#314-automation-without-gates-added-in-v2), [§15](#15-knowledge-base)).
- An **opt-in** semantic (nearest-neighbour) fallback for concepts that miss deterministic lookup, bounded to entries that already exist in the Knowledge Base ([§17](#17-resolver)).
- Knowledge Base versioning and an optional, off-critical-path Knowledge Base Editor.
- Concept fidelity: modifier preservation, full list transcription, and relational concepts ([§3.13](#313-fidelity-added-in-v2)).

## 2.2 Out of Scope

The following are intentionally excluded. They are **non-goals**, not missing features, and MUST NOT be added:

- Automatic creativity, prompt optimization, enhancement, or beautification.
- Style invention or artist selection/recommendation.
- Automatic generation of camera, lighting, environment, composition, or quality information.
- Automatic character completion (inventing hair, eyes, clothing, accessories, expressions, poses, or relationships).

**Governing rule:** if information is not explicitly present in the scene description, the compiler MUST NOT invent it.

## 2.3 Non-Goals (stated explicitly)

These limitations are intentional design boundaries:

- **The compiler is not a prompt generator.** It compiles semantic information into structured outputs. Prompt optimization belongs to downstream workflows.
- **The compiler is not an AI artist.** It does not improve, beautify, or make artistic decisions about scenes.
- **The compiler does not hallucinate.** Missing information stays missing; unknown concepts stay unknown.
- **The compiler does not replace EasyIllustrious.** EasyIllustrious remains responsible for prompt optimization, workflow organization, and image generation. The compiler provides structured semantic outputs only.
- **The compiler does not replace the user.** It never changes the user's intention; an incomplete description yields an incomplete output.
- **No automatic prompt engineering.** The compiler never injects tags such as `masterpiece`, `best quality`, `detailed`, `high resolution`, `professional lighting`, or `cinematic`.
- **No style decisions.** The compiler never decides whether an image is anime, realistic, painterly, illustration, or photorealistic.
- **No image-model knowledge.** The compiler understands semantic concepts, not diffusion models. It targets Illustrious solely through the Resolver.

Every proposed addition MUST be evaluated against the [Design Principles](#3-design-principles) before implementation.

---

# 3. Design Principles

These principles define the identity of the project. They are mandatory; every contribution MUST respect them.

## 3.1 Determinism First
Given identical input, Knowledge Base, and configuration, the compiler MUST always produce identical output. No randomness is permitted anywhere in the compiler. Random seeds MUST NOT exist.

## 3.2 Analyze Before Resolving
Natural language is first converted into semantic concepts (Scene JSON); concepts are then resolved into tags. The compiler MUST NOT skip this intermediate representation.

## 3.3 Explicit Over Implicit
Only explicitly described information may appear in Scene JSON. Implicit assumptions are forbidden.

## 3.4 No Hallucinations
When information is missing, the compiler MUST preserve uncertainty rather than invent detail. Generating fewer tags is preferable to generating incorrect tags. Unknown concepts MUST be reported, never guessed.

## 3.5 Traceability
Every generated tag MUST be explainable and traceable along the full chain:

```
Natural Language → Scene JSON → Knowledge Base Entry → Resolved Tag → Prompt Output
```

## 3.6 Separation of Concerns
Every compiler stage has exactly one responsibility. Responsibilities MUST NOT overlap, and no stage MAY perform the work of another. The project favours modularity over compactness.

## 3.7 Immutable Pipeline
Each stage receives immutable input and produces new immutable output. No stage modifies a previous representation.

## 3.8 Knowledge Is Data
Knowledge belongs in the Knowledge Base, never in source code. The Knowledge Base is the single source of truth for every supported concept, alias, tag, and category. Hardcoded mappings are forbidden. Compiler behaviour and compiler knowledge MUST remain independent.

## 3.9 The Resolver Owns Model Knowledge
The Resolver is the only component permitted to translate concepts into model-specific (Illustrious) tags. The language model MUST NOT generate tags of any format.

## 3.10 Nodes Are Interfaces
ComfyUI nodes expose functionality; they MUST NOT contain compiler logic. Business logic lives in the compiler package.

## 3.11 Human Readability
Knowledge Base entries and intermediate representations MUST remain understandable without reading source code. Readable data is maintainable data.

## 3.12 Simplicity & Long-Term Stability
Simple deterministic rules are preferred over complex heuristics. Scene JSON is the compiler's stable public interface; future versions SHOULD preserve compatibility whenever practical.

## 3.13 Fidelity *(added in V2)*
Information the user explicitly described MUST reach the prompt or be reported. Silently discarding part of a concept is a defect, not tidiness: dropped modifiers, omitted list items, and flattened relationships MUST be preserved or warned about. This principle applies identically to explicit/NSFW input — content MUST NOT be abbreviated, softened, or skipped on grounds of subject matter.

This principle constrains [§17](#17-resolver) (modifier preservation) and [§12](#12-scene-analyzer)–[§13](#13-official-analyzer-prompt) (full list transcription, relational concepts).

## 3.14 Automation Without Gates *(added in V2)*
Anything the compiler can determine for itself, it MUST do unattended. Approval gates, manual validation steps, and interactive prompts are anti-patterns: an automation that stops to ask a human is an automation that does not run. Generated Knowledge Base entries are therefore accepted by rules, heuristics, and confidence — never by manual review ([§15](#15-knowledge-base)).

The Knowledge Base Editor is the single permitted manual surface, and it MUST remain optional and off the compile critical path.

## 3.15 Ask Only What Matters *(added in V2)*
Configuration MUST live in one place, and the user MUST NOT be asked for anything the system already knows or is not ready to expose. A node exists to move data, not to display a setting — a refinement of [§3.10](#310-nodes-are-interfaces).

Concretely: the Knowledge Base path is fixed because the Knowledge Base ships with the package; reserved or non-user-facing options keep working defaults instead of appearing as widgets; and stage nodes take a single optional `config` connection rather than their own copies of a setting ([§20](#20-comfyui-nodes), [§23](#23-configuration)).

---

# 4. Audience & Conventions

This specification is written primarily for AI software-engineering agents (such as Claude Code) and for human contributors. Every architectural decision SHOULD be interpreted literally.

- Implementation choices MAY vary. Behaviour MAY NOT.
- When ambiguity exists, deterministic behaviour MUST be preferred over intelligent behaviour.
- When uncertain, an implementation MUST emit a warning rather than an assumption.

RFC keyword conventions and formatting conventions are defined in [Document Conventions](#document-conventions) above.

---

# Part II — Requirements

# 5. Functional Requirements

This chapter defines the functional requirements of Version 1. Requirements describe expected behaviour and are implementation-independent.

## FR-001 — Natural Language Input
The compiler MUST accept a natural-language description as its primary input, and MUST NOT require the user to write Danbooru tags manually.

Example input:
```
A blonde girl holds her boyfriend's hand while walking in the rain.
```

## FR-002 — Scene Understanding
The compiler MUST extract explicit semantic information from the input, including (where explicitly present): characters, appearance, clothing, interactions, environment, objects, camera, and lighting. Camera and lighting MUST be extracted only if explicitly mentioned.

## FR-003 — Intermediate Representation
The compiler MUST convert every scene into a Scene JSON document. Every downstream module MUST consume Scene JSON. No module other than the Scene Analyzer MAY consume natural language directly.

## FR-004 — Deterministic Resolution
Every semantic concept MUST be resolved through the Resolver, using the Knowledge Base. No AI model MAY generate Illustrious tags.

## FR-005 — Scene & Tag Validation
Scene JSON MUST be validated before resolution (see [Scene Validator](#14-scene-validator)). Resolved tags MUST satisfy existence, duplicate-freedom, alias resolution, and category consistency before being joined into the prompt.

## FR-006 — Category Separation
The compiler MUST organize tags into the semantic categories defined in [Chapter 18](#18-categories--category-splitter).

## FR-007 — Prompt Generation
The compiler MUST assemble the validated resolved tags into the flat prompt string expected by downstream ComfyUI nodes, and MUST NOT modify the tags themselves. *(Originally the Prompt Builder's responsibility; performed by the Resolver since V1.1 — see [§19.7](#197-current-behaviour-flat-prompt).)*

## FR-008 — Error Reporting
The compiler MUST report every detected problem. Warnings MUST NOT silently disappear. Example: an unknown concept produces a warning and is then ignored, not guessed.

## FR-009 — Traceability
Every generated tag MUST be traceable back to the original sentence, the Scene JSON concept, and the Resolver rule (Knowledge Base Entry).

## FR-010 — Repeatability
Given identical input, Knowledge Base, and configuration, the compiler MUST always produce identical output.

## Expected User Workflow

```
Natural Language → Scene Compiler → Structured Prompt → EasyIllustrious → Image Generation
```

The user SHOULD never need to rewrite prompts manually, but remains free to edit generated prompts afterwards. Scene Compiler does not replace artistic iteration; it automates deterministic translation.

---

# 6. Non-Functional Requirements

Non-functional requirements describe quality constraints — how the compiler behaves, rather than what it does.

## NFR-001 — Determinism
Determinism is the highest priority. No randomness is permitted inside the compiler.

## NFR-002 — Explainability
Every compiler decision MUST be explainable. The compiler MUST NOT produce unexplained output.

```
gold hair → alias → blonde hair → Knowledge Base Entry `blonde_hair`
```

## NFR-003 — Modularity
Every stage MUST be replaceable without modifying unrelated stages. Replacing the Ollama Analyzer with another Analyzer MUST NOT require changes inside the Resolver.

## NFR-004 — Performance
The compiler SHOULD prioritize responsiveness. Most compilation time is expected to be spent in the Scene Analyzer; the remaining pipeline SHOULD remain lightweight.

## NFR-005 — Maintainability
Knowledge MUST NOT be hardcoded; every mapping belongs in the Knowledge Base. The codebase SHOULD avoid special cases.

## NFR-006 — Testability
Every module MUST be independently testable. Resolver tests MUST NOT require Ollama; Validator tests MUST NOT require the Scene Analyzer; node tests MUST NOT require a running ComfyUI.

## NFR-007 — Debuggability
Every intermediate representation MUST be inspectable (Scene JSON, Resolver output, validation output, final categories).

## NFR-008 — Extensibility
The architecture MUST allow future Resolver implementations (Illustrious, Pony, Flux, NoobAI, …) without modifying the compiler core.

## NFR-009 — Offline Support
The compiler SHOULD operate locally with no required internet connection. External APIs MUST remain optional.

## NFR-010 — Compatibility
The compiler MUST integrate naturally into existing ComfyUI workflows without forcing users to redesign their pipelines.

---

# 7. Success Criteria & Definition of Done

## 7.1 Functional Criteria
Version 1 is successful when the compiler:

- Accepts a natural-language description.
- Produces a valid Scene JSON document.
- Resolves semantic concepts into valid Illustrious tags.
- Organizes generated tags into semantic categories.
- Exposes workflow-ready string outputs.
- Integrates with ComfyUI through custom nodes.

## 7.2 Determinism
Given the same natural-language input, Knowledge Base, compiler version, and Analyzer configuration, the compiler MUST always produce identical outputs.

## 7.3 No Hallucinations
The compiler MUST never invent information. Every generated concept MUST originate from the user's description; every generated tag MUST originate from the Knowledge Base.

## 7.4 Traceability
Every generated tag MUST have a complete traceability chain (Natural Language → Scene JSON → Knowledge Base Entry → Resolved Tag → Prompt Output). No tag MAY exist without one.

## 7.5 Integrity Requirements
- **Knowledge Base:** validates successfully (unique canonical IDs, unique aliases, known categories, valid expansions, no circular dependencies, valid JSON).
- **Scene JSON:** every document validates against the official schema; invalid Scene JSON MUST NOT continue through the compiler.
- **Resolver:** every Illustrious tag originates from a Knowledge Base Entry; no tag is hardcoded or generated manually.
- **Pipeline:** every stage has exactly one responsibility; no stage performs another stage's work.
- **ComfyUI:** all functionality is accessible through nodes that remain lightweight wrappers around compiler logic.

## 7.6 Documentation & Testing
The project MUST ship with: README, Wiki, architecture documentation, Knowledge Base documentation, example workflows, contribution guide, and developer documentation; and automated tests covering the Knowledge Base, Scene Validator, Resolver, the ComfyUI nodes, the full pipeline, and regression tests.

## 7.7 Performance & Extensibility
The Knowledge Base MUST be initialized once and reused across compilations without reloading. Future versions MUST be able to introduce new Knowledge Bases, Resolvers, Analyzers, and image models without modifying Scene JSON.

## 7.8 Definition of Done
Version 1 is complete when:

- ✓ Natural language is successfully analyzed.
- ✓ Scene JSON validates successfully.
- ✓ Concepts resolve correctly.
- ✓ Illustrious tags are generated.
- ✓ Tags are categorized.
- ✓ Prompt outputs are generated.
- ✓ All automated tests pass.
- ✓ Documentation is complete.
- ✓ Example workflows execute successfully without modification.
- ✓ No mandatory feature depends on prompt generation.
- ✓ No compiler stage performs semantic hallucination.

At this point Scene Compiler is considered production-ready for Version 1.

---

# Part III — Architecture

# 8. Compilation Pipeline

The compiler is a sequence of independent, deterministic transformations. Each stage receives immutable input and produces new immutable output; no stage modifies a previous representation.

## 8.1 Pipeline Overview

```
Natural Language
  → Scene Analyzer      → Scene JSON
  → Scene Validator     → Validated Scene JSON
  → Resolver            → Prompt
```

Each stage produces a new representation of the same scene. The representations are named consistently throughout this specification; where a stage boundary matters, "Raw Scene JSON" (Analyzer output) and "Validated Scene JSON" (Scene Validator output) are distinguished, otherwise both are referred to as Scene JSON.

> **Changed in V1.1.** The pipeline was originally five stages, ending
> `Resolver → Category Splitter → Prompt Builder`. The last two were removed; the
> Resolver now produces the final flat prompt directly. Stages 4 and 5 below are
> retained as historical record.

## 8.2 Global Compilation Algorithm

The following reference algorithm defines behaviour; implementations MAY differ internally.

```
function Compile(input):
    scene    = Analyze(input)          # Natural Language → Scene JSON
    scene    = ValidateScene(scene)    # schema + normalization
    prompt   = Resolve(scene)          # concepts → tags (+ dedup) → flat prompt
    return prompt
```

## 8.3 Stages

Each stage below lists its input, output, allowed operations, and forbidden operations. Full behaviour is specified in the corresponding component chapter.

### Stage 1 — Scene Analyzer ([Ch 12](#12-scene-analyzer))
- **Input:** natural language (string).
- **Output:** Scene JSON.
- **Allowed:** extract explicit concepts, create Scene JSON, preserve ambiguity.
- **Forbidden:** generate tags, optimize prompts, guess missing information.

Reference extraction order (deterministic): characters → environment → objects → interactions → camera → lighting. Every extraction MUST obey explicit-information-only, never guess, never expand.

### Stage 2 — Scene Validator ([Ch 14](#14-scene-validator))
- **Input:** Scene JSON.
- **Output:** Validated Scene JSON.
- **Allowed:** validate against schema, normalize values, remove invalid fields, report warnings.
- **Forbidden:** create concepts, guess concepts, generate tags.

### Stage 3 — Resolver ([Ch 17](#17-resolver)) — *final stage*
- **Input:** Validated Scene JSON, plus the Knowledge Base.
- **Output:** a flat `prompt` string (plus the Resolved Tags as `json` for inspection).
- **Allowed:** normalize, resolve aliases, look up canonical concepts, expand concepts, generate Illustrious tags, preserve dropped modifiers, remove duplicate tags, join the tags into one prompt, emit warnings. Optionally (V2) consult the semantic fallback.
- **Forbidden:** analyze language, invent concepts or tags, optimize prompts, call an LLM.

### Stage 4 — Category Splitter *(removed in V1.1 — historical)*
- **Input:** Resolved Tags. **Output:** Category Map.
- Assigned tags to output categories and preserved ordering. Removed: categories are now traceability metadata only ([Ch 18](#18-categories--category-splitter)).

### Stage 5 — Prompt Builder *(removed in V1.1 — historical)*
- **Input:** Category Map. **Output:** named Prompt Outputs.
- Concatenated tags into one string per category. Removed: the Resolver emits a single flat prompt ([§19.7](#197-current-behaviour-flat-prompt)).

## 8.4 Pipeline Invariants

The following MUST always hold:

- Each representation exists only within its window: natural language before the Analyzer; Scene JSON before the Resolver; Resolved Tags and the flat prompt after it.
- Each stage has exactly one responsibility.
- No stage MAY bypass another stage.
- Every stage MUST be independently testable.

## 8.5 Immutability & Data Ownership

Each stage owns only its output and MUST treat each transformation as immutable:

```
Input → Transform → Output   (Input remains unchanged)
```

Stages MUST NOT modify the outputs of previous stages.

## 8.6 Compiler Result Wrapper

Every compiler stage returns the same wrapper object, exposing debugging information while preserving a uniform interface:

```json
{
  "data": {},
  "warnings": [],
  "errors": [],
  "metadata": {}
}
```

## 8.7 Traceability

Every output element MUST be traceable back through:

```
Natural Language → Scene JSON → Knowledge Base Entry → Resolved Tag → Prompt Output
```

## 8.8 Compiler Guarantees & Failure Policy

At every stage the compiler guarantees valid input, valid output, deterministic behaviour, explicit warnings, and no silent failures.

Failure policy:

- Compilation SHOULD continue whenever possible.
- **Warnings** never stop compilation.
- **Errors** stop the affected compilation.
- **Fatal** conditions stop the compiler entirely (see [Ch 21](#21-error--warning-handling)).

---

# 9. Data Model

This chapter defines the internal data model manipulated by the compiler. These models are independent from JSON serialization, from ComfyUI, and from the implementation language. Their serialized form is defined in [Chapter 10 (Scene JSON Grammar)](#10-scene-json-grammar) and [Chapter 11 (JSON Schemas)](#11-json-schemas).

Design constraints — every model MUST be: human-readable, JSON-serializable, versionable, immutable once produced, deterministic, and self-descriptive. Additional fields are permitted only if explicitly documented; removing or changing an existing field is a breaking change.

## 9.1 Scene

The Scene is the root object. It contains every semantic element extracted from the user's description.

```
Scene
├── characters    (array)
├── interactions  (array)
├── objects       (array)
├── environment   (array of concepts)
├── camera        (array of concepts)
├── lighting      (array of concepts)
└── metadata      (object)
```

## 9.2 Character

A Character represents one independent subject (human, creature, or identifiable subject). Each field contains **semantic concepts**, never Illustrious tags.

```
Character
├── id           (integer — index of this character within characters[])
├── identity     (array of concepts)   # what the character is
├── appearance   (array of concepts)   # permanent physical traits
├── clothing     (array of concepts)   # wearable items
├── accessories  (array of concepts)   # removable items
├── pose         (array of concepts)   # static body position
├── expression   (array of concepts)   # facial emotion
└── actions      (array of concepts)   # independent actions
```

- **id** — an integer equal to the character's position in `characters[]` (0-based). It is the identifier referenced by `interactions[].participants`.
- **identity** — describes what the character is (`female`, `male`, `child`, `cat`, `dragon`, `robot`); it never describes appearance.
- **appearance** — permanent physical characteristics (hair, eyes, body, skin, ears, tail, horns, wings).
- **clothing** — wearable items (dress, shirt, pants, shoes, hat, gloves, cape, armor).
- **accessories** — removable items (necklace, glasses, earrings, backpack, watch, sword, shield, book, flower).
- **pose** — static body posture (standing, sitting, kneeling, lying, jumping).
- **expression** — facial emotion (smile, sad, angry, surprised, crying, laughing, blushing).
- **actions** — independent actions a character performs (reading, eating, sleeping, writing, pointing, drinking, drawing). Actions MUST NOT describe interactions.

Only `id` is required; every other field MAY be an empty array. Unknown information is omitted, never invented.

## 9.3 Concept

A Concept is the smallest semantic unit handled by the compiler. Within Scene JSON section arrays, a concept entry MAY take either form:

- **String form:** `"female"`.
- **Object form (optional confidence):** `{ "name": "female", "confidence": 0.98 }`.

The full internal model is:

```
Concept
├── name       (string — required)
├── category   (string — optional until validation)
├── source     (string — optional; origin sentence/field)
└── metadata   (object — optional; e.g. confidence)
```

Concepts are resolved later by the Resolver; they are never Illustrious tags. **Confidence is metadata only and MUST NOT influence deterministic compilation.**

## 9.4 Interaction

An Interaction represents a relationship between two or more characters. Interactions belong to the scene, never to an individual character.

```
Interaction
├── participants  (array of Character id)
└── concept       (string — the interaction, e.g. "holding hands")
```

Rules: `participants` MUST reference existing Character `id` values; participant order SHOULD remain stable.

## 9.5 Object

An Object represents an independent scene element. Objects MAY optionally reference an owning character, but ownership is not required in Version 1. An object entry contains semantic concepts describing the object (and MAY carry attributes such as colour).

## 9.6 Environment, Camera, Lighting

Each is an array of semantic concepts:

- **Environment** — the location and global scene conditions (forest, classroom, beach; rain, sunset, spring).
- **Camera** — how the scene is viewed (close-up, wide shot, low angle). Present only when explicitly described.
- **Lighting** — light conditions (sunset, moonlight, studio lighting, backlighting). Present only when explicitly described.

## 9.7 Metadata

Metadata contains compiler information such as language, Analyzer version, compiler version, timestamp, schema version, and warnings. **Metadata MUST NOT affect compilation.**

## 9.8 Resolved Tag

A Resolved Tag represents a generated Illustrious tag. Resolved Tags are immutable and MUST remain traceable to their origin.

```
Resolved Tag
├── tag                   (string — the Illustrious tag)
├── category              (string)
├── source_concept        (string — the originating concept)
└── knowledge_base_entry  (Canonical ID of the source entry)
```

## 9.9 Category Map

> **⚠️ Superseded.** The Category Map no longer exists. It was produced by the removed
> Category Splitter and consumed by the removed Prompt Builder ([Ch 18](#18-categories--category-splitter), [Ch 19](#19-prompt-builder--outputs)).
> The Resolver emits a flat prompt directly.

It mapped each category to an ordered array of Resolved Tags:

```
Category Map
{ "<category>": [ ResolvedTag, ... ], ... }
```

## 9.10 Prompt Output

Since V1.1 the compiler produces exactly **one** prompt output: a flat UTF-8 string of comma-separated tags in resolution order ([§19.7](#197-current-behaviour-flat-prompt)). The Resolver additionally serializes the Resolved Tags as `json` for inspection.

The original per-category, named form is retained below for historical reference:

```
Prompt Output   (removed in V1.1)
├── name   (string)
└── value  (UTF-8 string)
```

Prompt Outputs are the final compiler product.

## 9.11 Versioning

Every model supports explicit versioning via a schema version identifier (see [Ch 11](#11-json-schemas)). Breaking changes increment the major version; backward-compatible additions increment the minor version.

---

# 10. Scene JSON Grammar

Scene JSON is the compiler's Intermediate Representation (IR). This chapter defines its semantic grammar — which concepts may exist and where. It does not define how concepts are resolved. Every Scene JSON document MUST conform to this grammar and to the [Scene Schema](#111-scene-schema).

## 10.1 Root Structure

A Scene always contains the following top-level sections. All sections MUST exist; empty sections are represented by empty arrays (and `metadata` by an object).

```
Scene
├── characters    (0..N)
├── interactions  (0..N)
├── objects       (0..N)
├── environment   (0..N concepts)
├── camera        (0..N concepts)
├── lighting      (0..N concepts)
└── metadata
```

## 10.2 Character Grammar

Characters represent every human, creature, or identifiable subject. Each character is independent; character order reflects discovery order within the description. Every character follows the structure defined in [§9.2](#92-character): `identity`, `appearance`, `clothing`, `accessories`, `pose`, `expression`, `actions`. Every field contains semantic concepts, never tags.

The semantic role of each field is defined in [§9.2](#92-character) and is authoritative for placement decisions.

## 10.3 Interactions

Interactions describe relationships between two or more characters (holding hands, hugging, kissing, shaking hands, looking at each other, fighting, dancing together). An interaction MUST belong to the scene, never to an individual character, and follows the structure in [§9.4](#94-interaction).

## 10.4 Environment, Objects, Camera, Lighting

- **Environment** — the location (forest, bedroom, classroom, beach, castle, street, office, park, sky, ocean).
- **Objects** — independent scene elements (chair, table, tree, car, sword, book, umbrella, computer, window, lamp). Objects are not owned by characters unless explicitly stated.
- **Camera** — how the scene is viewed (close-up, wide shot, low/high angle, dutch angle, profile/front/back view). Only explicitly described camera information appears.
- **Lighting** — light conditions (sunset, moonlight, studio lighting, backlighting, soft lighting, candlelight, neon lighting). Only explicit lighting appears.

## 10.5 Metadata

Metadata contains compiler information (language, Analyzer version, timestamp, schema version, warnings) and MUST NOT affect compilation. See [§9.7](#97-metadata).

## 10.6 Cardinality

`characters`, `interactions`, `objects`, `environment`, `camera`, and `lighting` each have cardinality `0..N`.

## 10.7 Ordering

Ordering is preserved. Concepts appear in the order they are discovered in the description. The compiler MUST NOT reorder semantic concepts.

## 10.8 Unknown Concepts

Unknown concepts are permitted in Scene JSON. They remain as plain concepts; they MUST NOT be removed or replaced. Later stages MAY emit warnings.

## 10.9 Grammar Constraints

A concept belongs to exactly one location. For example, `smile` belongs to `expression` (not `actions`); `walking` belongs to `actions` (not `pose`). The Analyzer MUST place concepts according to their semantic meaning. The mapping from Scene sections to output categories is defined in [Appendix C](#appendix-c--category-reference).

## 10.10 Extensibility

Future versions MAY introduce new sections. Existing sections SHOULD remain backward compatible, and future additions MUST NOT change the meaning of existing sections.

---

# 11. JSON Schemas

Every JSON document exchanged between compiler modules MUST conform to an official JSON Schema. Schemas exist to guarantee interoperability, provide documentation, and enable tooling. No module SHOULD depend on implementation-specific objects; every module communicates through schemas.

## 11.0 Required Schemas

Schemas are defined for: Scene, Character, Concept, Interaction, Metadata, Knowledge Base Entry, Resolved Tag, Configuration, and — added in V2 — **Knowledge Base Manifest**. Every JSON exchanged between stages MUST validate against its schema; invalid JSON MUST NOT continue through the pipeline.

> **Changed in V1.1.** The **Category Map** and **Prompt Output** schemas were retired with the stages that used them ([§11.8](#118-category-map-schema), [§11.9](#119-prompt-output-schema)).

## 11.1 Scene Schema

Root object with required fields `characters`, `interactions`, `objects`, `environment`, `camera`, `lighting`, `metadata`. All fields are required; collections MAY be empty.

## 11.2 Character Schema

Fields `id`, `identity`, `appearance`, `clothing`, `accessories`, `pose`, `expression`, `actions`. `id` is an integer; every concept field is an array (of strings or Concept objects — see [§9.3](#93-concept)); empty arrays are allowed.

## 11.3 Concept Schema

Fields `name` (mandatory), `category` (optional until validation), `source` (optional metadata), and optional `metadata` (e.g. `confidence`). A concept MAY be serialized as a bare string, which is equivalent to `{ "name": <string> }`.

## 11.4 Interaction Schema

Fields `participants` (array of Character `id`) and `concept` (string).

## 11.5 Metadata Schema

Fields `schema_version`, `compiler_version`, `language`, `warnings`. Metadata never affects semantic meaning.

## 11.6 Knowledge Base Entry Schema

Fields `id`, `aliases`, `tags`, `category`, `expand`, `deprecated`, `notes` (see [Ch 15](#15-knowledge-base)). Every field is explicitly defined.

## 11.7 Resolved Tag Schema

Fields `tag`, `category`, `source_concept`, `knowledge_base_entry`. This schema enables complete traceability.

## 11.8 Category Map Schema

> **⚠️ Removed in V1.1.** Retired with the Category Splitter.

Mapped each category to an array of Resolved Tags.

## 11.9 Prompt Output Schema

> **⚠️ Removed in V1.1.** Retired with the Prompt Builder: the prompt is now a single plain string, not a named object.

Fields `name` and `value`.

## 11.12 Knowledge Base Manifest Schema *(V2)*

A Knowledge Base directory MAY ship a `manifest.json` describing the dataset: its `version`, a deterministic content hash, the source-vocabulary digest, and an optional entry-schema version. It enables version pinning and cross-version loading ([§15](#15-knowledge-base)). A missing manifest MUST be treated as an implicit initial version so existing installs load unchanged.

## 11.10 Validation Rules

Schemas MUST validate type correctness, required fields, unknown fields, array types, string types, enum values, and schema version.

## 11.11 Versioning & Generation

Every schema carries a version comprising a **major** and **minor** component. Breaking changes increment the major version; backward-compatible additions increment the minor version. Version 1 guarantees schema compatibility within the same major version. Future tooling MAY automatically generate data classes, validation code, documentation, and example JSON directly from the schemas.

---

# Part IV — Components

# 12. Scene Analyzer

The Scene Analyzer transforms natural language into structured semantic information (Scene JSON). It is the **only** component permitted to use a Large Language Model. It extracts information; it never invents it. Its sole responsibility is language understanding — it knows nothing about Danbooru, Illustrious, Stable Diffusion, prompt engineering, or ComfyUI.

## 12.1 Responsibilities

The Scene Analyzer MUST: parse natural language; identify characters, interactions, objects, environments, camera descriptions, and lighting descriptions; extract explicit attributes; produce a valid Scene JSON document; and preserve uncertainty without inventing information.

The Scene Analyzer MUST NOT: produce Illustrious or Danbooru tags; guess or infer missing information; optimize or beautify prompts; recommend artistic choices; assign categories; or perform Knowledge Base lookup.

## 12.2 Input & Output

- **Input:** a single natural-language description (string). Example: `A blonde girl wearing a white dress hugs a young man while walking under the rain.`
- **Output:** a valid Scene JSON document conforming to [Ch 10](#10-scene-json-grammar) and the [Scene Schema](#111-scene-schema). The Analyzer MUST NOT output Illustrious tags.

Example output (per-section form):

```json
{
  "characters": [
    { "id": 0, "identity": ["female"], "appearance": ["blonde hair"],
      "clothing": ["white dress"], "accessories": [], "pose": [],
      "expression": [], "actions": [] },
    { "id": 1, "identity": ["male"], "appearance": [], "clothing": [],
      "accessories": [], "pose": [], "expression": [], "actions": [] }
  ],
  "interactions": [ { "participants": [0, 1], "concept": "hug" } ],
  "objects": [],
  "environment": ["rain"],
  "camera": [],
  "lighting": [],
  "metadata": {}
}
```

## 12.3 Backend

Version 1 uses **Ollama**. The implementation MUST remain isolated from the compiler so that replacing Ollama with another backend requires replacing only the Analyzer implementation. No downstream component may require modification. The compiler MUST NOT depend on any specific language model.

## 12.4 Temperature, Context Window, Prompts

- **Temperature:** recommended `0.0`. Deterministic output is preferred over creative output.
- **Context window:** the Analyzer SHOULD support long descriptions; context length depends on the selected model. The compiler MUST NOT assume a fixed context size.
- **System prompt:** defines Analyzer behaviour (understand, extract, structure; never optimize, beautify, or invent). The complete official prompt is [Chapter 13](#13-official-analyzer-prompt).
- **User prompt:** forwarded without modification. No hidden prompt engineering occurs outside the System Prompt.

## 12.5 Extraction Behaviour

Only explicitly described information is extracted. The following examples are normative:

| Input | Extracted concepts |
|---|---|
| `A blonde girl smiles.` | `female`, `blonde hair`, `smile` |
| `A girl.` | `female` (no hair, eyes, expression, pose, or clothing) |
| `A beautiful girl smiles.` | `female`, `smile` (`beautiful` is subjective — ignored) |
| `A girl wearing an elegant white dress.` | `female`, `white dress` (`elegant` ignored) |

Subjective adjectives (beautiful, cute, elegant) and artistic language (masterpiece, best quality) MUST be ignored. The Analyzer MUST NOT infer missing information — given `A girl`, it MUST NOT add eyes, expression, clothing, or pose.

## 12.6 Ambiguity

When ambiguity exists, the Analyzer MUST preserve it rather than resolve it. Given `A person`, the result MUST NOT become `male` or `female`. Given `Someone holds a bat`, the Analyzer MUST NOT decide between `animal` and `baseball bat`; the ambiguous concept remains visible in Scene JSON, and the Resolver or a later stage MAY emit a warning.

## 12.7 Confidence

Each extracted concept MAY optionally carry a confidence score, using the object form defined in [§9.3](#93-concept):

```json
{ "name": "female", "confidence": 0.98 }
```

Confidence values are metadata only and MUST NOT influence deterministic compilation.

## 12.8 Failure Handling & Validation

If the Analyzer cannot confidently identify a concept, it MUST omit it — an incorrect concept is worse than a missing one.

Every Analyzer output MUST validate against the [Scene Schema](#111-scene-schema); invalid JSON MUST NOT continue through the compiler. Possible failures include invalid JSON, missing required fields, unexpected fields, malformed arrays, and incomplete objects.

## 12.9 Retry Policy

Version 1 recommends a maximum of **3** retries. Each retry MUST reuse the original user prompt. The Analyzer MUST NOT attempt to repair JSON heuristically; instead it MUST request a corrected response from the model.

## 12.10 Timeouts, Logging, Error Handling

- **Timeouts:** the Analyzer timeout MUST be configurable; failure to receive a response produces a compiler error.
- **Logging:** the Analyzer SHOULD expose request duration, retry count, model name, and validation status. No prompt content is modified during logging.
- **Error handling:** the Analyzer MUST distinguish model failure, connection failure, timeout, schema-validation failure, and unexpected response, and produce a specific compiler error for each (see [Appendix B](#appendix-b--error--warning-codes)).

## 12.11 Future Extensions

Future versions MAY introduce multiple LLM providers, prompt caching, conversation memory, streaming responses, and semantic confidence scores. These additions MUST NOT modify the Scene JSON interface.

---

# 13. Official Analyzer Prompt

This chapter defines the official System Prompt used by the Scene Analyzer. It is part of the compiler specification; every compliant implementation SHOULD use this prompt or an equivalent version. Its objective is to transform natural language into structured semantic information — not to generate prompts.

## 13.1 Core Identity

> You are a Scene Analyzer. You are not a prompt generator, a creative assistant, or an image-generation assistant. You are a deterministic semantic parser. Your only responsibility is extracting information explicitly present in the user's description.

## 13.2 Primary Objective

> Read the user's description. Understand its semantic meaning. Extract explicit concepts. Organize them into Scene JSON. Return valid JSON. Nothing else.

## 13.3 Forbidden Behaviours

> Never generate Illustrious or Danbooru tags. Never optimize, beautify, or rewrite the request. Never improve the scene or add artistic interpretation. Never invent details, guess missing information, or assume defaults. Never explain your reasoning. Never output markdown, comments, or any text outside the JSON document.

## 13.4 Information Extraction Rules

Extract only explicitly described information.

- `A blonde girl smiles.` → `female`, `blonde hair`, `smile`.
- `A girl.` → `female` (do not add hair colour, eye colour, expression, pose, or clothing).

## 13.5 Explicit vs Implicit Information

Explicit information may be extracted; implicit information MUST be ignored. Given `A queen`, do not infer castle, royal room, golden crown, or luxury dress. Given `A knight`, do not invent sword, armor, horse, or castle.

## 13.6 Subjective Adjectives & Artistic Language

Ignore subjective adjectives (beautiful, cute, pretty, cool, amazing, fantastic, elegant, epic) — they describe opinions, not concepts. Ignore artistic/prompt-engineering language (masterpiece, highly detailed, best quality, award winning, beautiful composition) — these are not scene concepts.

## 13.7 Camera & Lighting

Extract camera descriptions only when explicitly present (`Close-up portrait.` → camera `close-up`; `Low angle shot.` → camera `low angle`). Extract lighting only when explicitly described (sunset, candle light, studio lighting, moonlight, golden hour). Do not infer lighting from the environment or invent camera information.

## 13.8 Environment

Extract every explicitly described environmental concept (`Walking in heavy rain.` → environment `rain`; `Standing inside a classroom.` → environment `classroom`).

## 13.9 Characters & Relationships

Every character becomes an independent Character object; never merge characters. Interactions belong to the scene, not to individual characters (`A girl hugs a boy.` → Character 0 `female`, Character 1 `male`, Interaction `hug`).

## 13.10 Unknown & Missing Information

If a concept cannot be categorized confidently, preserve the original wording; never invent another concept. Never complete missing information.

## 13.13 Fidelity Rules *(V2)*

These rules implement [§3.13](#313-fidelity-added-in-v2). The Analyzer MUST NOT quietly reduce what the user wrote.

**List inputs.** When the input is a list of concepts (comma-, newline-, or bullet-separated), the Analyzer MUST transcribe **every** item: a list of N items MUST yield N concepts. Items MUST NOT be dropped, merged, deduplicated, or summarized away; where an item's field is unclear, its original wording is preserved rather than discarded. A deterministic post-parse check emits `SC0021` when a tag-list input yields fewer concepts than it has items.

**Relations and positions.** Spatial, postural, and possessive relationships MUST be preserved as their own concepts rather than collapsed to the bare noun. A held, worn, or positioned object MUST yield the relational concept in addition to the object itself — `a bunch of money in her hand` MUST produce `holding money` *and* `money`, not `money` alone. Body positions (`hand on own hip`, `... in mouth`) MUST survive.

**Conjunctions.** Every item joined by *and*, *with*, *as well as*, *plus*, or a comma is a separate concept; later conjuncts are as important as the first and MUST NOT be dropped.

**Explicit content.** These rules apply identically regardless of subject matter. Adult, suggestive, or NSFW descriptions MUST NOT be abbreviated, softened, censored, generalized, or omitted.

These are extraction-fidelity requirements only. They MUST NOT be read as licence to invent: [§3.4](#34-no-hallucinations) and [§13.3](#133-forbidden-behaviours) still forbid adding anything not present in the description.

## 13.11 JSON, Determinism, Error Recovery

Always return valid JSON with no markdown, explanations, comments, or additional text. The same input SHOULD always produce the same Scene JSON. If a sentence cannot be understood, preserve the unknown concept rather than replacing it with a guess.

## 13.12 Final Objective

> Understand. Extract. Structure. Never imagine, optimize, or create. Analyze.

---

# 14. Scene Validator

The Scene Validator verifies and normalizes Scene JSON **before** resolution. It guarantees that only structurally valid, normalized Scene JSON reaches the Resolver.

> **Note on terminology.** Earlier drafts placed a "Validator" *after* the Resolver to validate resolved tags. In this specification that role is retired: pre-resolution validation is performed here by the Scene Validator, and duplicate-tag removal is performed by the Resolver ([§17.7](#177-duplicate-tags)). "Validator" without qualification refers to the Scene Validator.

## 14.1 Responsibilities

- **Input:** Scene JSON (Analyzer output).
- **Output:** Validated Scene JSON.

The Scene Validator MUST: validate the document against the [Scene Schema](#111-scene-schema); normalize values; remove invalid fields; and report warnings.

The Scene Validator MUST NOT: create or guess concepts; generate tags; or perform Knowledge Base lookup.

## 14.2 Behaviour

Invalid Scene JSON (malformed structure, missing required fields, wrong types) produces an error and MUST NOT continue through the compiler. Recoverable issues (an unexpected field, an empty concept) produce warnings, and compilation continues. Validation order MUST be stable: identical input yields identical output.

---

# 15. Knowledge Base

The Knowledge Base (KB) is the central source of knowledge used by the compiler. It defines how semantic concepts translate into valid Illustrious tags. **The Knowledge Base contains data only; it contains no executable logic.**

## 15.1 Philosophy & Source of Truth

The Knowledge Base is the single source of truth. Every Illustrious tag generated by the compiler MUST originate from the Knowledge Base. No module may hardcode or invent tag mappings. If a concept does not exist in the Knowledge Base, it cannot be resolved. The Knowledge Base separates semantic understanding (the Analyzer understands language) from model-specific knowledge (the Knowledge Base understands Illustrious).

## 15.2 Responsibilities

The Knowledge Base is responsible for: canonical concepts, Illustrious tag mappings, aliases, category assignment, tag expansion, metadata, and validation information.

It is **not** responsible for: natural-language understanding, prompt optimization, prompt formatting, or scene analysis.

## 15.3 File Organization

The Knowledge Base SHOULD be organized into multiple JSON files by domain, improving readability and maintenance. The compiler loads every file during initialization.

```
knowledge_base/
  appearance.json   clothing.json   anatomy.json   expressions.json
  poses.json        actions.json    interactions.json  objects.json
  environments.json camera.json     lighting.json   quality.json  style.json
```

## 15.4 Entry Structure

Every Knowledge Base Entry represents exactly one canonical concept.

```json
{
  "id": "female",
  "aliases": ["girl", "woman", "lady"],
  "tags": ["1girl"],
  "category": "character",
  "expand": [],
  "deprecated": false,
  "notes": ""
}
```

## 15.5 Fields

- **id** — unique **Canonical ID**, a lowercase `snake_case` string, unique across the entire Knowledge Base (e.g. `female`, `blonde_hair`).
- **aliases** — alternative expressions that refer to the same concept. Aliases never generate tags directly; they always resolve to the canonical entry. Aliases MUST be unique across the Knowledge Base.
- **tags** — the Illustrious tags generated by this concept. Tag order MUST be preserved.
- **category** — the primary semantic category (defined by the compiler; see [Ch 18](#18-categories--category-splitter)). Unknown categories are invalid.
- **expand** — an optional list of additional Canonical IDs automatically added during resolution. Expansion references Canonical IDs, never raw tags.
- **deprecated** — marks an obsolete concept. Deprecated concepts continue to work while generating compiler warnings.
- **notes** — optional documentation for contributors; ignored during compilation.

> **Superseded alternative (traceability).** An earlier draft used a numeric integer `id` plus a separate `concept` name field. Version 1 uses the string Canonical ID `id` above; the numeric form is not part of the specification.

## 15.6 Canonical Concepts

Every real-world concept MUST exist exactly once. `female` is one concept; `girl`, `woman`, and `lady` are aliases of it, not separate concepts.

## 15.7 Aliases

Aliases improve natural-language understanding and resolve deterministically. An alias MUST resolve directly to a canonical concept; **aliases MUST NOT point to other aliases** (no alias chains).

```
girl → female → 1girl
```

## 15.8 Expansions

Some concepts imply additional concepts. Expansion is recursive and references Canonical IDs. **Circular expansion is forbidden**, and the compiler MUST detect cycles during Knowledge Base loading.

```
school_uniform → blazer, pleated_skirt
```

## 15.9 Categories

Each canonical concept belongs to exactly one primary category, carried through to the Resolved Tag as traceability metadata. The authoritative category list is defined in [Chapter 18](#18-categories--category-splitter).

## 15.10 Validation Rules

Every entry MUST satisfy: unique `id`; unique aliases; a known category; existing expansion targets; no circular expansions; at least one generated tag; and valid JSON.

## 15.11 Loading & Reloading

The compiler loads the complete Knowledge Base during initialization, and loading MUST fail if validation fails (partial loading is forbidden). Automatic file watching is out of scope. The Knowledge Base is loaded once per process and reused across compilations ([§17.14](#1714-performance-v2)).

In ComfyUI the **Configuration** node performs the load and emits the Knowledge Base for the Resolver; its `knowledge_base_reload` counter is the manual reload operation ([§20](#20-comfyui-nodes)). The Knowledge Base ships inside the package, so its path is fixed rather than a user-facing setting ([§3.15](#315-ask-only-what-matters-added-in-v2)).

## 15.12 Versioning

The Knowledge Base is versioned independently of the compiler. Compiler updates SHOULD NOT require Knowledge Base updates, and Knowledge Base updates SHOULD NOT require compiler updates.

*(V2)* A Knowledge Base directory MAY ship a manifest ([§11.12](#1112-knowledge-base-manifest-schema-v2)) recording its dataset version. A project MAY pin a version via `resolver.knowledge_base_version`; an unavailable version MUST fail with a clear error. Datasets older than the current entry schema MUST be adapted **in memory** at load time — pinned files MUST NOT be rewritten — and versions too old to adapt MUST error clearly.

## 15.13 Automatic Construction *(V2)*

The generated portion of the Knowledge Base MUST be reproducible by a single automated pipeline with **zero required human input**: generate candidates from a committed tag vocabulary → ingest aliases and implications → auto-validate → scan for conflicts → write.

Normative constraints:

1. **No approval gate.** Generated entries are accepted or rejected by structural rules, heuristics, and confidence — never by manual review ([§3.14](#314-automation-without-gates-added-in-v2)). A rejected candidate emits `SC0022`.
2. **Deterministic.** The same snapshots MUST produce the same Knowledge Base.
3. **Curated-first.** The merge is additive: a generated entry MUST be skipped when its id already exists as a curated id or alias, so hand-authored canonicalization and expansions always win.
4. **Real tags only.** Candidates come from a fixed vocabulary of tags that actually exist, so the process cannot invent a tag ([§3.4](#34-no-hallucinations)).

Hand correction remains possible through the Knowledge Base Editor ([§20.2.1](#2021-knowledge-base-editor-v2--not-a-node)), which is optional and off the critical path.

## 15.14 Design Principles & Future Extensions

The Knowledge Base MUST remain deterministic, human-readable, version-controlled, easy to extend, easy to validate, and independent from compiler logic. **The Knowledge Base is data; the compiler is behaviour; these responsibilities MUST NOT be mixed.**

Future versions MAY add metadata such as popularity, examples, language localization, confidence, relationships, and embedding vectors. Such additions MUST remain backward compatible whenever possible and MUST NOT break deterministic behaviour.

---

# 16. Knowledge Base Construction Guide

This chapter defines how the Knowledge Base is built and maintained, ensuring consistency across entries and predictable evolution over time.

## 16.1 General Philosophy

The Knowledge Base represents **meaning**, not words and not prompts. Every entry should answer *"What concept is being described?"* rather than *"What words did the user write?"*.

## 16.2 Canonical Concepts

Every concept exists exactly once. `female` is a concept; `girl`, `woman`, `lady`, `young woman` become aliases of it.

## 16.3 Choosing a Canonical ID

Canonical IDs SHOULD be lowercase, English, singular where possible, readable, and stable (e.g. `female`, `blonde_hair`, `long_hair`, `school_uniform`, `smile`, `holding_hands`). Avoid abbreviations, model-specific names, and implementation details.

## 16.4 Naming Convention

Canonical IDs use `snake_case`; spaces are forbidden (e.g. `looking_at_viewer`, `holding_hands`, `rainy_weather`, `sitting_on_chair`).

## 16.5 Creating Aliases

Create an alias only when multiple expressions describe the same concept (`girl → female`, `lady → female`, `blond hair → blonde_hair`). Aliases MUST NOT introduce ambiguity.

## 16.6 Creating New Concepts

Create a new concept only when the semantic meaning changes. `blonde_hair` and `black_hair` are distinct concepts; `cute_girl`, `beautiful_girl`, `pretty_girl` are subjective descriptions and SHOULD be avoided.

## 16.7 Composite & Expansion Concepts

Composite concepts naturally combine multiple ideas and SHOULD expand into simpler concepts rather than generating many tags directly (`school_uniform → blazer, pleated_skirt`). Expansions MUST represent deterministic relationships only. `school_uniform → blazer` is valid; `princess → castle` is not — a princess does not necessarily imply a castle. Expansions MUST never guess.

## 16.8 Subjective, Context-Dependent & Ambiguous Concepts

- **Subjective** concepts requiring interpretation (beautiful, cute, handsome, cool, epic) MUST NOT exist in Version 1.
- **Context-dependent** concepts MUST be made complete: not `holding`, but `holding_sword`, `holding_book`, `holding_hands`.
- **Ambiguous** expressions (e.g. `bat` = animal or baseball equipment) MUST NOT resolve automatically; the compiler emits a warning instead of guessing.

## 16.9 Category Assignment

Each concept belongs to exactly one primary category, representing the concept's semantic role, not its generated tag (`long_hair → Hair`, `blue_eyes → Eyes`, `white_dress → Clothing`).

## 16.10 Granularity

Prefer atomic concepts (`long_hair`, `blue_eyes`, `white_dress`) over large composite ones (`beautiful_blonde_girl_with_blue_eyes`), which are difficult to reuse.

## 16.11 Unknown Concepts & Deprecation

Unknown concepts MUST NOT be silently ignored; the compiler generates a warning (future versions MAY let users extend the Knowledge Base). Entries MUST NOT be deleted immediately; deprecated entries remain available for compatibility and generate migration warnings.

## 16.12 Documentation & Contributor Guidelines

Complex concepts SHOULD include `notes` explaining meaning, expected usage, known limitations, and expansion behaviour (for contributors only). When adding an entry, a contributor SHOULD verify: does the concept already exist? can it be an alias? should it expand into simpler concepts? is the meaning deterministic? is the category correct? does it generate valid Illustrious tags? will another contributor understand it a year later? If any answer is uncertain, the entry SHOULD NOT be added until clarified.

## 16.13 Long-Term Evolution

The Knowledge Base SHOULD grow by refining concepts (better aliases, better expansions, better validation) rather than duplicating them. Consistency is more valuable than size.

---

# 17. Resolver

The Resolver converts semantic concepts into Illustrious-compatible tags. It is the first component aware of the target model, and it is completely deterministic — no Large Language Model is involved. It ships a single implementation: the **Illustrious Resolver**.

> **Scope grew in V1.1.** The Resolver is now the **final** compiler stage: it also
> performs the work of the removed Category Splitter and Prompt Builder, joining the
> resolved tags into one flat prompt ([§19.7](#197-current-behaviour-flat-prompt)).

## 17.1 Responsibilities

The Resolver MUST: normalize concepts; resolve aliases; look up canonical concepts; expand concepts; generate Illustrious tags; remove duplicate tags; **join the resulting tags into one flat prompt string**; and emit warnings.

The Resolver MUST NOT: call an LLM; guess concepts; invent tags; or modify Scene JSON.

- **Input:** Validated Scene JSON, plus the Knowledge Base.
- **Output:** a flat `prompt` string, plus the Resolved Tags (see [§9.8](#98-resolved-tag)) serialized for inspection, plus warnings and errors.

## 17.2 Resolver Pipeline

Each concept follows the same deterministic pipeline:

```
Concept → Normalize → Alias Resolution → Canonical Concept
        → Knowledge Base Lookup → Expansion → Tag Generation → Resolved Tags
        → join in resolution order → Prompt
```

## 17.3 Normalization

Concepts are normalized before lookup: lowercase conversion, whitespace trimming, repeated-whitespace removal, and Unicode normalization.

## 17.4 Alias Resolution & Canonical Lookup

Aliases resolve directly to canonical concepts (`girl → female`). **Alias chains are forbidden** (`girl → woman → female` is invalid); an alias always resolves directly to its canonical concept. Canonical concepts are then looked up in the Knowledge Base. Known concepts continue; unknown concepts produce a warning (see [§17.6](#176-unknown-concepts)).

## 17.5 Expansion

Expansion occurs after canonical lookup and is **recursive**; **circular expansion is forbidden** and MUST be detected by the Knowledge Base loader.

```
school_uniform → school_uniform, blazer, pleated_skirt
```

**Expansion order (normative):** a concept emits its own `tags` first, then, depth-first and in list order, the tags produced by each `expand` target. Expansion tags are inserted immediately after the concept that generated them. Expansion order MUST remain stable. A configurable maximum expansion depth MAY be enforced (see [Ch 23](#23-configuration)).

## 17.6 Unknown Concepts

Unknown concepts MUST never disappear. The Resolver emits a warning (`SC0001`) and compilation continues.

Before a concept is declared unknown, the Resolver MUST attempt, in order:

1. **Head-noun reduction with modifier preservation** *(V2)* — when a compound concept has no entry, the Resolver drops leading modifiers and looks up the longest matching suffix (`white summer dress` → `dress`), emitting `SC0019`. Each dropped modifier MUST then be retried as a `<modifier> <head-noun>` compound through the normal resolution path and, when it resolves, emitted as its own Resolved Tag in discovery order (`open white shirt` → `white shirt`, `open shirt`). Only the high-precision compound form is tried — never a bare single word — so no tag is invented. This satisfies [§3.13](#313-fidelity-added-in-v2).
2. **Semantic fallback** *(V2, opt-in)* — see [§17.12](#1712-semantic-fallback-v2-opt-in).

## 17.7 Duplicate Tags

Duplicate tags are removed after expansion. Original ordering MUST be preserved (the first occurrence is kept), and `SC0007` is emitted.

*(V2)* This deduplication is gated by `prompt_builder.remove_duplicate_tags`, which defaults to `true`. When disabled, duplicates are kept and `SC0007` MUST NOT be emitted.

## 17.8 Ordering & Category Preservation

Resolver output preserves discovery order. Every generated tag retains the category of its Knowledge Base Entry; categories are never inferred later.

## 17.9 Warnings & Errors

- **Warnings** (compilation continues): unknown concept, deprecated concept, invalid expansion, missing Knowledge Base entry.
- **Errors** (compilation stops): Knowledge Base unavailable or corrupted, circular expansion, invalid category.

## 17.10 Logging

The Resolver SHOULD expose every decision for debugging, for example:

```
gold hair → alias → blonde hair → Knowledge Base `blonde_hair` → tag "blonde hair"
```

## 17.11 Future Resolver Implementations

The architecture allows multiple target models. Each Resolver (Illustrious, Pony, Flux, …) consumes identical Scene JSON; only the Knowledge Base changes, and the compiler core remains unchanged. Resolver behaviour MUST always remain deterministic, predictable, explainable, traceable, and independent from language models.

## 17.12 Semantic Fallback *(V2, opt-in)*

The Resolver MAY fall back to a nearest-neighbour search when a concept misses both deterministic lookup and head-noun reduction ([§17.6](#176-unknown-concepts)). This behaviour is **disabled by default** (`semantic.enabled`).

When enabled, the Resolver compares the unresolved concept against a committed embedding index of Knowledge Base entries and accepts the nearest entry only when similarity is at least `semantic.min_similarity`, emitting `SC0020`. The default backend is a deterministic, offline, dependency-free character-n-gram model.

The following guarantees are **normative** and MUST hold:

1. **Deterministic lookup always wins.** The fallback is consulted only after exact lookup and reduction have failed.
2. **It can never invent a tag.** It MUST return an entry that already exists in the Knowledge Base, or nothing. This preserves [§3.4](#34-no-hallucinations).
3. **It is reproducible.** Identical input MUST yield identical output; no randomness, no network access, no model sampling.
4. **It is bounded.** A match below `min_similarity` MUST be rejected and the concept reported unknown (`SC0001`).

## 17.13 Prompt Translation

After the Resolved Tags are ordered and de-duplicated, the Resolver joins their `tag` values into a single flat prompt string. This is the whole of the former Prompt Builder stage; see [§19.7](#197-current-behaviour-flat-prompt) for the normative output format.

## 17.14 Performance *(V2)*

Performance work MUST NOT change output. The following are permitted and MUST be observationally equivalent to the naive implementation:

- The Knowledge Base is loaded once per process and reused across compilations.
- The normalized lookup table is compiled once per Knowledge Base and reused across resolves.
- Per-concept resolution MAY run in parallel above a size threshold, provided results are merged back in **exact discovery order** so output is identical regardless of scheduling. Sequential resolution is the default.

---

# 18. Categories & Category Splitter

> **⚠️ Superseded in part (V1.1).** The **Category Splitter stage no longer exists**.
> Splitting resolved tags into a Category Map was removed together with the per-category
> prompt outputs ([Ch 19](#19-prompt-builder--outputs)); the Resolver now emits a single
> flat prompt ([§17](#17-resolver)).
>
> **What remains normative:** the **category list** in [§18.2](#182-category-list) and the
> category rules. Every Knowledge Base entry MUST still declare exactly one category, and
> every Resolved Tag MUST still carry it — but purely as **traceability metadata**, surfaced
> on the Resolver's `json` output. Categories MUST NOT shape or partition the prompt.
>
> §18.1 below describes the removed stage and is retained for design rationale only.

## 18.1 Responsibilities *(removed stage — historical)*

- **Input:** Resolved Tags.
- **Output:** Category Map (see [§9.9](#99-category-map)).

The Category Splitter received resolved tags, assigned each to its category, preserved ordering, and prepared prompt construction. Since V1.1 the Resolver performs the ordering and deduplication directly and no Category Map is produced.

## 18.2 Category List

The following **19** categories are defined. This list is authoritative throughout the specification and remains in force: it is the vocabulary for the `category` field of a Knowledge Base entry and of a Resolved Tag.

| Category | Purpose | Examples |
|---|---|---|
| Character | Identity tags | `1girl`, `1boy`, `2girls`, `multiple girls` |
| Appearance | General appearance | `young`, `adult`, `muscular`, `slim` |
| Hair | Hair-related | `blonde hair`, `long hair`, `ponytail`, `braid` |
| Face | Facial characteristics | `freckles`, `beauty mark`, `fang`, `lipstick` |
| Eyes | Eye-related | `blue eyes`, `green eyes`, `closed eyes` |
| Expression | Emotion | `smile`, `crying`, `angry`, `blush` |
| Body | Body-related | `large breasts`, `abs`, `tail`, `wings` |
| Clothing | Wearable items | `dress`, `shirt`, `jacket`, `armor` |
| Accessories | Portable items | `glasses`, `necklace`, `earrings`, `hat` |
| Pose | Static body positions | `standing`, `kneeling`, `sitting`, `lying` |
| Action | Independent actions | `walking`, `reading`, `running`, `sleeping` |
| Interaction | Character relationships | `hug`, `holding hands`, `kiss`, `handshake` |
| Objects | Scene objects | `chair`, `book`, `tree`, `car` |
| Environment | Scene location | `forest`, `classroom`, `bedroom`, `beach` |
| Camera | Camera descriptors | `close-up`, `wide shot`, `low angle` |
| Lighting | Lighting descriptors | `sunset`, `moonlight`, `studio lighting` |
| Style | Reserved for workflow integration | — (not generated automatically in V1) |
| Quality | Reserved for workflow integration | — (not generated automatically in V1) |
| Miscellaneous | Fallback category | should remain nearly empty |

- **Style** and **Quality** are reserved for workflow integration; Version 1 does not generate them automatically.
- **Miscellaneous** is a fallback that SHOULD remain nearly empty; concepts SHOULD migrate to dedicated categories over time.

> **Rejected for V1 (traceability).** `Composition` and `Background` categories appeared in an earlier draft and are intentionally excluded from the Version 1 category set. They MAY be reconsidered in a future version.

## 18.3 Category Rules

Every tag belongs to exactly one category. Categories never overlap and never duplicate tags. Ordering within a category is preserved (Resolver order).

## 18.4 Ordering & Missing Categories *(removed stage — historical)*

Category ordering was deterministic: categories always appeared in the same order, and tags within a category preserved Resolver order. Empty categories were omitted from the Category Map.

Since V1.1 there is no Category Map: the Resolver preserves discovery order across the whole prompt ([§17.8](#178-ordering--category-preservation)).

---

# 19. Prompt Builder & Outputs

> **⚠️ Superseded (V1.1).** The **Prompt Builder stage no longer exists**, and there are
> no per-category prompt outputs, Negative output, or Scene output.
>
> **Current normative behaviour:** the **Resolver** is the final stage. After producing
> ordered, de-duplicated Resolved Tags it joins their `tag` values into **one flat prompt
> string**, comma-separated, in resolution order — see
> [§19.7](#197-current-behaviour-flat-prompt) and [§17](#17-resolver).
>
> §19.1–§19.6 describe the removed stage and are retained for design rationale only.

## 19.1 Responsibilities *(removed stage — historical)*

The Prompt Builder received the Category Map; preserved ordering and categories; formatted outputs; and exposed one output per category. It never generated, removed, or optimized tags.

- **Input:** Category Map (see [§9.9](#99-category-map)).

## 19.2 Standard Outputs *(removed stage — historical)*

It exposed one output per category defined in [§18.2](#182-category-list): Character, Appearance, Hair, Face, Eyes, Expression, Body, Clothing, Accessories, Pose, Action, Interaction, Objects, Environment, Camera, Lighting, Style, Quality, Miscellaneous.

## 19.3 Reserved Outputs *(removed stage — historical)*

It additionally exposed two **reserved** outputs for workflow convenience: **Negative** and **Scene**, always emitted empty. Both were removed with the stage; nothing in the compiler ever populated them, consistent with [§2.3](#23-non-goals-stated-explicitly) (*No automatic prompt engineering*).

## 19.4 Output Format & Empty Outputs *(removed stage — historical)*

Every output was a UTF-8 string; tags comma-separated with no additional formatting:

```
blonde hair,long hair,ponytail
```

The separator was `,` with no surrounding whitespace and no trailing comma. Empty categories returned an empty string, never `null` or placeholder text.

## 19.5 Ordering & Escaping *(removed stage — historical)*

Tag order remained identical to the Category Splitter output; no reordering and no escaping were performed.

## 19.6 EasyIllustrious & Future Compatibility

EasyIllustrious compatibility is achieved by connecting the Resolver's `prompt` output to the appropriate node; the compiler implements no EasyIllustrious-specific logic. Future versions MAY introduce additional prompt targets (Pony, Flux, raw Danbooru, plain prompt, JSON prompt, or A1111) without modifying the compiler pipeline. Existing outputs SHOULD remain backward compatible whenever possible.

## 19.7 Current Behaviour: Flat Prompt

This section is the **normative** replacement for §19.1–§19.5.

The **Resolver** is the final stage. After producing ordered, de-duplicated Resolved Tags ([§17](#17-resolver)) it joins their `tag` values into a single flat prompt string:

- **Output:** one `prompt` string (UTF-8), plus the Resolved Tags serialized as `json` for inspection, and `warnings` / `errors`.
- **Separator:** `,` with no surrounding whitespace and no trailing comma (`tag1,tag2,tag3`). The separator is configurable in the configuration document (`prompt_builder.separator`) but is **not** exposed as a node input in this version ([§23](#23-configuration), [§3.15](#315-ask-only-what-matters-added-in-v2)).
- **Ordering:** resolution (discovery) order across the whole prompt; character concepts first, then the scene sections. Nothing is reordered.
- **Escaping:** none. Tags are emitted exactly as resolved.
- **Empty result:** an empty string. It MUST NOT be `null` or placeholder text.

```
1girl,blonde hair,blue eyes,dress,smile,classroom,sunset
```

Categories still exist on every Resolved Tag but MUST NOT partition this output; they are traceability metadata only ([§18](#18-categories--category-splitter)).

---

# 20. ComfyUI Nodes

The compiler is implemented entirely as a ComfyUI custom-node package. **Nodes are thin interfaces; all business logic remains inside the compiler package.** The compiler is not a workflow but a toolbox: users SHOULD be able to replace only the parts they need, and every node SHOULD be usable independently.

> **Consolidated in V1.1 and V2.1.** The package originally exposed eight nodes, one
> per stage plus support nodes. Stages that carried no real decisions were folded away:
> the Category Splitter and Prompt Builder into the Resolver (V1.1), and the Knowledge
> Base Loader into the Configuration node (V2.1). **Five nodes ship today.** This follows
> [§3.15](#315-ask-only-what-matters-added-in-v2): a node moves data; it is not a settings panel.

## 20.1 Pipeline Nodes

| Node | Input | Output |
|---|---|---|
| Scene Analyzer | `natural_language`; `config` (optional) | `scene`; `warnings`; `errors`; `raw` |
| Scene Validator | `scene`; `config` (optional) | `scene`; `warnings`; `errors`; `raw` |
| Resolver | `scene`; `knowledge_base`; `config` (optional) | `prompt`; `warnings`; `errors`; `json` |

Analyzer settings (model, temperature, retries, timeout) arrive through the optional `config` connection and MUST NOT be duplicated as node inputs. Without a Configuration node the built-in defaults apply, with a timeout generous enough for a local model that cold-loads on first call.

*(Removed: the Category Splitter and Prompt Builder node rows — see the note above.)*

## 20.2 Support Nodes

| Node | Input | Output |
|---|---|---|
| Configuration | the compiler settings a user should set ([§23](#23-configuration)) | `config`; `knowledge_base`; `warnings`; `errors` |
| Debug Viewer | `scene`; `warnings`; `errors` (all optional) | `report` |

- **Configuration** is the single source of compiler settings **and** the Knowledge Base loader: it loads the Knowledge Base that ships with the package and emits it on `knowledge_base`, which is wired into the Resolver. A `knowledge_base_reload` counter forces a fresh read. If the Knowledge Base fails to load, `config` MUST still be emitted (the Analyzer and Validator do not need it) and the failure reported on `errors`.
- **Debug Viewer** — read-only; displays connected intermediate state. Resolved tags are inspectable via the Resolver's `json` output.
- *(Removed: the Knowledge Base Loader node — folded into Configuration in V2.1.)*

### 20.2.1 Knowledge Base Editor *(V2 — not a node)*

An optional web editor for curated Knowledge Base entries is served on a sub-route of the ComfyUI server (`/scene-compiler/kb`). It MUST remain optional, MUST validate against the authoritative Knowledge Base rules before saving, MUST write atomically and format-safely, and MUST stay off the compile critical path — the compiler MUST NOT depend on it. It is the only manual surface permitted by [§3.14](#314-automation-without-gates-added-in-v2).

## 20.3 Node Independence & Future Nodes

Every node SHOULD be usable independently, and users MAY replace any stage with a custom implementation. Future versions MAY introduce additional helper nodes — and Version 4 plans a single unified node running the whole pipeline ([§30](#30-long-term-roadmap)) — but core compiler behaviour MUST remain unchanged.

---

# Part V — Cross-Cutting Concerns

# 21. Error & Warning Handling

Errors are first-class compiler objects. The compiler MUST never silently ignore a failure. Every compiler stage returns the [Compiler Result wrapper](#86-compiler-result-wrapper) (`data`, `warnings`, `errors`, `metadata`), and this interface is identical across all modules.

## 21.1 Severity Levels

The compiler defines four severity levels:

- **Information** — describes compiler activity (successful compilation, debug events, statistics); never requires user action.
- **Warning** — a recoverable problem; compilation continues. Examples: unknown concept, deprecated concept/alias, duplicate tag removed, unused/unknown field.
- **Error** — invalid intermediate data; the affected compilation stops. Examples: malformed Scene JSON, missing required field, invalid category, unknown schema version, schema mismatch, circular expansion.
- **Fatal** — the compiler cannot start or continue at all. Examples: Knowledge Base missing, Resolver unavailable, Analyzer unavailable, invalid configuration.

The distinction between Error and Fatal: an **Error** halts one compilation path while the compiler itself remains operational; a **Fatal** condition means the compiler cannot run.

## 21.2 Message Codes

Every message carries a unique code (e.g. `SC0001`). The complete enumeration is in [Appendix B](#appendix-b--error--warning-codes).

## 21.3 Message Structure

Every message contains: `code`, `severity`, `title`, `description`, and optional `context`. Error messages SHOULD explain what failed, why, and a possible solution.

## 21.4 Logging

Messages MUST be machine-readable; human-readable formatting belongs to the user interface. Logs MUST NOT require string parsing.

---

# 22. Logging & Debugging

Debugging is a core feature: intermediate compiler representations MUST always be inspectable.

## 22.1 Debug Levels

`None`, `Basic`, `Verbose`, `Developer`.

## 22.2 Stage Inspection

Users MUST be able to inspect each representation in the pipeline:

```
Natural Language → Scene JSON → Resolved Tags → Category Map → Prompt Outputs
```

## 22.3 Traceability

Every generated tag SHOULD expose its origin sentence, Scene JSON location, Resolver rule, Knowledge Base Entry, and final category (see [§3.5](#35-traceability)).

## 22.4 Development Mode

Development Mode SHOULD expose compilation time, Resolver statistics, Knowledge Base version, Analyzer version, and node versions.

---

# 23. Configuration

The compiler MUST be configurable without code modification. Configuration is external to compiler logic, human-readable, and version-controlled. The compiler uses JSON; YAML MAY be introduced later.

## 23.1 Configuration Philosophy

Configuration changes behaviour, never architecture. Every configuration option MUST remain deterministic; random seeds MUST NOT exist.

## 23.2 Global Configuration Example

```json
{
  "schema": "1.0",
  "analyzer": {
    "backend": "ollama",
    "model": "llama3",
    "temperature": 0.0,
    "max_retries": 3,
    "timeout": 60
  },
  "resolver": {
    "knowledge_base": "knowledge_base/",
    "strict_mode": true,
    "allow_aliases": true,
    "expansion_enabled": true,
    "max_expansion_depth": 8,
    "include_nsfw": false,
    "knowledge_base_version": null
  },
  "validator": {
    "allow_unknown_fields": false
  },
  "prompt_builder": {
    "target": "easy_illustrious",
    "separator": ",",
    "remove_duplicate_tags": true
  },
  "semantic": {
    "enabled": false,
    "min_similarity": 0.5,
    "backend": "char_ngram"
  },
  "debug": {
    "enabled": false,
    "level": "basic"
  }
}
```

> **Changed in V2.** `prompt_builder.trim_empty_outputs` was **removed** — it became
> inert when V1.1 dropped per-category outputs. `prompt_builder.remove_duplicate_tags`
> is now wired to real behaviour ([§17.7](#177-duplicate-tags)). The `semantic` section,
> `resolver.include_nsfw`, and `resolver.knowledge_base_version` were added.

## 23.3 Configuration Options by Section

- **Analyzer:** backend, model, temperature, maximum retries, timeout, context length, custom system prompt, streaming. `temperature = 0` is recommended to maximize repeatability.
- **Resolver:** Knowledge Base path, strict mode, alias resolution, expansion enabled, maximum expansion depth, `include_nsfw` (default `false`; gates explicit-rated entries), and `knowledge_base_version` (default `null`; pins a dataset version — see [§15](#15-knowledge-base)).
- **Scene Validator:** unknown-field policy, strictness.
- **Prompt output (`prompt_builder`):** `separator` (used by the Resolver's translation), `target` (reserved), and `remove_duplicate_tags`.
- **Semantic (V2, opt-in):** `enabled` (default `false`), `min_similarity`, `backend`. Governs [§17.12](#1712-semantic-fallback-v2-opt-in).
- **Debug:** debug mode, log level, save intermediate files, performance metrics, trace mode.

## 23.4 Exposed vs Internal Configuration *(V2)*

The sections above define the **configuration document**. Per [§3.15](#315-ask-only-what-matters-added-in-v2), the Configuration node MUST expose only the subset a user should set. The following fields keep their defaults and MUST NOT appear as node inputs:

| Field | Rationale |
|---|---|
| `resolver.knowledge_base` | The Knowledge Base ships inside the package; the path is fixed, not a question to ask. |
| `prompt_builder.target` | Reserved; to be replaced in V3. |
| `prompt_builder.separator` | Fixed to `,` for this version. |
| `analyzer.system_prompt` | A hand-written system prompt is not a user-friendly surface; the official prompt ([Ch 13](#13-official-analyzer-prompt)) is always used. |

They remain part of the document, so a programmatic caller constructing a configuration directly MAY still set them.

## 23.5 Future Configuration

Future versions MAY add plugin management, multiple Knowledge Bases, language packs, caching, profiling, and benchmarking. These MUST remain optional and backward compatible.

---

# Part VI — Engineering & Process

# 24. Repository Structure

The repository is organized around compiler stages; every directory corresponds to a clear responsibility.

```
ComfyUI-SceneCompiler/
├── __init__.py
├── nodes/            # ComfyUI nodes only — no compiler logic
├── compiler/         # pure compiler logic — never imports ComfyUI
│   ├── analyzer/
│   ├── validator/
│   ├── resolver/     # resolution + flat prompt translation
│   └── common/       # config, logging, result, knowledge base, embeddings
├── knowledge_base/   # Knowledge Base JSON files only — no code
├── schemas/          # JSON Schemas and data models
├── prompts/          # official LLM system prompts and templates
├── config/           # configuration files
├── tests/
│   ├── analyzer/
│   ├── resolver/
│   ├── validator/
│   ├── integration/
│   └── regression/
├── examples/         # workflows, example Scene JSON, example prompts
├── scripts/          # dev utilities, KB generators, validation, migration
├── docs/
├── LICENSE
├── README.md
└── pyproject.toml
```

## 24.1 Directory Responsibilities

- **nodes/** — ComfyUI node definitions only; no compiler logic. (Since V1.1/V2.1 there are no `splitter/` or `builder/` packages: the Resolver performs that work.)
- **compiler/** — all business logic; MUST never import ComfyUI.
- **knowledge_base/** — Knowledge Base files (concepts, aliases, categories, expansion rules); only JSON, no executable code.
- **schemas/** — JSON Schemas and Python data models (Scene JSON, Compiler Result, Knowledge Base, Configuration).
- **prompts/** — official LLM system prompts, few-shot examples, templates; no implementation logic.
- **config/** — configuration files.
- **tests/** — dedicated tests per compiler stage plus integration and regression tests.
- **examples/** — ready-to-use workflows, example Scene JSON documents, example prompts.
- **scripts/** — development utilities, Knowledge Base generators, validation tools, migration scripts.
- **docs/** — documentation not included in the GitHub Wiki.

---

# 25. Coding Guidelines

This project is developed primarily with AI-assisted programming; readability and maintainability are valued over cleverness and premature optimization.

## 25.1 Primary Objective

Readable code is preferred over clever code; maintainability over optimization. Claude Code and other agents SHOULD prioritize correctness, determinism, readability, and testability before optimization.

## 25.2 Language & Types

- **Python version:** 3.11 or newer.
- **Type hints:** every public function SHOULD use explicit type hints.
- **Data models:** structured data SHOULD use typed models; avoid anonymous dictionaries where possible.

## 25.3 Design Rules

Functions SHOULD remain small with a single responsibility and explicit names. Minimize hidden state; no magic values; no undocumented behaviour.

## 25.4 Separation of Concerns & State

Compiler logic belongs in `compiler/`; ComfyUI nodes are interfaces only. Avoid mutable global state; compiler instances SHOULD be self-contained.

## 25.5 Hardcoded Data

Hardcoded tag mappings are forbidden; every mapping belongs in the Knowledge Base (see [§3.8](#38-knowledge-is-data)).

## 25.6 Comments & Documentation

Comments SHOULD explain *why*, never *what* — the code already explains what. Every public class and function SHOULD include a docstring.

## 25.7 Error Messages & Logging

Every error message SHOULD explain what failed, why, and a possible solution. Use centralized, structured logging; avoid `print()`. Logs SHOULD NOT require string parsing.

## 25.8 Testing

New functionality SHOULD include tests; every bug fix SHOULD include a regression test (see [Ch 26](#26-testing-strategy)).

## 25.9 Dependencies

Keep external dependencies minimal; prefer the Python standard library where practical.

## 25.10 Refactoring & Pull Requests

Large refactors MUST preserve compiler behaviour — behavioural compatibility outweighs implementation compatibility. Every pull request SHOULD include a description, reason, tests, and (if required) a documentation update.

---

# 26. Testing Strategy

Testing is a core feature: every compiler stage MUST be independently verifiable, and every bug SHOULD become a permanent regression test.

## 26.1 Unit Tests

Each compiler stage exposes isolated unit tests: Scene Analyzer, Scene Validator, Resolver — plus the ComfyUI node adapters and the Knowledge Base tooling.

## 26.2 Integration Tests

Integration tests exercise the complete pipeline (`Natural Language → Scene JSON → Resolved Tags → Prompt Outputs`); expected output MUST remain deterministic.

## 26.3 Regression Tests

Every fixed bug receives a permanent regression test. Regression tests MUST NOT be removed; a resolved bug MUST never reappear unnoticed.

## 26.4 Knowledge Base Tests

Every Knowledge Base Entry is validated for: duplicate IDs, duplicate aliases, missing categories, unknown/missing tags, circular aliases, circular/invalid expansions, and schema validity.

## 26.5 Schema Validation

Every JSON file MUST validate against its schema (Scene JSON, Knowledge Base, Configuration, Compiler Result).

## 26.6 Performance Tests

Measure compilation time, Resolver speed, Knowledge Base loading, and memory consumption.

## 26.7 Golden Tests

Golden tests compare generated prompts against reference outputs (identical input → identical output), ensuring determinism across compiler updates.

## 26.8 Reference Test Dataset

Version 1 ships an official set of benchmark scenes that become part of the long-term validation suite: single character, two characters, character interaction, indoor scene, outdoor scene, fantasy scene, modern scene, unknown concepts, ambiguous concepts, and a complex multi-character scene.

---

# 27. Guidelines for AI Engineering Agents

This specification is intended primarily for AI-assisted development. This chapter contains implementation guidance (recommended strategies) and mandatory rules. The guidance describes *how* to implement; it is not compiler behaviour.

## 27.1 General Philosophy

Prefer correctness over optimization, readability over cleverness, and deterministic behaviour over intelligent behaviour.

## 27.2 Module Isolation & Dependency Direction

Compiler stages MUST NOT depend directly on each other; only public interfaces are shared. Dependencies point downward only:

```
Allowed:   Scene Analyzer → Scene Validator → Resolver
Forbidden: Resolver → Scene Validator
```

## 27.3 State, Configuration, Knowledge Base

Compiler stages SHOULD remain stateless where possible; global mutable state is discouraged. Configuration SHOULD be injected, not globally imported. The Knowledge Base is loaded once, cached safely, and reloaded only explicitly — never automatically.

## 27.4 Exceptions vs Warnings

Exceptions represent unexpected failures; compiler warnings represent expected, recoverable failures. These two concepts MUST remain independent.

## 27.5 Future Refactoring

Version 1 prioritizes clarity; performance optimizations belong to future versions. Behavioural compatibility always takes precedence.

## 27.6 Mandatory Rules

- When implementation details are ambiguous, prefer deterministic behaviour.
- When architecture conflicts with convenience, prefer architecture.
- When optimization conflicts with readability, prefer readability.
- When intelligence conflicts with explainability, prefer explainability.
- When creativity conflicts with correctness, prefer correctness.
- When uncertain, generate warnings instead of assumptions.
- Never hardcode knowledge — knowledge belongs in the Knowledge Base.
- Never bypass compiler stages — every stage exists for a reason.
- Never merge responsibilities — the Single Responsibility Principle is mandatory.
- Always write tests before considering a feature complete; every bug fix introduces a regression test.
- Every generated Illustrious tag MUST be explainable; every compiler output MUST be reproducible.

**The compiler is not a prompt generator; it is a deterministic compiler. Protect this principle above all others.**

---

# 28. Versioning Strategy

Scene Compiler follows Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **MAJOR** — breaking changes: schema changes, pipeline changes.
- **MINOR** — new features: new nodes, new Resolver implementations, new Knowledge Base capabilities.
- **PATCH** — bug fixes, performance improvements, documentation, regression fixes.

## 28.1 Stability Policy

Version 1 provides a stable API, stable Scene JSON, and a stable Knowledge Base format.

## 28.2 Deprecation

Deprecated features SHOULD remain available for at least one major version where practical, and compiler warnings MUST clearly indicate deprecated behaviour.

---

# Part VII — Roadmap

# 29. Recommended Development Order

This chapter defines the recommended implementation order. Following it minimizes refactoring; dependencies always point downward, and no step depends on unfinished future work. A smaller, stable Version 1 is preferred over an incomplete Version 2. Every completed phase MUST leave the repository in a working state.

> **Historical record.** This is the original Version 1 build plan, executed as written
> and kept for reference. Some components it schedules were later folded away — the
> Category Splitter and Prompt Builder into the Resolver (V1.1), and the Knowledge Base
> Loader node into the Configuration node (V2.1). For what ships today see
> [Ch 20](#20-comfyui-nodes).

## Phase 0 — Repository Initialization
Create the repository structure; configure linting, formatting, the testing framework, and CI; create the documentation skeleton. No compiler logic yet.

## Phase 1 — Foundation
Implement JSON Schemas, data models, the Compiler Result wrapper, the configuration system, logging, and the Knowledge Base Loader. At the end, every data structure exists but nothing compiles yet.

## Phase 2 — Knowledge Layer
Implement the Knowledge Base format, alias system, expansion rules, category system, and validation tools; create the first Knowledge Base dataset. The compiler now knows everything about Illustrious but cannot yet analyze language.

## Phase 3 — Compiler Core (no LLM)
Implement the Scene Validator, Resolver (deterministic lookup, expansion, warnings, logging), Category Splitter, and Prompt Builder, with their tests. The compiler now transforms Scene JSON into prompt outputs **without any LLM**.

## Phase 4 — Scene Analyzer
Implement the Ollama interface, the strict system prompt, the Scene JSON parser, response validation, and retry logic, with Analyzer tests. Natural language now becomes Scene JSON; the full pipeline functions.

## Phase 5 — ComfyUI Integration
Implement the pipeline nodes (Analyzer, Validator, Resolver, Category Splitter, Prompt Builder) and the support nodes (Debug Viewer, Knowledge Base Loader, Configuration). All nodes remain thin wrappers around compiler modules.

## Phase 6 — Testing
Implement unit, integration, regression, Knowledge Base validation, and example-scene tests.

## Phase 7 — Integration & Examples
Provide example workflows, example prompts, and example Scene JSON; complete documentation; add the benchmark dataset and performance measurements.

## Phase 8 — Release Preparation
Finalize the regression suite; perform performance optimization, documentation review, and Knowledge Base review; package and release Version 1.

## Development Rules
The compiler MUST remain functional after every phase. No phase MAY introduce unfinished architecture. Refactoring SHOULD be minimized, and behavioural compatibility always has priority over implementation convenience.

## Release Criteria
Version 1 is complete when: the compiler converts natural language into categorized Illustrious tags; all stages are tested; the Knowledge Base validates successfully; official example workflows execute without modification; documentation is complete; the compiler remains deterministic; and no mandatory feature relies on prompt generation. (See also [Ch 7](#7-success-criteria--definition-of-done).)

---

# 30. Long-Term Roadmap

This roadmap defines the long-term evolution of Scene Compiler. Each version has a clearly defined scope; features scheduled for future versions SHOULD NOT be implemented early unless explicitly required.

## 30.1 Version 1 — Deterministic Compiler Foundation ✅ *delivered (`v1.0.0`, `v1.1.0`)*

**Objective:** build a complete deterministic compiler that transforms natural language into Illustrious-compatible prompts. The objective is reliability, not intelligence.

**Core features:** Scene Analyzer, Scene JSON, Knowledge Base, Scene Validator, Resolver, EasyIllustrious integration, Ollama integration, Debug Viewer, configuration system, JSON Schemas, regression tests. *(The Category Splitter and Prompt Builder shipped in `v1.0.0` and were removed in `v1.1.0`; the Resolver absorbed their work.)*

**Supported model family:** Illustrious only. The architecture remains model-independent, but a single Resolver ships.

**Explicitly excluded at the time:** semantic search, embeddings, Knowledge Base editor, automatic prompt optimization/beautification, graph representation, plugin system, multiple model families, automatic style/camera/lighting/composition/quality generation. *(The first three were delivered in V2 under strict constraints; the rest remain excluded.)*

**Success criteria:** see [Chapter 7](#7-success-criteria--definition-of-done).

## 30.2 Version 2 — Semantic Resolution ✅ *delivered (`v2.0.0`, `v2.1.0`)*

**Objective:** improve concept resolution without sacrificing determinism. Version 2 adds semantic assistance while keeping the compiler architecture unchanged.

The guiding shift was to make the compiler **know more and ask less**: grow the Knowledge Base and catch near-misses automatically, while reducing what the user is asked to configure.

**Delivered:**

- **Knowledge Base Editor** — an optional web editor that validates entries before saving, off the compile critical path ([§20.2.1](#2021-knowledge-base-editor-v2--not-a-node)).
- **Semantic / Embedding Search** — an **opt-in** nearest-neighbour fallback used only when deterministic lookup and head-noun reduction fail. It never replaces deterministic lookup and can only return an existing Knowledge Base entry ([§17.12](#1712-semantic-fallback-v2-opt-in)).
- **Automatic Knowledge Base Builder** — a fully automated pipeline. **This shipped deliberately differently from the original plan:** generated entries are validated by rules, heuristics, and confidence, and **not** by manual review. An approval gate was rejected as an anti-pattern — see [§3.14](#314-automation-without-gates-added-in-v2).
- **Alias & validation tooling** — automatic duplicate and conflict detection, Knowledge Base coverage benchmarking, Resolver optimization.
- **Knowledge Base Versioning** — a dataset manifest, a pinnable version, and in-memory migration of older datasets.
- **Concept fidelity** — modifier preservation, full list transcription, and relational concepts ([§3.13](#313-fidelity-added-in-v2)).
- **Performance improvements** — Knowledge Base caching, compiled lookup tables, incremental loading, optional parallel resolution ([§17.14](#1714-performance-v2)).
- **Node & configuration consolidation** *(V2.1)* — eight nodes became five and the Configuration surface was trimmed ([§3.15](#315-ask-only-what-matters-added-in-v2), [§20](#20-comfyui-nodes)).

**Dropped:** **Localization** (multi-language analyzers) was planned and then dropped as unnecessary.

**Not pursued:** the **Entity Graph** internal representation remains unimplemented. Scene JSON is still both the internal and the public representation, and remains the public interface for backward compatibility.

**Migration:** Scene JSON is unchanged, so scenes and the compiler API remain compatible. **Saved ComfyUI workflows do require rewiring**, because nodes were removed and consolidated ([§20](#20-comfyui-nodes)).

## 30.3 Version 3 — Extensible Compiler Platform

**Objective:** transform Scene Compiler into a general-purpose prompt compiler.

- **Multi-model support:** Illustrious, Pony, Flux, NoobAI, future Danbooru and (where applicable) non-Danbooru models. Each model uses its own Resolver while sharing the same Scene JSON.
- **Plugin system:** Resolvers, Analyzers, Prompt Builders, Validators, and Knowledge Providers all become plugins.
- **Multiple Analyzer backends:** Ollama, Claude, GPT, Gemini, Mistral, custom NLP engines.
- **Interactive Knowledge Base:** visual editor, search, conflict resolution, validation, statistics, version management.
- **Workflow Optimizer:** automatic workflow generation, node recommendations, EasyIllustrious integration helpers, workflow templates.
- **Compiler SDK:** expose the compiler as a reusable Python package usable independently of ComfyUI.
- **Benchmark Suite:** public benchmark dataset, reference prompts, performance/regression/Knowledge Base benchmarks.

**Long-term vision:** Scene Compiler becomes a compiler framework in which Illustrious is only one supported backend, while the compiler core remains unchanged.

---

# Appendix A — Glossary

Canonical vocabulary. Each term is defined once here and used consistently throughout the specification.

| Term | Definition |
|---|---|
| **Scene Compiler** | The deterministic prompt compiler specified by this document. |
| **Scene Analyzer** | The stage that converts natural language into Scene JSON; the only component that uses an LLM. |
| **Scene JSON** | The Intermediate Representation (IR): a structured document of semantic concepts. The compiler's stable public interface. |
| **Raw Scene JSON / Validated Scene JSON** | Scene JSON as produced by the Analyzer / as produced by the Scene Validator. Used only where the stage boundary matters. |
| **Scene Validator** | The stage that validates and normalizes Scene JSON before resolution. |
| **Concept** | The smallest semantic unit in Scene JSON (e.g. `female`, `blonde hair`). Never an Illustrious tag. |
| **Knowledge Base (KB)** | The data-only single source of truth mapping concepts to Illustrious tags. |
| **Knowledge Base Entry** | A single canonical record in the Knowledge Base (`id`, `aliases`, `tags`, `category`, `expand`, `deprecated`, `notes`). |
| **Canonical ID** | The unique `snake_case` `id` of a Knowledge Base Entry. |
| **Alias** | An alternative expression that resolves directly to a Canonical ID. Aliases never chain. |
| **Expansion** | The automatic inclusion of additional Canonical IDs referenced by an entry's `expand` field. |
| **Resolver** | The deterministic stage that converts concepts into Illustrious tags using the Knowledge Base. |
| **Illustrious tag** | A Danbooru-format tag valid for the Illustrious model family. ("Danbooru" denotes the tag-format lineage; the Analyzer emits no tags of any format.) |
| **Resolved Tag** | A generated Illustrious tag with full traceability metadata. |
| **Category** | One of the 19 semantic groups defined in [Ch 18](#18-categories--category-splitter). |
| **Category Splitter** | *(Removed in V1.1.)* The stage that assigned Resolved Tags to categories. Categories are now traceability metadata only. |
| **Category Map** | The mapping of categories to ordered arrays of Resolved Tags. |
| **Prompt Builder** | *(Removed in V1.1.)* The final stage that formatted the Category Map into per-category Prompt Outputs. The Resolver now emits one flat prompt. |
| **Prompt Output** | One named workflow output (a UTF-8 string). The final compiler product. |
| **Compiler Result** | The uniform wrapper (`data`, `warnings`, `errors`, `metadata`) returned by every stage. |

---

# Appendix B — Error & Warning Codes

Every compiler message carries a unique code. Codes are stable across patch versions.

| Code | Severity | Title | Meaning |
|---|---|---|---|
| SC0001 | Warning | Unknown Concept | A concept has no Knowledge Base Entry; it is reported and ignored. |
| SC0002 | Error | Invalid Scene JSON | Scene JSON fails schema validation. |
| SC0003 | Error | Circular Expansion | An expansion cycle was detected. |
| SC0004 | Fatal | Knowledge Base Load Failure | The Knowledge Base could not be loaded or failed validation. |
| SC0005 | Error | Duplicate Canonical ID | Two Knowledge Base Entries share an `id`. |
| SC0006 | Warning | Deprecated Concept | A resolved concept is marked deprecated; migration is encouraged. |
| SC0007 | Warning | Duplicate Tag Removed | A duplicate tag was removed after expansion. |
| SC0008 | Error | Invalid Category | A tag or entry references a category outside the defined set. |
| SC0009 | Error | Missing Required Field | A required field is absent from an intermediate document. |
| SC0010 | Error | Schema Version Mismatch | A document declares an unsupported schema version. |
| SC0011 | Error | Analyzer Schema Validation Failure | The Analyzer response failed Scene JSON validation after all retries. |
| SC0012 | Fatal | Analyzer Unavailable | The Analyzer backend (e.g. Ollama) could not be reached. |
| SC0013 | Error | Analyzer Timeout | The Analyzer did not respond within the configured timeout. |
| SC0014 | Fatal | Invalid Configuration | The compiler configuration is invalid. |

**Extensions added during implementation.** SC0001–SC0014 are the original codes; the following were added as the compiler was built and are equally normative.

| Code | Severity | Title | Meaning |
|---|---|---|---|
| SC0015 | Warning | Unexpected Field Removed | The Scene Validator removed a field not present in the schema. |
| SC0016 | Warning | Empty Concept Removed | An empty or whitespace-only concept was removed after trimming. |
| SC0017 | Warning | Interaction Dropped | An interaction referencing a non-existent character was dropped. |
| SC0018 | Error | Analyzer Unexpected Response | The Analyzer backend returned an HTTP error or an unexpected response shape. |
| SC0019 | Warning | Concept Reduced | A compound concept was reduced to its head noun to resolve. Each dropped modifier is retried as a `<modifier> <head-noun>` compound and, when it resolves, emitted as its own tag ([§17.6](#176-unknown-concepts)). |
| SC0020 | Warning | Semantic Fallback | The opt-in semantic fallback resolved a concept that missed deterministic lookup, above `semantic.min_similarity` ([§17.12](#1712-semantic-fallback-v2-opt-in)). |
| SC0021 | Warning | List Under-Transcription | A tag-list input produced fewer concepts than it has items — the Analyzer may have omitted entries. Advisory ([§3.13](#313-fidelity-added-in-v2)). |
| SC0022 | Warning | Candidate Rejected | The automatic Knowledge Base builder's auto-validation rejected a generated candidate entry ([§15](#15-knowledge-base)). |

Message structure: every message contains `code`, `severity`, `title`, `description`, and optional `context` (see [§21.3](#213-message-structure)).

---

# Appendix C — Category Reference

## C.1 The 19 Categories

The authoritative category list, with examples, is defined in [§18.2](#182-category-list): Character, Appearance, Hair, Face, Eyes, Expression, Body, Clothing, Accessories, Pose, Action, Interaction, Objects, Environment, Camera, Lighting, Style, Quality, Miscellaneous.

## C.2 Scene Section → Category Mapping

A concept's final category is determined by the **`category` field of its Knowledge Base Entry**, not by the Scene JSON section it appears in. The Scene section constrains *placement during analysis*; the Knowledge Base assigns the *output category during resolution*. Most sections map directly to one category; the `appearance` section fans out across several categories according to each concept's Knowledge Base Entry.

| Scene section | Typical output category / categories |
|---|---|
| `identity` | Character |
| `appearance` | Hair, Face, Eyes, Body, or Appearance (per Knowledge Base Entry) |
| `clothing` | Clothing |
| `accessories` | Accessories |
| `pose` | Pose |
| `expression` | Expression |
| `actions` | Action |
| `interactions` | Interaction |
| `objects` | Objects |
| `environment` | Environment |
| `camera` | Camera |
| `lighting` | Lighting |
| (workflow-supplied) | Style, Quality |
| (fallback) | Miscellaneous |

---

*End of Master Specification.*
