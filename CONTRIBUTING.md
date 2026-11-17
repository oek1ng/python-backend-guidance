# Contributing

The project is an expanded Alpha with 60 draft guides. Start with an issue describing a concrete
agent failure, or propose a small guide with a reproducible example.

## Guide checklist

- Describe a task or failure mode, not a library overview or architectural taste.
- State when the advice applies and when a simpler approach is sufficient.
- Declare Python (at least 3.12), runtime, library, and database requirements.
- Explain resource ownership, failure behavior, and limits of guarantees.
- Prefer primary documentation; include links and a source-review date.
- Supply a runnable minimal example and behavioral checks.
- Fully annotate examples, tests, and evaluation code using the
  [Python 3.12+ typing policy](docs/typing.md); run Pyrefly with the checked-in `all` preset.
- Keep guidance focused; do not repeat advice already enforced by tooling.
- Identify each example's architectural role; keep domain/application policy
  independent of drivers and put SQL, transport and resource ownership at the
  adapter/composition boundary. See [the example architecture](docs/guide-format.md#clean-architecture-in-reference-examples).
- Distinguish a tested example from evidence of improved agent outcomes.

Guides live in `src/python_backend_guidance/guides/<id>.md` and follow
[guide schema 1](docs/guide-format.md). The ID must match the filename. Use `draft`
until independent technical review is recorded with a reviewer and date.
Source inspection, example tests, technical review, and measured agent usefulness
are separate kinds of evidence. A runtime or library choice in one guide is not a
project-wide requirement.

Keep the complete example code block synchronized with its declared `examples/`
file. The catalog-wide synchronization check covers every declared example.
After formatting an example, refresh the embedded copies with
`uv run python -m evals.sync_examples` and review the resulting guide changes.
Register its public task and reusable behavioral checks in `evals/tasks.toml`,
including a deliberately defective solution with one documented behavioral
mutation. Calibration runs its full contract: `must_fail` and any declared
`related_failures` must fail, while all other reference checks must pass.
Declare related failures only for the same violated guarantee; preserve unrelated
validation and cleanup in the candidate.
Related tasks can share a test file using `@pytest.mark.contract("<guide-id>")`;
`--task` selects the appropriate contract. Add the guide to [the catalog](docs/catalog.md)
and supported queries in both retrieval splits, and reconsider formerly
unsupported query labels when coverage changes.

## Tests and evaluation

Use the cheapest level that demonstrates the behavior. Use real asyncio
primitives for concurrency examples; coordinate with events instead of relying
on scheduler timing. Every test should catch a distinct regression. Do not make
graders require a preferred implementation when another satisfies the contract.

Run the commands in [README.md](README.md#develop). The Python 3.12 job is required:
passing on a newer interpreter alone does not establish minimum-version support.
Do not run untrusted generated code with secrets or production access.
Database and broker semantics must use the real disposable services described in
[integration testing](docs/integration-testing.md), rather than mock commit/ack calls.

## Sources and licensing

Write original explanations. Link to primary sources instead of copying their
documentation. Before including quotations or adapted code, check the source's
license, retain required notices, and record attribution. A link alone does not
make an otherwise incompatible copy acceptable.

By submitting a contribution, you agree to license it under the applicable
Apache-2.0 (software and snippets) or CC-BY-4.0 (prose) terms described in README.
