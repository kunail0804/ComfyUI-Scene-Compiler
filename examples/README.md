# Examples

Ready-to-use examples for Scene Compiler.

## Workflow

[`workflows/scene_compiler_pipeline.json`](workflows/scene_compiler_pipeline.json)
is a ComfyUI workflow wiring the full pipeline:

```
Configuration ─┬─▶ Scene Validator ─▶ Resolver ─▶ Category Splitter ─▶ Prompt Builder
               ├──────────────────────▶ (config)               (config) ◀┘
Knowledge Base Loader ─────────────────▶ Resolver (knowledge_base)
Scene Analyzer ─▶ Scene Validator (scene)
```

Load it in ComfyUI (**Load** → pick the file). The Scene Analyzer requires a local
[Ollama](https://ollama.com) instance; the rest of the pipeline runs offline.

## Scene JSON examples

Each `scenes/*.scene.json` is a Scene JSON document (the Analyzer's output form),
and each matching `scenes/*.prompts.json` is the exact prompt output it compiles
to with the shipped Knowledge Base and default configuration:

| Scene | Highlights |
|---|---|
| [`single_character`](scenes/single_character.scene.json) | one character, appearance, clothing, environment, camera, lighting |
| [`couple_interaction`](scenes/couple_interaction.scene.json) | two characters, an interaction, and an expansion (`school_uniform → blazer, pleated_skirt`) |

The `*.prompts.json` outputs are verified by `tests/test_examples.py`. To skip the
Analyzer and compile a Scene JSON directly, feed it through the Validator →
Resolver → Category Splitter → Prompt Builder nodes (or the compiler API).

> **Note:** the workflow JSON is provided as a starting point; verify it loads in
> your ComfyUI and re-save if ComfyUI adjusts the layout.
