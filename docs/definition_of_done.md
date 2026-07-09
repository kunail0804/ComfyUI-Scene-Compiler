# Version 1 — Definition of Done

Status of the MASTER_SPEC §7.8 Definition of Done. Items marked **auto** are
verified by the automated test suite / CI; **manual** items require a ComfyUI
visual check before the release is tagged.

| # | Definition-of-Done item | Status | Evidence |
|---|---|---|---|
| 1 | Natural language is successfully analyzed | ✅ auto | Scene Analyzer (`compiler/analyzer/`): backend, system prompt, response parsing, and bounded retry — `tests/analyzer/` (backend mocked, no live Ollama). |
| 2 | Scene JSON validates successfully | ✅ auto | Scene Validator (`compiler/validator/`) — `tests/validator/`. |
| 3 | Concepts resolve correctly | ✅ auto | Illustrious Resolver (`compiler/resolver/`) — `tests/resolver/`. |
| 4 | Illustrious tags are generated | ✅ auto | Resolver tag generation + expansion — `tests/resolver/`, golden tests. |
| 5 | Tags are categorized | ✅ auto | Category Splitter (`compiler/splitter/`) — `tests/test_category_splitter.py`. |
| 6 | Prompt outputs are generated | ✅ auto | Prompt Builder (`compiler/builder/`) — `tests/test_prompt_builder.py`, integration + golden tests. |
| 7 | All automated tests pass | ✅ auto | `pytest` green on Python 3.11 & 3.12 in CI (unit, integration, golden, performance). |
| 8 | Documentation is complete | ✅ auto/manual | README, `docs/`, CONTRIBUTING, `knowledge_base/README.md`, wiki; `tests/test_docs_consistency.py` guards node references. |
| 9 | Example workflows execute without modification | ⏳ manual | `examples/scenes/*` compile to their documented outputs (`tests/test_examples.py`); the ComfyUI workflow (`examples/workflows/scene_compiler_pipeline.json`) needs a load-and-run check in ComfyUI. |
| 10 | No mandatory feature depends on prompt generation | ✅ auto | Reserved Negative/Scene outputs and Style/Quality categories are always empty in V1; nothing performs automatic prompt engineering. |
| 11 | No compiler stage performs semantic hallucination | ✅ auto | Unknown concepts are reported (SC0001) and never invented; the Analyzer prompt forbids invention; the Resolver only looks up the Knowledge Base. Golden tests pin unknown/ambiguous behaviour. |

## Remaining before tagging `v1.0.0`

- **ComfyUI visual verification (manual):** load the package in ComfyUI, confirm
  all eight nodes appear under *Scene Compiler*, and run the example workflow
  end to end (item 9).
- **Tag & release:** once the visual check passes, tag `v1.0.0` (SemVer, §28) and
  publish the GitHub release. This step is intentionally deferred to a human.
