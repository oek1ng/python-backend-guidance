# Guide format: schema 1

This is the Alpha format contract, to be stabilized before v1.0. The CLI parses
metadata but never imports or executes a guide's example.

## Location and front matter

Store a guide at `src/python_backend_guidance/guides/<id>.md`. Use UTF-8 Markdown,
with TOML metadata between opening and closing `+++` lines:

```toml
schema_version = 1
id = "example-guide"
title = "Solve a concrete problem"
description = "A short explanation used to choose search results."
python = ">=3.12"
runtime = "asyncio"
tags = ["concurrency", "backpressure"]
status = "draft"
example = "examples/example_guide.py"

[[sources]]
url = "https://docs.python.org/3.12/library/asyncio-task.html"
checked = 2026-11-16
```

Required fields:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`; unsupported schemas fail explicitly |
| `id` | Lowercase hyphenated slug matching the filename |
| `title`, `description` | Nonempty strings |
| `python` | Minimum version in the form `>=MAJOR.MINOR`, no lower than 3.12 |
| `runtime` | A nonempty explicit runtime name; `any` means runtime-independent |
| `tags` | Nonempty array of nonempty strings |
| `status` | `draft` or `reviewed` |
| `example` | Relative `.py` path under `examples/`, without parent traversal |
| `sources` | Nonempty array of source URL and `checked` date tables |

Source URLs must be HTTP(S) URLs without credentials. Dates are native TOML dates,
not strings or timestamps. Runtime filters use exact names such as `asyncio` and
`sync`; `any` has no concurrency-runtime requirement. There is no implicit
migration between runtimes.

Unknown metadata keys are ignored for additive extensions. Required keys are
validated; do not use an extension to change an existing field's meaning.

Optional `aliases` is an array of nonempty English capability descriptions. Use
it for real terminology and synonyms that the guide covers. Do not list unrelated
queries just to inflate benchmark recall. See [retrieval](retrieval.md).

## Applicability beyond Python and runtime

Optional `services` is an array of human-readable requirements, for example
`["PostgreSQL >=16"]`. An optional `[libraries]` table maps names to nonempty
version-requirement strings.

These requirements are declarations, not automatic environment checks. The CLI
does not install dependencies, query services, or interpret library specifiers.
Agents must inspect the project and read the full guide. A successful Python and
runtime filter does not establish complete compatibility.

## Review and evidence

`reviewed` additionally requires a nonempty `reviewed_by` string and native TOML
`reviewed_on` date before any table headers. This is a maintainer assertion, not
an authenticated approval mechanism.

Keep the following evidence separate:

1. Source inspection: the `sources[].checked` dates.
2. Reference behavior: runnable examples and contract tests.
3. Technical review: named review of applicability, limitations, and code.
4. Agent results: reproducible reports for a pinned agent/model and task set.

Passing tests does not set `reviewed`. A reviewed guide need not improve every
agent. Do not invent a reviewer or treat calibration as an agent-performance eval.

## Required content

Include these sections:

- `When to use`: conditions and when a simpler approach is enough.
- `Rules`: short, actionable recommendations.
- `Reference example`: a complete runnable Python example.
- `Guarantees and assumptions`: ownership, versions, error and cancellation policy.
- `Pitfalls`: important limits, not blanket claims.
- `Verification`: observable behaviors, not preferred source patterns.
- `Sources`: primary links matching the structured source list.

The example's first Python code block must match its executable file. Tests check
this generically for every guide. Do not embed secrets, vendor project details,
or unlicensed copied material.

## Clean Architecture in reference examples

Every reference names the architectural role of the code it demonstrates:
domain policy, input/application boundary or workflow, infrastructure adapter,
observability adapter, or composition root. A reference is a **slice** of an
application, not a mandate to reproduce every layer in a single file. A pure
calculation needs no repository interface; an example about SQL, broker acks,
HTTP, files, or processes belongs at the corresponding adapter boundary.

Keep domain rules independent of drivers. Application workflows borrow
capabilities through callables or narrow protocols when they must coordinate
external effects; adapters implement those capabilities and own vendor APIs.
Storage-enforced invariants, such as scoped SQL queries and atomic writes, stay
in the persistence adapter. Composition roots create and close resources. If a
reference includes more than one role for a runnable public contract, separate
the policy/workflow into a vendor-independent function and keep the adapter as
the public entrypoint. Preserve the documented entrypoint and observable
behavior when refactoring. Do not introduce unused layers, fake repositories,
or framework dependencies solely to make a small example look like a complete
application.

Keep named helpers at module scope. Use a small class for callbacks that need
owned state rather than defining functions inside other functions.

Every reference follows the [typing policy](typing.md): complete annotations,
precise callback and data contracts, and stdlib typing available at its declared
Python minimum. Pyrefly checks the executable copies; synchronization checks
extend that guarantee to the first Python block of all 60 guides.

The CLI and its catalog remain dependency-free. An example needing a library,
database, or broker must declare it and arrange separate test dependencies; it
must not silently add those requirements to the CLI.
