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
