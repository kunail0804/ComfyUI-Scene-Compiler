# Contributing

Full contributor guidelines live in the project wiki:
[Development, Testing & Contributing](https://github.com/kunail0804/ComfyUI-Scene-Compiler/wiki/Development-Testing-and-Contributing).
The authoritative specification is [`MASTER_SPEC.md`](MASTER_SPEC.md) (see §24–§28).

## Local setup

Requires **Python 3.11+**.

```bash
git clone https://github.com/kunail0804/ComfyUI-Scene-Compiler.git
cd ComfyUI-Scene-Compiler
python -m pip install -e ".[dev]"
```

## Checks

Run the same checks CI runs before opening a pull request:

```bash
ruff check .          # lint
ruff format --check . # formatting
pytest                # tests
```

## Ground rules

- **Determinism first** — identical input + Knowledge Base + config always produces
  identical output. No randomness.
- **No hardcoded tag mappings** — concept-to-tag knowledge lives in `knowledge_base/`.
- **Separation of concerns** — `compiler/` never imports ComfyUI; `nodes/` contains no
  compiler logic.
- **Tests ship with code** — new functionality includes tests; every bug fix adds a
  regression test.
- Explicit type hints on public functions, docstrings, and structured logging (no `print`).

## Contributing to the Knowledge Base

The Knowledge Base is data, not code. To add or edit a concept, follow the field
rules and file layout in [`knowledge_base/README.md`](knowledge_base/README.md),
then validate your change:

```bash
python scripts/validate_knowledge_base.py knowledge_base/
```

A change that alters compiler output must also update the golden files
deliberately (see [`tests/regression/golden/README.md`](tests/regression/golden/README.md)).

## Node and developer reference

- ComfyUI node inputs/outputs: [`docs/nodes.md`](docs/nodes.md)
- Performance baselines: [`docs/benchmarks.md`](docs/benchmarks.md)
