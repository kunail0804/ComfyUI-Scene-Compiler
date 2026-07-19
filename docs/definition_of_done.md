# Version 1 — Definition of Done

Status of the MASTER_SPEC §7.8 Definition of Done. Items marked **auto** are
verified by the automated test suite / CI; **manual** items required a ComfyUI
visual check before the release was tagged.

> **All items are met; Version 1 shipped as `v1.0.0` / `v1.1.0`.** This page is kept
> as the V1 completion record. The *evidence* column below is updated to point at the
> code as it stands today: V1.1 removed the separate Category Splitter and Prompt
> Builder stages (their work moved into the Resolver), and V2 folded the Knowledge
> Base Loader into the Configuration node. For the current pipeline see
> [`nodes.md`](nodes.md).

| # | Definition-of-Done item | Status | Evidence |
|---|---|---|---|
| 1 | Natural language is successfully analyzed | ✅ auto | Scene Analyzer (`compiler/analyzer/`): backend, system prompt, response parsing, and bounded retry — `tests/analyzer/` (backend mocked, no live Ollama). |
| 2 | Scene JSON validates successfully | ✅ auto | Scene Validator (`compiler/validator/`) — `tests/validator/`. |
| 3 | Concepts resolve correctly | ✅ auto | Illustrious Resolver (`compiler/resolver/`) — `tests/resolver/`. |
| 4 | Illustrious tags are generated | ✅ auto | Resolver tag generation + expansion — `tests/resolver/`, golden tests. |
| 5 | Tags are categorized | ✅ auto | Every resolved tag carries the category of its Knowledge Base entry, surfaced in the Resolver's `json` output (`compiler/resolver/`) — `tests/resolver/`. Since V1.1 the category is traceability metadata and no longer splits the output. |
| 6 | Prompt outputs are generated | ✅ auto | The Resolver joins the resolved tags into one flat prompt string (`compiler/resolver/`) — `tests/resolver/`, integration + golden tests. |
| 7 | All automated tests pass | ✅ auto | `pytest` green on Python 3.11 & 3.12 in CI (unit, integration, golden, performance). |
| 8 | Documentation is complete | ✅ auto/manual | README, `docs/`, CONTRIBUTING, `knowledge_base/README.md`, wiki; `tests/test_docs_consistency.py` guards node references. |
| 9 | Example workflows execute without modification | ⏳ manual | `examples/scenes/*` compile to their documented outputs (`tests/test_examples.py`); the ComfyUI workflow (`examples/workflows/scene_compiler_pipeline.json`) needs a load-and-run check in ComfyUI. |
| 10 | No mandatory feature depends on prompt generation | ✅ auto | The Style and Quality categories are reserved for workflow integration and are not generated; nothing performs automatic prompt engineering or beautification. |
| 11 | No compiler stage performs semantic hallucination | ✅ auto | Unknown concepts are reported (SC0001) and never invented; the Analyzer prompt forbids invention; the Resolver only looks up the Knowledge Base. Golden tests pin unknown/ambiguous behaviour. |

## Outcome

Both remaining steps were completed: the package was verified visually in ComfyUI
(all nodes appear under *Scene Compiler* and the example workflow runs end to end),
and `v1.0.0` was tagged and published, followed by `v1.1.0`.

The package now ships **five** nodes — Scene Analyzer, Scene Validator, Resolver,
Configuration, and Debug Viewer — after V1.1 and V2 consolidated the pipeline. The
same manual check (load in ComfyUI, run the example workflow) is repeated before
each release.
