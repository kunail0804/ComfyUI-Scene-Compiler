# Golden files & the regression convention

This directory holds the **golden outputs** for the ten reference scenes
(MASTER_SPEC §26.8): the exact prompt outputs each scene compiles to. The golden
tests (`tests/regression/test_golden.py`) assert exact equality, guarding
determinism — the same input, Knowledge Base, and configuration must always
produce identical output.

The reference scenes themselves are defined in
[`tests/regression/golden_scenes.py`](../golden_scenes.py).

## Regenerating goldens (deliberate only)

Goldens are **never** regenerated automatically. When a change is *intended* to
alter compiler output — for example a Knowledge Base edit or a formatting change —
regenerate them explicitly and review the diff before committing:

```bash
python scripts/regenerate_goldens.py
git diff tests/regression/golden/
```

If the golden tests fail and the change was **not** intended to alter output, that
is a real regression — fix the code, do not regenerate.

## Regression convention

Every fixed bug adds a **permanent** regression test that is never removed. Put
scene-level regressions here (a new reference scene plus its golden) and
unit-level regressions in the relevant stage's test module. Regression tests are
part of the long-term validation suite and only grow.
