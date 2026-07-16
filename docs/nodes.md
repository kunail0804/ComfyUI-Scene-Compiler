# ComfyUI node reference

The exact inputs, outputs, and data types of the shipped Scene Compiler nodes.
All nodes appear under the **Scene Compiler** category. Data flows between nodes
as typed objects; the inter-stage types are `SCENE`, `RESOLVED_TAGS`,
`CATEGORY_MAP`, `KNOWLEDGE_BASE`, and `COMPILER_CONFIG`.

Nodes are thin adapters: all behaviour lives in the `compiler` package, which
never imports ComfyUI.

Every stage node also exposes a **`raw`** string output — a JSON dump of that
node's data output — for inspecting the pipeline (wire it into a text/preview
node). The Knowledge Base Loader's `raw` summarizes the loaded entries. A
relative Knowledge Base `path` is resolved against the installed package, so the
default `knowledge_base/` works regardless of ComfyUI's working directory.

## Pipeline nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Scene Analyzer** | `natural_language` (STRING), `config` (COMPILER_CONFIG, optional — supplies model/temperature/retries/timeout), `system_prompt` (STRING, optional override) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING) |
| **Scene Validator** | `scene` (SCENE), `config` (COMPILER_CONFIG, optional) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING) |
| **Resolver** | `scene` (SCENE), `knowledge_base` (KNOWLEDGE_BASE), `config` (COMPILER_CONFIG, optional) | `resolved_tags` (RESOLVED_TAGS), `warnings` (STRING), `errors` (STRING) |
| **Category Splitter** | `resolved_tags` (RESOLVED_TAGS) | `category_map` (CATEGORY_MAP), `warnings` (STRING), `errors` (STRING) |
| **Prompt Builder** | `category_map` (CATEGORY_MAP), `config` (COMPILER_CONFIG, optional) | one STRING per category (`character`, `appearance`, `hair`, `face`, `eyes`, `expression`, `body`, `clothing`, `accessories`, `pose`, `action`, `interaction`, `objects`, `environment`, `camera`, `lighting`, `style`, `quality`, `miscellaneous`) plus reserved `negative` and `scene` (STRING) |

The **Category Splitter** produces the intermediate Category Map; the per-category
prompt strings are produced by the **Prompt Builder**.

## Support nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Configuration** | one input per configuration option (analyzer, resolver, validator, prompt builder, semantic, debug), plus the Knowledge Base `knowledge_base` path, `resolver_knowledge_base_version`, and `knowledge_base_reload` | `config` (COMPILER_CONFIG), `knowledge_base` (KNOWLEDGE_BASE), `warnings` (STRING), `errors` (STRING) |
| **Debug Viewer** | `scene` (SCENE, optional), `resolved_tags` (RESOLVED_TAGS, optional), `category_map` (CATEGORY_MAP, optional), `warnings` (STRING, optional), `errors` (STRING, optional) | `report` (STRING) |

- The **Configuration** node is the single place for compiler settings. Its `config`
  output feeds the optional `config` input of the Scene Analyzer, Validator, and
  Resolver, and it also **loads the Knowledge Base** from the configured path/version
  and emits it on its `knowledge_base` output (wired into the Resolver's
  `knowledge_base` input) — so the Knowledge Base directory is entered in one place.
  There is no separate Knowledge Base Loader node. Bump `knowledge_base_reload` to
  force a fresh read (no automatic file watching).
- The **Debug Viewer** is read-only; connect any intermediate state to inspect it.

A ready-to-use workflow wiring all of these is in
[`examples/workflows/scene_compiler_pipeline.json`](../examples/workflows/scene_compiler_pipeline.json).
