# Typing policy

Python **3.12+** is the baseline for the CLI, all 60 reference examples, tests,
evaluation tools, and calibration candidates. CI also runs behavior on 3.13 and
3.14. The CLI has no third-party runtime dependencies.

## Required checks

```sh
uv sync --locked --group dev --python 3.12
uv run --python 3.12 pyrefly check
uv run --python 3.12 ruff check .
uv run --python 3.12 pytest
```

Pyrefly is pinned to **1.4.1**, uses `preset = "all"` and targets Python 3.12.
It checks `src/`, `examples/`, `tests/`, `evals/`, and the local `.pyi` stubs.
Do not weaken the preset, exclude difficult modules, or suppress diagnostics
to pass the gate. The guide synchronization tests ensure the first Python block
is the same code as the checked executable reference.
`tests/typing_contracts.py` additionally asserts concrete caller result types for
generic callbacks, caches, transactions, and resource scopes.

## Express the contract

- Annotate every parameter (except inferred `self`/`cls`) and return, including
  fixtures, nested functions, generators, and deliberately defective candidates.
- Use PEP 695 generic functions/classes and `type` aliases. Keep the relationship
  between input values, callbacks, and results; a generic result is not `object`.
- Use `collections.abc` interfaces for input capabilities, concrete containers
  for owned results, `Protocol` for structural dependencies, and `TypedDict` for
  known record fields. Use `Literal`, `Never`, and `override` where they describe
  actual behavior.
- Use stdlib `typing` and ordinary imports. Avoid `typing_extensions`,
  `from __future__ import annotations`, and `TYPE_CHECKING` guards. Quote only
  actual forward references. Ruff enforces these import choices.
- Keep annotations valid at runtime on 3.12: spell all type arguments of
  `Generator[T, None, None]` and `AsyncGenerator[T, None]`. Do not use later-only
  features such as type-parameter defaults or closed `TypedDict` declarations.
- Explicitly discard intentionally unused results with `_ = ...`. Express
  emptiness and optional values explicitly rather than relying on truthiness
  of arbitrary objects.

## Dynamic boundaries

`object` is appropriate for genuinely unknown input, opaque values, and broad
driver rows. Validate and narrow before using it. Never use it to erase a
relationship that generics or a record schema can express. Explicit `Any` and
blanket casts are not acceptable substitutes for contracts.

Psycopg connections use `Connection[tuple[object, ...]]`. A local, explained cast
may describe a known SQL projection established by the schema and query.
These casts assert a schema assumption; real PostgreSQL tests verify it.
JSON and user-supplied TOML are narrowed at their boundaries. Casts of checked-in
evaluation fixtures and test reports describe trusted schemas, rather than
pretending to validate arbitrary user input.

Pytest dynamically loads independent candidate modules. `tests/contracts.py`
describes their public structural interfaces; candidates need not inherit
reference classes. Defective calibration candidates must honestly annotate
their actual results, even when these differ from the correct contract.
Calibration must detect exactly their declared behavioral failures across the
full contract, with all unrelated checks passing. Document intentional unused
parameters instead of adding dummy reads or changing public keyword names.

Pika lacks bundled typing. `stubs/pika/` describes only the blocking API used by
our real RabbitMQ tests, with its supported version range documented there.
The installed Pika package remains the runtime implementation. Update the stubs
when changing the exercised API; do not replace third-party packages at runtime.

Transitive development dependencies may depend on `typing-extensions`; this
policy concerns our source and direct dependencies, not their implementation.
Static checks, runtime tests, source review, and agent-performance evidence are
separate guarantees.
