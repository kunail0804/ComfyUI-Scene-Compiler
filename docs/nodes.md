# ComfyUI node reference

The exact inputs, outputs, and data types of the shipped Scene Compiler nodes.
All nodes appear under the **Scene Compiler** category. Data flows between nodes
as typed objects; the inter-stage types are `SCENE`, `KNOWLEDGE_BASE`, and
`COMPILER_CONFIG`.

Nodes are thin adapters: all behaviour lives in the `compiler` package, which
never imports ComfyUI. Settings live on a single **Configuration** node; the stage
nodes take one optional `config` connection rather than carrying their own copies.

Every stage node also exposes a diagnostic string output — `raw` (a JSON dump of
that node's data output) for the Analyzer and Validator, and `json` (the traceable
resolved tags) for the Resolver — for inspecting the pipeline. Wire it into a
text/preview node or the Debug Viewer.

## Pipeline nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Scene Analyzer** | `natural_language` (STRING), `config` (COMPILER_CONFIG, optional — supplies model/temperature/retries/timeout) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING), `raw` (STRING) |
| **Scene Validator** | `scene` (SCENE), `config` (COMPILER_CONFIG, optional) | `scene` (SCENE), `warnings` (STRING), `errors` (STRING), `raw` (STRING) |
| **Resolver** | `scene` (SCENE), `knowledge_base` (KNOWLEDGE_BASE), `config` (COMPILER_CONFIG, optional) | `prompt` (STRING), `warnings` (STRING), `errors` (STRING), `json` (STRING) |

The **Resolver** is the final stage. It resolves concepts to Knowledge Base tags,
expands them, removes duplicates, and joins them into one flat `prompt` string in
resolution order. There are no per-category outputs: the separate Category Splitter
and Prompt Builder stages were removed in V1.1 and their work now happens inside the
Resolver. Categories still exist on each Knowledge Base entry and on each resolved
tag (visible in the `json` output) purely for traceability.

Without a Configuration node the Scene Analyzer falls back to built-in defaults
(llama3, temperature 0) with a 300 s timeout, which is generous on purpose: a local
Ollama model cold-loads into VRAM on the first call.

## Support nodes

| Node | Inputs | Outputs |
|---|---|---|
| **Configuration** | see the table below | `config` (COMPILER_CONFIG), `knowledge_base` (KNOWLEDGE_BASE), `warnings` (STRING), `errors` (STRING) |
| **Debug Viewer** | `scene` (SCENE, optional), `warnings` (STRING, optional), `errors` (STRING, optional) | `report` (STRING) |

- The **Configuration** node is the single source of compiler settings *and* the
  Knowledge Base loader. It reads the Knowledge Base that ships inside the package
  and emits it on `knowledge_base`, which you wire into the Resolver — there is no
  separate Knowledge Base Loader node. The Knowledge Base path is fixed (not a
  user-facing setting); bump `knowledge_base_reload` to force a fresh read. If the
  Knowledge Base fails to load, `config` is still emitted (the Analyzer and Validator
  do not need it) and the failure is reported on `errors`.
- The **Debug Viewer** is read-only; connect any intermediate state to inspect it.

### Configuration inputs

| Input | Type | Purpose |
|---|---|---|
| `analyzer_model` | STRING | Ollama model the Scene Analyzer uses. |
| `analyzer_temperature` | FLOAT | Sampling temperature; 0 is the most repeatable. |
| `analyzer_max_retries` | INT | Retries when the model returns malformed JSON. |
| `analyzer_timeout` | INT | Seconds to wait for the model (default 300). |
| `resolver_strict_mode` | BOOLEAN | Report unknown concepts instead of guessing. |
| `resolver_allow_aliases` | BOOLEAN | Resolve aliases to their canonical entry. |
| `resolver_expansion_enabled` | BOOLEAN | Add tags implied by an entry's expansion list. |
| `resolver_max_expansion_depth` | INT | How deep expansion may recurse. |
| `resolver_include_nsfw` | BOOLEAN | Include explicit-rated entries. Off = SFW only. |
| `validator_allow_unknown_fields` | BOOLEAN | Keep unrecognized Scene JSON fields. |
| `prompt_remove_duplicate_tags` | BOOLEAN | Drop duplicate tags after expansion (`SC0007`). |
| `debug_enabled` / `debug_level` | BOOLEAN / combo | Diagnostic logging and its verbosity. |
| `resolver_knowledge_base_version` | STRING *(optional)* | Pin a Knowledge Base dataset version. Empty = unpinned. |
| `semantic_enabled` | BOOLEAN *(optional)* | Opt-in nearest-neighbour fallback. Off by default. |
| `semantic_min_similarity` | FLOAT *(optional)* | Minimum similarity to accept a fallback match. |
| `semantic_backend` | STRING *(optional)* | Embedding backend for the fallback (offline). |
| `knowledge_base_reload` | INT *(optional)* | Bump to re-read the Knowledge Base from disk. |

Deliberately **not** exposed: the Knowledge Base path (fixed — it ships in the
package), `prompt_target` and `prompt_separator` (reserved / fixed to `,` for this
version), and any hand-written analyzer system prompt. These keep their compiler
defaults; see [Configuration, Errors & Logging](../../../wiki/Configuration-Errors-and-Logging)
for the full config document.

## Typical graph

```
Configuration ─ config ──────────► Scene Analyzer / Scene Validator / Resolver
              └ knowledge_base ───► Resolver

Scene Analyzer → Scene Validator → Resolver → (image workflow)
```

A ready-to-use workflow wiring all of these is in
[`examples/workflows/scene_compiler_pipeline.json`](../examples/workflows/scene_compiler_pipeline.json).
