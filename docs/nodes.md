# ComfyUI node reference

The exact inputs, outputs, and data types of the shipped Scene Compiler nodes.
All nodes appear under the **Scene Compiler** category. Data flows between nodes
as typed objects; the inter-stage types are `SCENE`, `RESOLVED_TAGS`,
`CATEGORY_MAP`, `KNOWLEDGE_BASE`, and `COMPILER_CONFIG`.

Nodes are thin adapters: all behaviour lives in the `compiler` package, which
never imports ComfyUI.

## Pipeline nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Scene Analyzer** | `natural_language` (STRING), `model_name` (STRING), `temperature` (FLOAT), `timeout` (INT), `system_prompt` (STRING, optional) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING) |
| **Scene Validator** | `scene` (SCENE), `config` (COMPILER_CONFIG, optional) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING) |
| **Resolver** | `scene` (SCENE), `knowledge_base` (KNOWLEDGE_BASE), `config` (COMPILER_CONFIG, optional) | `resolved_tags` (RESOLVED_TAGS), `warnings` (STRING), `errors` (STRING) |
| **Category Splitter** | `resolved_tags` (RESOLVED_TAGS) | `category_map` (CATEGORY_MAP), `warnings` (STRING), `errors` (STRING) |
| **Prompt Builder** | `category_map` (CATEGORY_MAP), `config` (COMPILER_CONFIG, optional) | one STRING per category (`character`, `appearance`, `hair`, `face`, `eyes`, `expression`, `body`, `clothing`, `accessories`, `pose`, `action`, `interaction`, `objects`, `environment`, `camera`, `lighting`, `style`, `quality`, `miscellaneous`) plus reserved `negative` and `scene` (STRING) |

The **Category Splitter** produces the intermediate Category Map; the per-category
prompt strings are produced by the **Prompt Builder**.

## Support nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Configuration** | one input per configuration option (analyzer, resolver, validator, prompt builder, debug) | `config` (COMPILER_CONFIG), `errors` (STRING) |
| **Knowledge Base Loader** | `path` (STRING), `reload` (INT, optional) | `knowledge_base` (KNOWLEDGE_BASE), `warnings` (STRING), `errors` (STRING) |
| **Debug Viewer** | `scene` (SCENE, optional), `resolved_tags` (RESOLVED_TAGS, optional), `category_map` (CATEGORY_MAP, optional), `warnings` (STRING, optional), `errors` (STRING, optional) | `report` (STRING) |

- The **Configuration** node's `config` output feeds the optional `config` input of
  the Validator, Resolver, and Prompt Builder, so behaviour changes without
  rewiring.
- The **Knowledge Base Loader** reloads only when `reload` changes (no automatic
  file watching).
- The **Debug Viewer** is read-only; connect any intermediate state to inspect it.

A ready-to-use workflow wiring all of these is in
[`examples/workflows/scene_compiler_pipeline.json`](../examples/workflows/scene_compiler_pipeline.json).
